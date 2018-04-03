#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_cw_dashboard(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = '%s_%s' % (name, region)
    print_message('terminate cloudwatch dashboard: %s' % dashboard_name)

    cmd = ['cloudwatch', 'delete-dashboards']
    cmd += ['--dashboard-names', dashboard_name]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch dashboard')

cw = env.get('cloudwatch', dict())

target_cw_dashboard_name = args[1]
target_cw_dashboard_name_exists = False

if len(args) == 2:
    for cw_dashboard_env in cw.get('DASHBOARDS', list()):
        if cw_dashboard_env['NAME'] == target_cw_dashboard_name:
            target_cw_dashboard_name_exists = True
            run_terminate_cw_dashboard(cw_dashboard_env['NAME'], cw_dashboard_env)
    if not target_cw_dashboard_name_exists:
        print('"%s" is not exists in config.json' % target_cw_dashboard_name)
else:
    for cw_dashboard_env in cw.get('DASHBOARDS', list()):
        run_terminate_cw_dashboard(cw_dashboard_env['NAME'], cw_dashboard_env)
