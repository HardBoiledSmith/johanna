#!/usr/bin/env python3

from env import env
from run_common import AWSCli

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    aws_cli = AWSCli()

    env = env['appstream']['STACK'][0]
    stack_name = env['NAME']
    fleet_name = f'fleet/{env["FLEET_NAME"]}'
    appstream_policy_name = env["APPSTREAM_SCALING_POLICY"]

    ################################################################################
    #
    # start
    #
    ################################################################################

    cc = ['application-autoscaling', 'delete-scaling-policy']
    cc += ['--policy-name', appstream_policy_name]
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-id', fleet_name]
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    aws_cli.run(cc, ignore_error=True)

    cc = ['application-autoscaling', 'deregister-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-id', fleet_name]
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    aws_cli.run(cc, ignore_error=True)
