#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


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

        env_name_only = True
        for dimension in pm[0]:
            if dimension == 'InstanceId':
                env_name_only = False

        template = json.dumps(pm[0])
        new_metrics_list = list()
        if env_name_only:
            for ii in env_list:
                new_metric = template.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        else:
            for ii in env_instances_list:
                new_metric = template.replace('INSTANCE_ID', ii['Id'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
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


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch dashboard')

check_template_availability()

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
    else:
        print('"%s" is not supported' % cw_dashboard_env['TYPE'])
        raise Exception()

if not check_exists and target_cw_dashboard_name and not region:
    print('"%s" is not exists in config.json' % target_cw_dashboard_name)

if not check_exists and target_cw_dashboard_name and region:
    print('"%s, %s" is not exists in config.json' % (target_cw_dashboard_name, region))
