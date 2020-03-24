#!/usr/bin/env python3

import json
import time

from env import env
from run_common import AWSCli

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    aws_cli = AWSCli()

    env = env['appstream']['STACK'][0]
    fleet_name = f'fleet/{env["FLEET_NAME"]}'
    max_capacity = f'{env["MIN_CAPACITY"]}'
    min_capacity = f'{env["MAX_CAPACITY"]}'
    appstream_policy_name = env["APPSTREAM_SCALING_POLICY"]
    scale_target_value = env['SCALE_TARGET_VALUE']

    ################################################################################
    #
    # start
    #
    ################################################################################

    cc = ['application-autoscaling', 'describe-scalable-targets']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-ids', fleet_name]

    rr = aws_cli.run(cc)
    if rr['ScalableTargets']:
        cc = ['application-autoscaling', 'deregister-scalable-target']
        cc += ['--service-namespace', 'appstream']
        cc += ['--resource-id', fleet_name]
        cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
        aws_cli.run(cc)

        time.sleep(30)

    cc = ['application-autoscaling', 'register-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    cc += ['--resource-id', fleet_name]
    cc += ['--min-capacity', max_capacity]
    cc += ['--max-capacity', min_capacity]
    aws_cli.run(cc)

    appstream_policy = {
        'PolicyName': appstream_policy_name,
        'ServiceNamespace': 'appstream',
        'ResourceId': fleet_name,
        'ScalableDimension': 'appstream:fleet:DesiredCapacity',
        'PolicyType': 'TargetTrackingScaling',
        'TargetTrackingScalingPolicyConfiguration': {
            'TargetValue': scale_target_value,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'AppStreamAverageCapacityUtilization'
            },
            'ScaleOutCooldown': 30,
            'ScaleInCooldown': 300
        }
    }

    cc = ['application-autoscaling', 'put-scaling-policy']
    cc += ['--cli-input-json', json.dumps(appstream_policy)]
    aws_cli.run(cc)
