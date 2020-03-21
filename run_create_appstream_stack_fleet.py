#!/usr/bin/env python3

import json
import time
from time import sleep

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


################################################################################
#
# start
#
################################################################################
def create_iam_for_appstream():
    aws_cli = AWSCli()
    sleep_required = False

    role_name = 'AmazonAppStreamServiceAccess'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role: %s' % role_name)

        cc = ['iam', 'create-role']
        cc += ['--role-name', role_name]
        cc += ['--path', '/service-role/']
        cc += ['--assume-role-policy-document', 'file://aws_iam/aws-appstream-role.json']
        aws_cli.run(cc)

        cc = ['iam', 'attach-role-policy']
        cc += ['--role-name', role_name]
        cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonAppStreamServiceAccess']
        aws_cli.run(cc)

        sleep_required = True

    role_name = 'ApplicationAutoScalingForAmazonAppStreamAccess'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role: %s' % role_name)

        cc = ['iam', 'create-role']
        cc += ['--role-name', role_name]
        cc += ['--assume-role-policy-document', 'file://aws_iam/aws-appstream-role.json']
        aws_cli.run(cc)

        cc = ['iam', 'attach-role-policy']
        cc += ['--role-name', role_name]
        cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/ApplicationAutoScalingForAmazonAppStreamAccess']
        aws_cli.run(cc)
        sleep_required = True

    if sleep_required:
        print_message('wait 30 seconds to let iam role and policy propagated to all regions...')
        time.sleep(30)


def create_fleet(name, image_name, subnet_ids, security_group_id, desired_instances):
    vpc_config = 'SubnetIds=%s,SecurityGroupIds=%s' % (subnet_ids, security_group_id)

    aws_cli = AWSCli()
    cmd = ['appstream', 'create-fleet']
    cmd += ['--name', name]
    cmd += ['--instance-type', 'stream.standard.medium']
    cmd += ['--fleet-type', 'ON_DEMAND']
    cmd += ['--compute-capacity', 'DesiredInstances=%d' % desired_instances]
    cmd += ['--image-name', image_name]
    cmd += ['--vpc-config', vpc_config]
    cmd += ['--no-enable-default-internet-access']
    cmd += ["--disconnect-timeout-in-seconds", '60']
    cmd += ["--idle-disconnect-timeout-in-seconds", '180']
    # cmd += ["--max-user-duration-in-seconds", '60~360000']

    aws_cli.run(cmd)

    sleep(10)

    cmd = ['appstream', 'start-fleet']
    cmd += ['--name', name]
    aws_cli.run(cmd)


def create_stack(stack_name, embed_host_domains):
    name = stack_name

    storage_connectors = 'ConnectorType=HOMEFOLDERS,'
    storage_connectors += 'ResourceIdentifier=appstream2-36fb080bb8-ap-northeast-2-041220267268'

    user_settings = 'Action=CLIPBOARD_COPY_FROM_LOCAL_DEVICE,Permission=ENABLED,'
    user_settings += 'Action=CLIPBOARD_COPY_TO_LOCAL_DEVICE,Permission=ENABLED,'
    user_settings += 'Action=FILE_UPLOAD,Permission=ENABLED,'
    user_settings += 'Action=FILE_DOWNLOAD,Permission=ENABLED'

    application_settings = 'Enabled=true,SettingsGroup=stack'

    aws_cli = AWSCli()
    cmd = ['appstream', 'create-stack']
    cmd += ['--name', name]
    # cmd += ['--storage-connectors', storage_connectors]
    cmd += ['--user-settings', user_settings]
    cmd += ['--application-settings', application_settings]
    cmd += ['--embed-host-domains', embed_host_domains]
    aws_cli.run(cmd)


def associate_fleet(stack_name, fleet_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'associate-fleet']
    cmd += ['--fleet-name', fleet_name]
    cmd += ['--stack-name', stack_name]

    return aws_cli.run(cmd)


def wait_state(service, name, state):
    services = {
        'image-builder': {
            'cmd': 'describe-image-builders',
            'name': 'ImageBuilders'
        },
        'fleet': {
            'cmd': 'describe-fleets',
            'name': 'Fleets'
        }
    }

    if service not in services:
        raise Exception('only allow services(%s)' % ', '.join(services.keys()))

    aws_cli = AWSCli()
    elapsed_time = 0
    is_not_terminate = True
    ss = services[service]

    while is_not_terminate:
        cmd = ['appstream', ss['cmd']]
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr[ss['name']]:
            if state == r['State']:
                is_not_terminate = False

        if elapsed_time > 1200:
            raise Exception('timeout: stop appstream image builder(%s)' % name)

        sleep(5)
        print('wait image builder state(%s) (elapsed time: \'%d\' seconds)' % (state, elapsed_time))
        elapsed_time += 5


def get_subnet_and_security_group_id():
    aws_cli = AWSCli()
    cidr_subnet = aws_cli.cidr_subnet

    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    if not eb_vpc_id:
        print('ERROR!!! No VPC found')
        raise Exception()

    print_message('get subnet id')

    subnet_id_1 = None
    subnet_id_2 = None
    cmd = ['ec2', 'describe-subnets']
    rr = aws_cli.run(cmd)
    for r in rr['Subnets']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
            subnet_id_1 = r['SubnetId']
        if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
            subnet_id_2 = r['SubnetId']

    print_message('get security group id')

    security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    rr = aws_cli.run(cmd)
    for r in rr['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == '%seb_private' % name_prefix:
            security_group_id = r['GroupId']
            break

    return [subnet_id_1, subnet_id_2], security_group_id


def apply_fleet_auto_scale_policy():
    aws_cli = AWSCli()
    ### tartget
    cc = ['application-autoscaling', 'register-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    cc += ['--resource-id', 'fleet/naoko-fleet']
    cc += ['--min-capacity', '1']
    cc += ['--max-capacity', '5']
    aws_cli.run(cc)



    # 예제 1
    # appstream_policy = {
    #     "PolicyName": "scale-out-utilization",
    #     "ServiceNamespace": "appstream",
    #     "ResourceId": "fleet/naoko-fleet",
    #     "ScalableDimension": "appstream:fleet:DesiredCapacity",
    #     "PolicyType": "StepScaling",
    #     "StepScalingPolicyConfiguration": {
    #         "AdjustmentType": "PercentChangeInCapacity",
    #         "StepAdjustments": [
    #             {
    #                 "MetricIntervalLowerBound": 0,
    #                 "ScalingAdjustment": 25
    #             }
    #         ],
    #         "Cooldown": 120
    #     }
    # }
    #
    # cc = ['application-autoscaling', 'put-scaling-policy']
    # cc += ['--cli-input-json', json.dumps(appstream_policy)]
    # rr = aws_cli.run(cc)
    # print(rr['PolicyARN'])
    #
    # cc = ['cloudwatch', 'put-metric-alarm']
    # cc += ['--alarm-name', 'appstream-scale-out']
    # cc += ['--alarm-description', 'Alarm when Capacity Utilization exceeds 75 percent']
    # cc += ['--metric-name', 'CapacityUtilizaion']
    # cc += ['--namespace', 'AWS/AppStream']
    # cc += ['--statistic', 'Average']
    # cc += ['--period', '60']
    # cc += ['--threshold', '75']
    # cc += ['--comparison-operator', 'GreaterThanThreshold']
    # cc += ['--dimensions', 'Name=fleetName,Value=%s' % "naoko-fleet"]
    # cc += ['--evaluation-periods', '1']
    # cc += ['--unit', 'Percent']
    # cc += ['--alarm-actions', rr['PolicyARN']]
    # aws_cli.run(cc)


    ### Case 2 // 용량 부족 오류를 기반으로 조정 정책 적용용량 부족 오류를 기반으로 조정 정책 적용
    appstream_policy = {
        "PolicyName": "scale-out-utilization",
        "ServiceNamespace": "appstream",
        "ResourceId": "fleet/naoko-fleet",
        "ScalableDimension": "appstream:fleet:DesiredCapacity",
        "PolicyType": "StepScaling",
        "StepScalingPolicyConfiguration": {
            "AdjustmentType": "ChangeInCapacity",
            "StepAdjustments": [
                {
                    "MetricIntervalLowerBound": 0,
                    "ScalingAdjustment": 1
                }
            ],
            "Cooldown": 0
        }
    }

    cc = ['application-autoscaling', 'put-scaling-policy']
    cc += ['--cli-input-json', json.dumps(appstream_policy)]
    rr = aws_cli.run(cc)
    print(rr['PolicyARN'])

    cc = ['cloudwatch', 'put-metric-alarm']
    cc += ['--alarm-name', 'appstream-scale-out']
    cc += ['--alarm-description', 'Alarm when out of capacity is > 0']
    cc += ['--metric-name', 'InsufficientCapacityError']
    cc += ['--namespace', 'AWS/AppStream']
    cc += ['--statistic', 'Maximum']
    cc += ['--period', '60']
    cc += ['--threshold', '0']
    cc += ['--comparison-operator', 'GreaterThanThreshold']
    cc += ['--dimensions', 'Name=FleetName,Value=%s' % "naoko-fleet"]
    cc += ['--evaluation-periods', '1']
    cc += ['--unit', 'Count']
    cc += ['--alarm-actions', rr['PolicyARN']]
    rr = aws_cli.run(cc)
    print('###################')
    print(rr)
    print('finish')

    ### Case 5 // 목표 추적 조정 정책
    # appstream_policy = {
    #     "PolicyName": "target-tracking-scaling-policy",
    #     "ServiceNamespace": "appstream",
    #     "ResourceId": "fleet/naoko-fleet",
    #     "ScalableDimension": "appstream:fleet:DesiredCapacity",
    #     "PolicyType": "TargetTrackingScaling",
    #     "TargetTrackingScalingPolicyConfiguration": {
    #         "TargetValue": 75.0,
    #         "PredefinedMetricSpecification": {
    #             "PredefinedMetricType": "AppStreamAverageCapacityUtilization"
    #         },
    #         "ScaleOutCooldown": 30,
    #         "ScaleInCooldown": 300
    #     }
    # }

    # cc = ['application-autoscaling', 'put-scaling-policy']
    # cc += ['--cli-input-json', json.dumps(appstream_policy)]
    # aws_cli.run(cc)


def delete_fleet_auto_scale_policy():
    aws_cli = AWSCli()
    ###
    # delete policy 예 5
    # cc = ['application-autoscaling', 'delete-scaling-policy']
    # cc += ['--policy-name', 'target-tracking-scaling-policy']
    # cc += ['--service-namespace', 'appstream']
    # cc += ['--resource-id', 'fleet/naoko-fleet']
    # cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    # aws_cli.run(cc)

    ####

    # delete policy 예 1
    # cc = ['application-autoscaling', 'delete-scaling-policy']
    # cc += ['--policy-name', 'scale-out-utilization']
    # cc += ['--service-namespace', 'appstream']
    # cc += ['--resource-id', 'fleet/naoko-fleet']
    # cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    # aws_cli.run(cc)
    #
    # cc = ['cloudwatch', 'delete-alarms']
    # cc += ['--alarm-names', 'appstream-scale-out']
    # aws_cli.run(cc)

    cc = ['application-autoscaling', 'deregister-scalable-target']
    cc += ['--service-namespace', 'appstream']
    cc += ['--resource-id', 'fleet/naoko-fleet']
    cc += ['--scalable-dimension', 'appstream:fleet:DesiredCapacity']
    aws_cli.run(cc)

###


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    target_name = None
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''
    subnet_ids, security_group_id = get_subnet_and_security_group_id()

    if len(args) > 1:
        target_name = args[1]

    # create_iam_for_appstream()
    # for env_s in env['appstream']['STACK']:
    #     if target_name and env_s['NAME'] != target_name:
    #         continue
    #
    #     print_session('create appstream image builder')
    #
    #     fleet_name = env_s['FLEET_NAME']
    #     image_name = env_s['IMAGE_NAME']
    #     stack_name = env_s['NAME']
    #     embed_host_domains = env_s['EMBED_HOST_DOMAINS']
    #     desired_instances = env_s.get('DESIRED_INSTANCES', 4)
    #
    #     create_fleet(fleet_name, image_name, ','.join(subnet_ids), security_group_id, desired_instances)
    #     create_stack(stack_name, embed_host_domains)
    #     wait_state('fleet', fleet_name, 'RUNNING')
    #     associate_fleet(stack_name, fleet_name)
    apply_fleet_auto_scale_policy()
    # delete_fleet_auto_scale_policy()
