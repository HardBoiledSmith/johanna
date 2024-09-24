#!/usr/bin/env python3.12

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_cw_alarm(name, settings):
    phase = env['common']['PHASE']
    region = settings['AWS_REGION']
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
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in cw.get('ALARMS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    run_terminate_cw_alarm(settings['NAME'], settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'cloudwatch alarm: {mm} is not found in config.json')
