#!/usr/bin/env python3

import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def create_appstream_fleet_autoscale(settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    fleet_name = settings["FLEET_NAME"]

    print_message(f'create fleet autoscale for: {fleet_name}')

    appstream_scale_in_policy_name = settings["APPSTREAM_SCALING_IN_POLICY"]
    appstream_scale_out_policy_name = settings["APPSTREAM_SCALING_OUT_POLICY"]
    fleet_path = f'fleet/{settings["FLEET_NAME"]}'
    max_capacity = settings["MAX_CAPACITY"]
    min_capacity = settings["MIN_CAPACITY"]

    cc = ['application-autoscaling', 'describe-scalable-targets']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-ids', fleet_path]
    rr = aws_cli.run(cc)
    if rr['ScalableTargets']:
        cc = ['application-autoscaling', 'deregister-scalable-target']
        cc += ['--service-namespace', 'appstream']
        cc += ['--resource-id', fleet_path]
        cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
        aws_cli.run(cc)

        time.sleep(30)

    # register target auto-scale
    cc = ['application-autoscaling', 'register-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    cc += ['--resource-id', fleet_path]
    cc += ['--min-capacity', min_capacity]
    cc += ['--max-capacity', max_capacity]
    aws_cli.run(cc)

    # Scale out
    appstream_policy = {
        'PolicyName': appstream_scale_out_policy_name,
        'ServiceNamespace': 'appstream',
        'ResourceId': fleet_path,
        'ScalableDimension': 'appstream:fleet:DesiredCapacity',
        'PolicyType': 'StepScaling',
        "StepScalingPolicyConfiguration": {
            "AdjustmentType": "PercentChangeInCapacity",
            "StepAdjustments": [
                {
                    "MetricIntervalLowerBound": 0,
                    "ScalingAdjustment": 25
                }
            ],
            "Cooldown": 60
        }
    }

    cc = ['application-autoscaling', 'put-scaling-policy']
    cc += ['--cli-input-json', json.dumps(appstream_policy)]
    rr = aws_cli.run(cc)

    policy_arn = rr['PolicyARN']
    cc = ['cloudwatch', 'put-metric-alarm']
    cc += ['--alarm-name', appstream_scale_out_policy_name]
    cc += ['--alarm-description', '"Alarm when Capacity Utilization exceeds 75 percent"']
    cc += ['--metric-name', 'CapacityUtilization']
    cc += ['--namespace', 'AWS/AppStream']
    cc += ['--statistic', 'Average']
    cc += ['--period', '120']
    cc += ['--threshold', '75']
    cc += ['--comparison-operator', 'GreaterThanThreshold']
    cc += ['--dimensions', 'Name=Fleet,Value=naoko-fleet']
    cc += ['--evaluation-periods', '1']
    cc += ['--unit', 'Percent']
    cc += ['--alarm-actions', policy_arn]

    aws_cli.run(cc)

    # Scale in
    appstream_policy = {
        "PolicyName": appstream_scale_in_policy_name,
        "ServiceNamespace": "appstream",
        "ResourceId": fleet_path,
        "ScalableDimension": "appstream:fleet:DesiredCapacity",
        "PolicyType": "StepScaling",
        "StepScalingPolicyConfiguration": {
            "AdjustmentType": "PercentChangeInCapacity",
            "StepAdjustments": [
                {
                    "MetricIntervalUpperBound": 0,
                    "ScalingAdjustment": -25
                }
            ],
            "Cooldown": 360
        }
    }

    cc = ['application-autoscaling', 'put-scaling-policy']
    cc += ['--cli-input-json', json.dumps(appstream_policy)]
    rr = aws_cli.run(cc)

    policy_arn = rr['PolicyARN']
    cc = ['cloudwatch', 'put-metric-alarm']
    cc += ['--alarm-name', appstream_scale_in_policy_name]
    cc += ['--alarm-description', '"Alarm when Capacity Utilization is less than or equal to 25 percent"']
    cc += ['--metric-name', 'CapacityUtilization']
    cc += ['--namespace', 'AWS/AppStream']
    cc += ['--statistic', 'Average']
    cc += ['--period', '120']
    cc += ['--threshold', '25']
    cc += ['--comparison-operator', 'LessThanOrEqualToThreshold']
    cc += ['--dimensions', f'Name=Fleet,Value={fleet_name}']
    cc += ['--evaluation-periods', '6']
    cc += ['--unit', 'Percent']
    cc += ['--alarm-actions', policy_arn]

    aws_cli.run(cc)


################################################################################
#
# start
#
################################################################################


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    target_name = None
    region = None

    if len(args) > 1:
        target_name = args[1]

    if len(args) > 2:
        region = args[2]

    print_session('create appstream autoscaling setting for stack & fleet')

    for settings in env['appstream']['STACK']:
        if target_name and settings['NAME'] != target_name:
            continue

        if region and settings.get('AWS_DEFAULT_REGION') != region:
            continue

        create_appstream_fleet_autoscale(settings)
