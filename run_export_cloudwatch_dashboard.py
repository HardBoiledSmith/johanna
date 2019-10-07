#!/usr/bin/env python3
import json
import re

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import reset_template_dir

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_export_cloudwatch_dashboard(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = '%s_%s' % (name, region)
    print_message('export cloudwatch dashboard: %s' % dashboard_name)

    cmd = ['cloudwatch', 'get-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    result = aws_cli.run(cmd)

    service_type = settings['TYPE']
    dashboard_body = json.loads(result['DashboardBody'])

    for dw in dashboard_body['widgets']:
        pm = dw['properties'].get('metrics')
        if not pm:
            return
        pm = pm[:1]
        prev = ''
        current_index = 0
        if len(pm) < 1:
            return
        for dimension in pm[0]:
            if service_type == 'elasticbeanstalk':
                if prev == 'AutoScalingGroupName':
                    pm[0][current_index] = 'AUTO_SCALING_GROUP_NAME'
                if prev == 'EnvironmentName':
                    pm[0][current_index] = 'ENVIRONMENT_NAME'
                if prev == 'InstanceId':
                    pm[0][current_index] = 'INSTANCE_ID'
                if prev == 'LoadBalancerName':
                    pm[0][current_index] = 'LOAD_BALANCER_NAME'
                if prev == 'LoadBalancer':
                    pm[0][current_index] = 'LOAD_BALANCER'
                if prev == 'TargetGroup':
                    pm[0][current_index] = 'TARGET_GROUP'
                if type(dimension) == dict and 'label' in dimension \
                        and re.match(r'^%s-[0-9]{10}$' % name, dimension['label']):
                    dimension['label'] = 'ENVIRONMENT_NAME'

            if service_type == 'rds/aurora':
                if prev == 'Role':
                    pm[0][current_index] = 'ROLE'
                if prev == 'DBClusterIdentifier':
                    pm[0][current_index] = 'DB_CLUSTER_IDENTIFIER'
                if prev == 'DbClusterIdentifier':
                    pm[0][current_index] = 'DB_CLUSTER_IDENTIFIER'

            prev = dimension
            current_index += 1
        dw['properties']['metrics'] = pm

    template_name = env['template']['NAME']
    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'w') as ff:
        json.dump(dashboard_body, ff, sort_keys=True, indent=2)


def run_export_cloudwatch_dashboard_sqs_lambda(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = '%s_%s' % (name, region)
    print_message('export cloudwatch dashboard: %s' % dashboard_name)

    cmd = ['cloudwatch', 'get-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    result = aws_cli.run(cmd)

    dashboard_body = json.loads(result['DashboardBody'])

    for dw in dashboard_body['widgets']:
        pm = dw['properties']['metrics']
        first_pm = pm[:1]
        prev = ''
        current_index = 0
        if len(first_pm) < 1:
            return
        for dimension in first_pm[0]:
            if prev == 'QueueName':
                queue_name = first_pm[0][current_index]
                if queue_name.startswith('dv-'):
                    queue_name = queue_name.replace('dv-', 'PHASE-')
                if queue_name.startswith('qa-'):
                    queue_name = queue_name.replace('qa-', 'PHASE-')
                if queue_name.startswith('op-'):
                    queue_name = queue_name.replace('op-', 'PHASE-')
                first_pm[0][current_index] = queue_name
            prev = dimension
            current_index += 1
        dw['properties']['metrics'] = pm

        title = dw['properties']['title']
        if title.startswith('SQS: dv-'):
            title = title.replace('SQS: dv-', 'SQS: PHASE-')
        if title.startswith('SQS: qa-'):
            title = title.replace('SQS: qa-', 'SQS: PHASE-')
        if title.startswith('SQS: op-'):
            title = title.replace('SQS: op-', 'SQS: PHASE-')
        dw['properties']['title'] = title

    template_name = env['template']['NAME']
    filename_path = 'template/%s/cloudwatch/%s.json' % (template_name, dashboard_name)
    with open(filename_path, 'w') as ff:
        json.dump(dashboard_body, ff, sort_keys=True, indent=2)


################################################################################
#
# start
#
################################################################################
print_session('export cloudwatch dashboard')

reset_template_dir()

cw = env['cloudwatch']
cw_dashboards = cw['DASHBOARDS']
for cd in cw_dashboards:
    if cd['TYPE'] == 'sqs,lambda,sms':
        run_export_cloudwatch_dashboard_sqs_lambda(cd['NAME'], cd)
    else:
        run_export_cloudwatch_dashboard(cd['NAME'], cd)
