#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def terminate_appstream_fleet_autoscale(settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

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


if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

    target_name = None
    region = options.get('region')

    if len(args) > 1:
        target_name = args[1]

    print_session('terminate appstream autoscaling setting for stack & fleet')

    for settings in env['appstream']['STACK']:
        if target_name and settings['NAME'] != target_name:
            continue

        if region and settings.get('AWS_DEFAULT_REGION') != region:
            continue

        terminate_appstream_fleet_autoscale(settings)
