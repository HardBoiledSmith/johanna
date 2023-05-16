#!/usr/bin/env python3
import json
import re
from datetime import datetime
from datetime import timedelta

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import reset_template_dir

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def create_sms_log():
    aws_cli = AWSCli('ap-northeast-1')

    role_name = 'aws-sns-sms-log-role'
    policy_name = 'aws-sns-sms-log-policy'

    print_message(f'create role: {role_name}')

    role = aws_cli.get_iam_role(role_name)

    if not role:
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', f'file://aws_iam/{role_name}.json']
        role = aws_cli.run(cmd)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', f'file://aws_iam/{policy_name}.json']
        aws_cli.run(cmd)

    role_arn = role['Role']['Arn']

    print_message('start sms log')

    dd = {'attributes': {'DeliveryStatusSuccessSamplingRate': '100',
                         'DeliveryStatusIAMRole': role_arn}}
    cmd = ['sns', 'set-sms-attributes']
    cmd += ['--cli-input-json', json.dumps(dd)]
    aws_cli.run(cmd)


def run_create_cw_dashboard_elasticbeanstalk(name, settings):
    dashboard_region = settings['AWS_REGION']
    aws_cli = AWSCli(dashboard_region)

    print_message(f'get elasticbeanstalk environment info: {name}')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--include-deleted']
    dd = datetime.now() - timedelta(weeks=8)
    cmd += ['--included-deleted-back-to', dd.strftime('%Y-%m-%d')]
    result = aws_cli.run(cmd)

    eid_list = set()
    elb_list = set()
    for ee in result['Environments']:
        ename = ee['EnvironmentName']
        if not ename.startswith(name):
            continue
        if 'EndpointURL' not in ee:
            continue
        eid_list.add(ee['EnvironmentId'])

        pattern = r'awseb-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+'
        match = re.search(pattern, ee['EndpointURL'])
        elb_list.add(match.group())

    def find_metrics(*args):
        cmd = ['cloudwatch', 'list-metrics']
        cmd += ['--namespace', args[0]]
        cmd += ['--metric-name', args[1]]
        result = aws_cli.run(cmd)

        mm_list = list()

        for cc in result['Metrics']:
            dd = cc['Dimensions']
            if args[2] != dd[0]['Name']:
                continue

            mm = re.match(r'^awseb-(.+)-stack.+$', dd[0]['Value'])
            if not mm:
                continue

            eid = mm.group(1)
            if eid not in eid_list:
                continue

            mm_list.append(cc)
        return mm_list

    def check_string_in_list(lst, string_to_check):
        for s in lst:
            if string_to_check in s:
                return True
        return False

    def find_metrics_by_target_group_load_balancer(*args):
        cmd = ['cloudwatch', 'list-metrics']
        cmd += ['--namespace', args[0]]
        cmd += ['--metric-name', args[1]]
        result = aws_cli.run(cmd)

        mm_list = list()

        for cc in result['Metrics']:
            dd = cc['Dimensions']
            if not dd or not len(dd) == 2:
                continue

            load_balancer_name = dd[0]['Name']
            if args[2] != load_balancer_name:
                continue

            target_group = re.match(r'^targetgroup/awseb-(.+).+$', dd[0]['Value'])
            loadbalancer = re.match(r'^app/awseb-(.+).+$', dd[1]['Value'])
            if not target_group and not loadbalancer:
                continue

            pattern = r"awseb-[A-Z0-9]+-[A-Z0-9]+"
            match = re.search(pattern, dd[1]['Value'])
            if not check_string_in_list(elb_list, match.group(0)):
                continue

            mm_list.append(cc)
        return mm_list

    ################################################################################
    dashboard_name = '%s_%s' % (name, dashboard_region)
    print_message('create or update cloudwatch dashboard: %s' % dashboard_name)

    template_name = env['template']['NAME']
    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'r') as ff:
        dashboard_body = json.load(ff)

    asg_only = ['CPUUtilization', 'CPUCreditBalance', 'CPUSurplusCreditBalance', 'NetworkIn', 'NetworkOut']

    for dw in dashboard_body['widgets']:
        if dw['properties'].get('title') not in asg_only:
            continue
        if not dw['properties'].get('metrics'):
            continue
        pm = dw['properties']['metrics']
        ii = 1
        new_metric = []

        ll = find_metrics(*pm[0])
        for oo in ll:
            mm = [oo['Namespace'], oo['MetricName']]
            for aa in oo['Dimensions']:
                mm.append(aa['Name'])
                mm.append(aa['Value'])
            mm.append({'id': f'max{ii}', 'visible': False, 'stat': 'Maximum'})
            new_metric.append(mm)

            mm = [oo['Namespace'], oo['MetricName']]
            for aa in oo['Dimensions']:
                mm.append(aa['Name'])
                mm.append(aa['Value'])
            mm.append({'id': f'avg{ii}', 'visible': False, 'stat': 'Average'})
            new_metric.append(mm)

            mm = [oo['Namespace'], oo['MetricName']]
            for aa in oo['Dimensions']:
                mm.append(aa['Name'])
                mm.append(aa['Value'])
            mm.append({'id': f'min{ii}', 'visible': False, 'stat': 'Minimum'})
            new_metric.append(mm)
            ii += 1

        new_metric += pm[1:]
        dw['properties']['metrics'] = new_metric

    elb_only = ['AutoScaleInstanceCount']
    for dw in dashboard_body['widgets']:
        if dw['properties'].get('title') not in elb_only:
            continue
        if not dw['properties'].get('metrics'):
            continue
        pm = dw['properties']['metrics']
        new_metric = []

        ll = find_metrics_by_target_group_load_balancer(*pm[0])
        ii = 0
        for oo in ll:
            mm = [oo['Namespace'], oo['MetricName']]
            for aa in oo['Dimensions']:
                mm.append(aa['Name'])
                mm.append(aa['Value'])
            mm.append({'id': f"mh{ii}", 'visible': False, 'stat': 'Average'})
            new_metric.append(mm)
            ii += 1

        ll = find_metrics_by_target_group_load_balancer(*pm[1])
        ii = 0
        for oo in ll:
            mm = [oo['Namespace'], oo['MetricName']]
            for aa in oo['Dimensions']:
                mm.append(aa['Name'])
                mm.append(aa['Value'])
            mm.append({'id': f"muh{ii}", 'visible': False, 'stat': 'Average'})
            new_metric.append(mm)
            ii += 1

        new_metric += pm[2:]
        dw['properties']['metrics'] = new_metric

    ################################################################################
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--no-include-deleted']
    result = aws_cli.run(cmd)

    latest_ee = None
    latest_name = ''
    for ee in result['Environments']:
        ename = ee['EnvironmentName']
        if not ename.startswith(name):
            continue
        if latest_name < ename:
            latest_ee = ee
            latest_name = ename

    env_list = [latest_ee]

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

    for dw in dashboard_body['widgets']:
        if dw['properties'].get('title') in asg_only:
            continue
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
            elif type(dimension) == dict:
                if 'expression' in dimension:
                    dimension_type = 'search_expression'
                    break

        new_metric = []

        template = json.dumps(pm)
        if dimension_type == 'asg':
            for ii in env_asg_list:
                new_metric = template.replace('AUTO_SCALING_GROUP_NAME', ii['Name'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
        elif dimension_type == 'instance':
            for ii in env_instances_list:
                new_metric = template.replace('INSTANCE_ID', ii['Id'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
        elif dimension_type == 'elb':
            for ii in env_elb_list:
                new_metric = template.replace('LOAD_BALANCER_NAME', ii['Name'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
        elif dimension_type == 'tg':
            for ii in env_tg_list:
                new_metric = template.replace('TARGET_GROUP', ii['Name'])
                new_metric = new_metric.replace('LOAD_BALANCER', ii['LoadBalancer'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
        elif dimension_type == 'search_expression':
            new_metric = json.loads(template)
        else:
            for ii in env_list:
                new_metric = template.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)

        dw['properties']['metrics'] = new_metric

    ################################################################################
    phase = env['common']['PHASE']
    dashboard_body = json.dumps(dashboard_body)
    dashboard_body = dashboard_body.replace('PHASE-', '%s-' % phase)

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

    dashboard_region = settings['AWS_REGION']
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
        old_lines = ff.readlines()

    new_lines = list()
    for ll in old_lines:
        nn = ll.replace('DB_CLUSTER_IDENTIFIER', cluster_id)
        new_lines.append(nn)

    dashboard_body = ' '.join(new_lines)

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


def run_create_cw_dashboard_sqs_lambda_sms(name, settings):
    print_message('create sms log')
    create_sms_log()

    phase = env['common']['PHASE']
    dashboard_region = settings['AWS_REGION']
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
    alarm_region = settings['AWS_REGION']
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


def run_create_cw_dashboard_ramiel(name, settings):
    region = settings['AWS_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = f'{name}_{region}'
    print_message(f'create or update cloudwatch dashboard: {dashboard_name}')

    template_name = env['template']['NAME']
    dashboard_body = f'file://template/{template_name}/cloudwatch/{dashboard_name}.json'

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch dashboard')

reset_template_dir(options)

cw = env.get('cloudwatch', dict())
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in cw.get('DASHBOARDS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True
    if settings['TYPE'] == 'elasticbeanstalk':
        run_create_cw_dashboard_elasticbeanstalk(settings['NAME'], settings)
    elif settings['TYPE'] == 'rds/aurora':
        run_create_cw_dashboard_rds_aurora(settings['NAME'], settings)
    elif settings['TYPE'] == 'sqs,lambda,sms':
        run_create_cw_dashboard_sqs_lambda_sms(settings['NAME'], settings)
    elif settings['TYPE'] == 'alarm':
        run_create_cw_dashboard_alarm(settings['NAME'], settings)
    elif settings['TYPE'] == 'ramiel':
        run_create_cw_dashboard_ramiel(settings['NAME'], settings)
    else:
        print('"%s" is not supported' % settings['TYPE'])
        raise Exception()

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'cloudwatch dashboard: {mm} is not found in config.json')
