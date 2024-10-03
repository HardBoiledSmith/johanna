#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def terminate_appstream_fleet_autoscale(settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    fleet_name = settings['FLEET_NAME']

    print_message(f'terminate fleet autoscale for: {fleet_name}')

    fleet_path = f"fleet/{settings['FLEET_NAME']}"

    cc = ['cloudwatch', 'delete-alarms']
    cc += ['--alarm-names', 'scale-out-utilization-policy']
    aws_cli.run(cc, ignore_error=True)

    cc = ['cloudwatch', 'delete-alarms']
    cc += ['--alarm-names', 'scale-in-utilization-policy']
    aws_cli.run(cc, ignore_error=True)

    cc = ['application-autoscaling', 'deregister-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-id', fleet_path]
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    aws_cli.run(cc, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate appstream autoscaling setting for stack & fleet')

appstream = env['appstream']
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in appstream.get('STACK', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    terminate_appstream_fleet_autoscale(settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'appstream autoscale: {mm} is not found in config.json')
