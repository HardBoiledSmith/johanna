#!/usr/bin/env python3
from __future__ import print_function

from run_common import AWSCli

aws_cli = AWSCli()


def describe_vpcs():
    vpc_id = aws_cli.get_vpc_id()
    if vpc_id is None:
        return False
    else:
        return vpc_id


def describe_subnets(vpc_id=None):
    cmd = ['ec2', 'describe-subnets']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['Subnets']:
        return False
    else:
        return True


def describe_internet_gateways(vpc_id=None):
    cmd = ['ec2', 'describe-internet-gateways']
    cmd += ['--filters=Name=attachment.vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['InternetGateways']:
        return False
    else:
        return True


def describe_addressed():
    cmd = ['ec2', 'describe-addresses']
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['Addresses']:
        return False
    else:
        return True


def describe_nat_gateways(vpc_id=None):
    cmd = ['ec2', 'describe-nat-gateways']
    cmd += ['--filter=Name=vpc-id,Values=%s' % vpc_id]

    # noinspection PyBroadException
    try:
        aws_cli.run(cmd)
    except:
        return False

    return True


def describe_route_tables(vpc_id=None):
    cmd = ['ec2', 'describe-route-tables']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['RouteTables']:
        return False
    else:
        return True


def describe_security_groups(vpc_id=None):
    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['SecurityGroups']:
        return False
    else:
        return True


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()
current_vpc_id = None

if not describe_vpcs():
    results.append('EC2 VPC -------------- X')
else:
    current_vpc_id = describe_vpcs()
    results.append('EC2 VPC -------------- O')

if not describe_subnets(current_vpc_id):
    results.append('EC2 Subnets -------------- X')
else:
    results.append('EC2 Subnets -------------- O')

if not describe_internet_gateways(current_vpc_id):
    results.append('EC2 Internet Gateway -------------- X')
else:
    results.append('EC2 Internet Gateway -------------- O')

if not describe_addressed():
    results.append('EC2 EIB -------------- X')
else:
    results.append('EC2 EIB -------------- O')

if not describe_nat_gateways(current_vpc_id):
    results.append('EC2 Nat Gateway -------------- X')
else:
    results.append('EC2 Nat Gateway -------------- O')

if not describe_route_tables(current_vpc_id):
    results.append('EC2 Route -------------- X')
else:
    results.append('EC2 Route -------------- O')

if not describe_security_groups(current_vpc_id):
    results.append('EC2 Security Group -------------- X')
else:
    results.append('EC2 Security Group -------------- O')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
