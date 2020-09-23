#!/usr/bin/env python3
from env import env
from run_common import AWSCli


def run_create_eb_windows_auto_scale(settings):
    aws_cli = AWSCli()

    cmd = ['autoscaling', 'describe-auto-scaling-groups']
    result = aws_cli.run(cmd)
    auto_scaling_group = ""

    for rr in result['AutoScalingGroups']:
        if not rr['Tags']:
            continue

        for dd in rr['Tags']:
            if dd['ResourceType'] == 'auto-scaling-group':
                auto_scaling_group = dd['ResourceId']
                break
        if auto_scaling_group:
            continue
        else:
            break

    # delete ELB default setting auto scale policy & cloudwatch alarm
    cmd = ['autoscaling', 'describe-policies']
    cmd += ['--auto-scaling-group-name', auto_scaling_group]
    response = aws_cli.run(cmd)
    for rr in response['ScalingPolicies']:
        if rr['Alarms']:
            cmd = ['cloudwatch', 'delete-alarms']
            cmd += ['--alarm-names', rr['Alarms'][0]['AlarmName']]
            aws_cli.run(cmd)

    for rr in response['ScalingPolicies']:
        if rr['PolicyName']:
            cmd = ['autoscaling', 'delete-policy']
            cmd += ['--auto-scaling-group-name', auto_scaling_group]
            cmd += ['--policy-name', rr['PolicyName']]
            aws_cli.run(cmd)

    cmd = ['autoscaling', 'put-scaling-policy']
    cmd += ['--policy-name', 'gendo-scale-out']
    cmd += ['--auto-scaling-group-name', auto_scaling_group]
    cmd += ['--scaling-adjustment', settings['SCALE_OUT_ADJUSTMENT']]
    cmd += ['--adjustment-type', 'ChangeInCapacity']
    result = aws_cli.run(cmd)
    scale_out_policy_arn = result['PolicyARN']

    cmd = ['autoscaling', 'put-scaling-policy']
    cmd += ['--policy-name', 'gendo-scale-in']
    cmd += ['--auto-scaling-group-name', auto_scaling_group]
    cmd += ['--scaling-adjustment', settings['SCALE_IN_ADJUSTMENT']]
    cmd += ['--adjustment-type', 'ChangeInCapacity']
    result = aws_cli.run(cmd)
    scale_in_policy_arn = result['PolicyARN']

    scale_out_alarm_name = 'AddGendoCapacityToProcessQueue'
    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-name', scale_out_alarm_name]
    cmd += ['--metric-name', 'ApproximateNumberOfMessagesVisible']
    cmd += ['--namespace', 'AWS/SQS']
    cmd += ['--statistic', 'Sum']
    cmd += ['--period', '180']
    cmd += ['--threshold', '10']
    cmd += ['--comparison-operator', 'GreaterThanThreshold']
    cmd += ['--dimensions', f'Name=QueueName, Value={settings["AWS_SQS_VISUAL_TEST_RESULT"]}']
    cmd += ['--evaluation-periods', '2']
    cmd += ['--alarm-actions', scale_out_policy_arn]
    aws_cli.run(cmd)

    scale_in_alarm_name = 'RemoveGendoCapacityToProcessQueue'
    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-name', scale_in_alarm_name]
    cmd += ['--metric-name', 'ApproximateNumberOfMessagesVisible']
    cmd += ['--namespace', 'AWS/SQS']
    cmd += ['--statistic', 'Sum']
    cmd += ['--period', '300']
    cmd += ['--threshold', '3']
    cmd += ['--comparison-operator', 'LessThanOrEqualToThreshold']
    cmd += ['--dimensions', f'Name=QueueName, Value={settings["AWS_SQS_VISUAL_TEST_RESULT"]}']
    cmd += ['--evaluation-periods', '2']
    cmd += ['--alarm-actions', scale_in_policy_arn]
    aws_cli.run(cmd)

    cmd = ['cloudwatch', 'describe-alarms']
    cmd += ['--alarm-names', scale_in_alarm_name, scale_out_alarm_name]
    aws_cli.run(cmd)

    cmd = ['autoscaling', 'describe-policies']
    cmd += ['--auto-scaling-group-name', auto_scaling_group]
    aws_cli.run(cmd)


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    eb = env['elasticbeanstalk']
    for eb_env in eb['ENVIRONMENTS']:
        if eb_env['TYPE'] == 'windows':
            run_create_eb_windows_auto_scale(eb_env)
            break
