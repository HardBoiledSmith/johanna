#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_export_cloudwatch_dashboard(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    cmd = ['cloudwatch', 'get-dashboard']
    cmd += ['--dashboard-name', name]
    result = aws_cli.run(cmd)

    dashboard_body = json.loads(result['DashboardBody'])

    for dw in dashboard_body['widgets']:
        pm = dw['properties']['metrics']
        pm = pm[:1]
        prev = ''
        current_index = 0
        for dimension in pm[0]:
            if prev == 'InstanceId':
                pm[0][current_index] = 'INSTANCE_ID'
            if prev == 'EnvironmentName':
                pm[0][current_index] = 'ENVIRONMENT_NAME'
            prev = dimension
            current_index += 1
        dw['properties']['metrics'] = pm

    template_name = env['template']['NAME']
    region = settings['AWS_DEFAULT_REGION']
    filename_path = 'template/%s/cloudwatch/%s_%s.json' % (template_name, name, region)
    with open(filename_path, 'w') as ff:
        json.dump(dashboard_body, ff, sort_keys=True, indent=2)


################################################################################
#
# start
#
################################################################################
print_session('export cloudwatch dashboard')

cw = env['cloudwatch']
cw_dashboards = cw['DASHBOARDS']
for cd in cw_dashboards:
    run_export_cloudwatch_dashboard(cd['NAME'], cd)
