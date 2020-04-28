#!/usr/bin/env python3

from env import env
from run_common import AWSCli

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    aws_cli = AWSCli()

    env = env['appstream']['STACK'][0]
    stack_name = env['NAME']
    fleet_path = f'fleet/{env["FLEET_NAME"]}'
    appstream_scaling_out_policy = env["APPSTREAM_SCALING_OUT_POLICY"]
    appstream_scaling_in_policy = env["APPSTREAM_SCALING_IN_POLICY"]

    ################################################################################
    #
    # start
    #
    ################################################################################

    cc = ['cloudwatch', 'delete-alarms']
    cc += ['--alarm-names', appstream_scaling_out_policy]
    aws_cli.run(cc, ignore_error=True)

    cc = ['cloudwatch', 'delete-alarms']
    cc += ['--alarm-names', appstream_scaling_in_policy]
    aws_cli.run(cc, ignore_error=True)

    cc = ['application-autoscaling', 'deregister-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-id', fleet_path]
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    aws_cli.run(cc, ignore_error=True)
