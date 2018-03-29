#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_terminate_cloudwatch_alarm_elasticbeanstalk(name, settings):
    phase = env['common']['PHASE']
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    alarm_name = '%s-%s_%s_%s' % (phase, name, region, settings['METRIC_NAME'])
    print_message('terminate cloudwatch alarm: %s' % alarm_name)

    cmd = ['cloudwatch', 'delete-alarms']
    cmd += ['--alarm-names', alarm_name]
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch alarm')

cw = env.get('cloudwatch', dict())
cw_alarms_list = cw.get('ALARMS', list())
for cw_alarm_env in cw_alarms_list:
    if cw_alarm_env['TYPE'] == 'elasticbeanstalk':
        run_terminate_cloudwatch_alarm_elasticbeanstalk(cw_alarm_env['NAME'], cw_alarm_env)
