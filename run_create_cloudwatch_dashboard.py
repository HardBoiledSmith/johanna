#!/usr/bin/env python3
import json
import re

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import reset_template_dir

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def create_sms_log():
    aws_cli = AWSCli('ap-northeast-1')

    role_name = 'aws-sns-sms-log-role'
    policy_name = 'aws-sns-sms-log-policy'

    print_message('create role: %s' % role_name)

    role = aws_cli.get_iam_role(role_name)

    if not role:
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', 'file://aws_iam/%s.json' % role_name]
        role = aws_cli.run(cmd)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', 'file://aws_iam/%s.json' % policy_name]
        aws_cli.run(cmd)

    role_arn = role['Role']['Arn']

    print_message('start sms log')

    dd = {'attributes': {'DeliveryStatusSuccessSamplingRate': '100',
                         'DeliveryStatusIAMRole': role_arn}}
    cmd = ['sns', 'set-sms-attributes']
    cmd += ['--cli-input-json', json.dumps(dd)]
    aws_cli.run(cmd)


def run_create_cw_dashboard_elasticbeanstalk(name, settings):
    dashboard_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(dashboard_region)

    print_message('get elasticbeanstalk environment info: %s' % name)

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--no-include-deleted']
    result = aws_cli.run(cmd)

    env_list = list()
    for ee in result['Environments']:
        ename = ee['EnvironmentName']
        if ename.startswith(name):
            env_list.append(ee)

    env_instances_list = list()
    env_asg_list = list()
    env_elb_list = list()
    env_tg_list = list()

    for ee in env_list:
        cmd = ['elasticbeanstalk', 'describe-environment-resources']
        cmd += ['--environment-id', ee['EnvironmentId']]
        result = aws_cli.run(cmd)
        ee_res = result['EnvironmentResources']
        for instance in ee_res['Instances']:
            ii = dict()
            ii['Id'] = instance['Id']
            ii['EnvironmentName'] = ee_res['EnvironmentName']
            env_instances_list.append(ii)
        for asg in ee_res['AutoScalingGroups']:
            ii = dict()
            ii['Name'] = asg['Name']
            ii['EnvironmentName'] = ee_res['EnvironmentName']
            env_asg_list.append(ii)
        for elb in ee_res['LoadBalancers']:
            ii = dict()
            ii['Name'] = elb['Name']
            ii['EnvironmentName'] = ee_res['EnvironmentName']
            env_elb_list.append(ii)
        for elb in ee_res['LoadBalancers']:
            cmd = ['elbv2', 'describe-target-groups']
            cmd += ['--load-balancer-arn', elb['Name']]
            result = aws_cli.run(cmd, ignore_error=True)
            for tg in result.get('TargetGroups', list()):
                tt = re.match(r'^.+(targetgroup/.+)$', tg['TargetGroupArn'])
                ll = re.match(r'^.+loadbalancer/(.+)$', elb['Name'])
                ii = dict()
                ii['Name'] = tt[1]
                ii['LoadBalancer'] = ll[1]
                ii['EnvironmentName'] = ee_res['EnvironmentName']
                env_tg_list.append(ii)

    ################################################################################
    dashboard_name = '%s_%s' % (name, dashboard_region)
    print_message('create or update cloudwatch dashboard: %s' % dashboard_name)

    template_name = env['template']['NAME']
    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'r') as ff:
        dashboard_body = json.load(ff)

    for dw in dashboard_body['widgets']:
        if not dw['properties'].get('metrics'):
            continue
        pm = dw['properties']['metrics']

        dimension_type = 'env'
        for dimension in pm[0]:
            if dimension == 'InstanceId':
                dimension_type = 'instance'
            elif dimension == 'AutoScalingGroupName':
                dimension_type = 'asg'
            elif dimension == 'LoadBalancerName':
                dimension_type = 'elb'
            elif dimension == 'TargetGroup':
                dimension_type = 'tg'

        template = json.dumps(pm[0])
        new_metrics_list = list()
        if dimension_type == 'asg':
            for ii in env_asg_list:
                new_metric = template.replace('AUTO_SCALING_GROUP_NAME', ii['Name'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        elif dimension_type == 'instance':
            for ii in env_instances_list:
                new_metric = template.replace('INSTANCE_ID', ii['Id'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        elif dimension_type == 'elb':
            for ii in env_elb_list:
                new_metric = template.replace('LOAD_BALANCER_NAME', ii['Name'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        elif dimension_type == 'tg':
            for ii in env_tg_list:
                new_metric = template.replace('TARGET_GROUP', ii['Name'])
                new_metric = new_metric.replace('LOAD_BALANCER', ii['LoadBalancer'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        else:
            for ii in env_list:
                new_metric = template.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)

        dw['properties']['metrics'] = new_metrics_list

    dashboard_body = json.dumps(dashboard_body)

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


def run_create_cw_dashboard_rds_aurora(name, settings):
    if not env.get('rds'):
        print_message('No RDS settings in config.json')
        return

    if env['rds'].get('ENGINE') != 'aurora':
        print_message('Only RDS Aurora supported')

    dashboard_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(dashboard_region)

    cluster_id = env['rds']['DB_CLUSTER_ID']
    instance_role_list = list()
    instance_role_list.append('WRITER')
    instance_role_list.append('READER')

    dashboard_name = '%s_%s' % (name, dashboard_region)
    print_message('create or update cloudwatch dashboard: %s' % dashboard_name)

    template_name = env['template']['NAME']

    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'r') as ff:
        dashboard_body = json.load(ff)

    for dw in dashboard_body['widgets']:
        pm = dw['properties']['metrics']

        cluster_id_only = True
        for dimension in pm[0]:
            if dimension == 'Role':
                cluster_id_only = False

        template = json.dumps(pm[0])
        new_metrics_list = list()
        if cluster_id_only:
            new_metric = template.replace('DB_CLUSTER_IDENTIFIER', cluster_id)
            new_metric = json.loads(new_metric)
            new_metrics_list.append(new_metric)
        else:
            for ir in instance_role_list:
                new_metric = template.replace('DB_CLUSTER_IDENTIFIER', cluster_id)
                new_metric = new_metric.replace('ROLE', ir)
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)

        dw['properties']['metrics'] = new_metrics_list

    dashboard_body = json.dumps(dashboard_body)

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


def run_create_cw_dashboard_sqs_lambda_sms(name, settings):
    print_message('create sms log')
    create_sms_log()

    phase = env['common']['PHASE']
    dashboard_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(dashboard_region)

    dashboard_name = '%s_%s' % (name, dashboard_region)
    print_message('create or update cloudwatch dashboard: %s' % dashboard_name)

    template_name = env['template']['NAME']

    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'r') as ff:
        dashboard_body = json.load(ff)

    for dw in dashboard_body['widgets']:
        pm = dw['properties']['metrics']

        current_index = 0

        for pp in pm:
            template = json.dumps(pp)
            template = template.replace('PHASE-', '%s-' % phase)
            pm[current_index] = json.loads(template)
            current_index += 1

        dw['properties']['metrics'] = pm

        title = dw['properties']['title']
        if title.startswith('SQS: PHASE-'):
            title = title.replace('SQS: PHASE-', 'SQS: %s-' % phase)
            dw['properties']['title'] = title

    dashboard_body = json.dumps(dashboard_body)

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


def run_create_cw_dashboard_alarm(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(alarm_region)

    dashboard_name = '%s_%s' % (name, alarm_region)

    widgets = list()
    cmd = ['cloudwatch', 'describe-alarms']
    cmd += ['--alarm-name-prefix', '%s-' % phase]
    rr = aws_cli.run(cmd)

    for (ii, aa) in enumerate(rr['MetricAlarms']):
        y = ii // 4 * 6
        x = ii % 4 * 6
        widgets.append({
            "height": 6,
            "properties": {
                "title": aa['AlarmName'],
                "annotations": {
                    "alarms": [
                        aa['AlarmArn']
                    ]
                },
                "view": "timeSeries",
                "stacked": False
            },
            "type": "metric",
            "width": 6,
            "x": x,
            "y": y
        })

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', json.dumps({
        'widgets': widgets
    })]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch dashboard')

reset_template_dir()

cw = env.get('cloudwatch', dict())
target_cw_dashboard_name = None
region = None
check_exists = False

if len(args) > 1:
    target_cw_dashboard_name = args[1]

if len(args) > 2:
    region = args[2]

for cw_dashboard_env in cw.get('DASHBOARDS', list()):
    if target_cw_dashboard_name and cw_dashboard_env['NAME'] != target_cw_dashboard_name:
        continue

    if region and cw_dashboard_env.get('AWS_DEFAULT_REGION') != region:
        continue

    if target_cw_dashboard_name:
        check_exists = True

    if cw_dashboard_env['TYPE'] == 'elasticbeanstalk':
        run_create_cw_dashboard_elasticbeanstalk(cw_dashboard_env['NAME'], cw_dashboard_env)
    elif cw_dashboard_env['TYPE'] == 'rds/aurora':
        run_create_cw_dashboard_rds_aurora(cw_dashboard_env['NAME'], cw_dashboard_env)
    elif cw_dashboard_env['TYPE'] == 'sqs,lambda,sms':
        run_create_cw_dashboard_sqs_lambda_sms(cw_dashboard_env['NAME'], cw_dashboard_env)
    elif cw_dashboard_env['TYPE'] == 'alarm':
        run_create_cw_dashboard_alarm(cw_dashboard_env['NAME'], cw_dashboard_env)
    else:
        print('"%s" is not supported' % cw_dashboard_env['TYPE'])
        raise Exception()

if not check_exists and target_cw_dashboard_name and not region:
    print('"%s" is not exists in config.json' % target_cw_dashboard_name)

if not check_exists and target_cw_dashboard_name and region:
    print('"%s, %s" is not exists in config.json' % (target_cw_dashboard_name, region))
