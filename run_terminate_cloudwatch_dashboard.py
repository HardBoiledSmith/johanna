#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_terminate_cloudwatch_dashboard(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    print_message('terminate cloudwatch dashboard: %s' % name)

    cmd = ['cloudwatch', 'delete-dashboards']
    cmd += ['--dashboard-names', name]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch dashboard')

cw = env['cloudwatch']
cw_dashboards = cw['DASHBOARDS']
for cd in cw_dashboards:
    run_terminate_cloudwatch_dashboard(cd['NAME'], cd)
