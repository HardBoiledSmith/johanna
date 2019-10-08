#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_cw_alarm(name, settings):
    phase = env['common']['PHASE']
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    metric_name = settings.get('METRIC_NAME', 'NotSuccessIn5Min')
    alarm_name = '%s-%s_%s_%s' % (phase, name, region, metric_name)

    if settings['TYPE'] == 'sqs':
        sqs_name = settings['QUEUE_NAME']
        alarm_name = '%s-%s_%s_%s_%s' % (phase, name, region, sqs_name, settings['METRIC_NAME'])

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

if len(args) == 2:
    target_cw_alarm_name = args[1]
    target_cw_alarm_name_exists = False

    for cw_alarm_env in cw.get('ALARMS', list()):
        if cw_alarm_env['NAME'] == target_cw_alarm_name:
            target_cw_alarm_name_exists = True
            run_terminate_cw_alarm(cw_alarm_env['NAME'], cw_alarm_env)
    if not target_cw_alarm_name_exists:
        print('"%s" is not exists in config.json' % target_cw_alarm_name)
else:
    for cw_alarm_env in cw.get('ALARMS', list()):
        run_terminate_cw_alarm(cw_alarm_env['NAME'], cw_alarm_env)
