#!/usr/bin/env python3

import time
from time import sleep

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def create_iam_for_appstream():
    aws_cli = AWSCli()
    sleep_required = False

    role_name = 'AmazonAppStreamServiceAccess'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam role: {role_name}')

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
        print_message(f'create iam role: {role_name}')

        cc = ['iam', 'create-role']
        cc += ['--role-name', role_name]
        cc += ['--assume-role-policy-document', 'file://aws_iam/aws-appstream-role.json']
        aws_cli.run(cc)

        cc = ['iam', 'attach-role-policy']
        cc += ['--role-name', role_name]
        cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/ApplicationAutoScalingForAmazonAppStreamAccess']
        aws_cli.run(cc)
        sleep_required = True

    role_name = 'AmazonAppStreamS3Permission'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam role: {role_name}')

        cc = ['iam', 'create-role']
        cc += ['--role-name', role_name]
        cc += ['--assume-role-policy-document', 'file://aws_iam/aws-appstream-role.json']
        aws_cli.run(cc)

        cc = ['iam', 'attach-role-policy']
        cc += ['--role-name', role_name]
        cc += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonS3FullAccess']
        aws_cli.run(cc)
        sleep_required = True

    if sleep_required:
        print_message('wait 30 seconds to let iam role and policy propagated to all regions...')
        time.sleep(30)


def create_fleet(name, image_name, subnet_ids, security_group_id, desired_instances, fleet_region, fleet_arn):
    vpc_config = f'SubnetIds={subnet_ids},SecurityGroupIds={security_group_id}'

    aws_cli = AWSCli(fleet_region)
    cmd = ['appstream', 'create-fleet']
    cmd += ['--name', name]
    cmd += ['--instance-type', 'stream.standard.medium']
    cmd += ['--fleet-type', 'ON_DEMAND']
    cmd += ['--compute-capacity', f'DesiredInstances={desired_instances}']
    cmd += ['--image-name', image_name]
    cmd += ['--vpc-config', vpc_config]
    cmd += ['--no-enable-default-internet-access']
    cmd += ['--idle-disconnect-timeout-in-seconds', '600']
    cmd += ['--iam-role-arn', fleet_arn]
    # cmd += ["--disconnect-timeout-in-seconds", '60']
    # cmd += ["--max-user-duration-in-seconds", '60~360000']

    aws_cli.run(cmd)

    sleep(10)

    cmd = ['appstream', 'start-fleet']
    cmd += ['--name', name]
    aws_cli.run(cmd)


def create_stack(stack_name, embed_host_domains, stack_region):
    name = stack_name

    user_settings = list()
    user_settings.append('Action=CLIPBOARD_COPY_FROM_LOCAL_DEVICE,Permission=ENABLED')
    user_settings.append('Action=CLIPBOARD_COPY_TO_LOCAL_DEVICE,Permission=ENABLED')
    user_settings.append('Action=FILE_UPLOAD,Permission=ENABLED')
    user_settings.append('Action=FILE_DOWNLOAD,Permission=ENABLED')

    aws_cli = AWSCli(stack_region)
    cmd = ['appstream', 'create-stack']
    cmd += ['--name', name]
    cmd += ['--user-settings'] + user_settings
    cmd += ['--embed-host-domains', embed_host_domains]
    aws_cli.run(cmd)


def associate_fleet(stack_name, fleet_name, fleet_region):
    aws_cli = AWSCli(fleet_region)
    cmd = ['appstream', 'associate-fleet']
    cmd += ['--fleet-name', fleet_name]
    cmd += ['--stack-name', stack_name]

    return aws_cli.run(cmd)


def wait_state(name, fleet_region):
    aws_cli = AWSCli(fleet_region)
    elapsed_time = 0
    is_waiting = True

    while is_waiting:
        cmd = ['appstream', 'describe-fleets']
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr['Fleets']:
            if 'RUNNING' == r['State']:
                is_waiting = False

        if elapsed_time > 1200:
            raise Exception('timeout: creating fleet (%s)' % name)

        sleep(5)
        print('waiting for fleet ready... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


def get_subnet_and_security_group_id(vpc_region):
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    aws_cli = AWSCli(vpc_region)
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


def get_latest_image(image_region):
    aws_cli = AWSCli(image_region)

    ll = list()

    cmd = ['appstream', 'describe-images']
    rr = aws_cli.run(cmd)
    for r in rr['Images']:
        if not r['Name'].startswith('naoko-windows'):
            continue
        ll.append(r['Name'])

    if len(ll) < 1:
        raise Exception('image not found: naoko-windows*')

    return sorted(ll, reverse=True)[0]


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

    print_session('create appstream image stack & fleet')

    create_iam_for_appstream()

    for settings in env['appstream']['STACK']:
        if target_name and settings['NAME'] != target_name:
            continue

        if region and settings.get('AWS_DEFAULT_REGION') != region:
            continue

        desired_instances = settings.get('DESIRED_INSTANCES', 1)
        embed_host_domains = settings['EMBED_HOST_DOMAINS']
        fleet_name = settings['FLEET_NAME']
        region = settings['AWS_DEFAULT_REGION']
        stack_name = settings['NAME']
        canonical_id = settings['CANONICAL_ID']
        fleet_arn = f'arn:aws:iam::{canonical_id}:role/AmazonAppStreamS3Permission'

        image_name = get_latest_image(region)
        subnet_ids, security_group_id = get_subnet_and_security_group_id(region)

        create_fleet(fleet_name, image_name, ','.join(subnet_ids), security_group_id, desired_instances, region, fleet_arn)
        create_stack(stack_name, embed_host_domains, region)
        wait_state(fleet_name, region)
        associate_fleet(stack_name, fleet_name, region)
