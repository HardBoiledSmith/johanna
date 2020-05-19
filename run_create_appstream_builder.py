#!/usr/bin/env python3

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


def create_image_builder(name, subnet_ids, security_group_id, image_name):
    vpc_config = 'SubnetIds=%s,SecurityGroupIds=%s' % (subnet_ids, security_group_id)

    aws_cli = AWSCli()
    cmd = ['appstream', 'create-image-builder']
    cmd += ['--name', name]
    cmd += ['--instance-type', 'stream.standard.medium']
    cmd += ['--image-name', image_name]
    cmd += ['--vpc-config', vpc_config]
    cmd += ['--no-enable-default-internet-access']

    aws_cli.run(cmd)


def wait_state(name):
    aws_cli = AWSCli()
    elapsed_time = 0
    is_waiting = True

    while is_waiting:
        cmd = ['appstream', 'describe-image-builders']
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr['ImageBuilders']:
            if 'RUNNING' == r['State']:
                is_waiting = False

        if elapsed_time > 1200:
            raise Exception('timeout: creating image builder (%s)' % name)

        sleep(5)
        print('wait image builder ready... (elapsed time: \'%d\' seconds)' % elapsed_time)
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


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    target_name = None
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''
    subnet_ids, security_group_id = get_subnet_and_security_group_id()

    if len(args) > 1:
        target_name = args[1]

    print_session('create appstream image builder')

    create_iam_for_appstream()
    for settings in env['appstream']['IMAGE_BUILDS']:
        if target_name and settings['NAME'] != target_name:
            continue

        name = settings['NAME']
        image_name = settings['IMAGE_NAME']

        create_image_builder(name, subnet_ids[0], security_group_id, image_name)
        wait_state(name)
