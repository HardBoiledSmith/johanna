#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_terminate_cloudwatch_alarm_elasticbeanstalk(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    alarm_name = '%s_%s_%s' % (name, region, settings['METRIC_NAME'])
    print_message('terminate cloudwatch alarm: %s' % alarm_name)

    cmd = ['cloudwatch', 'delete-alarms']
    cmd += ['--alarm-names', alarm_name]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch alarm')

cw = env['cloudwatch']
cw_alarms = cw['ALARMS']
for ca in cw_alarms:
    if ca['TYPE'] == 'elasticbeanstalk':
        run_terminate_cloudwatch_alarm_elasticbeanstalk(ca['NAME'], ca)
