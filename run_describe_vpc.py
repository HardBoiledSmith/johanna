#!/usr/bin/env python3
from run_common import AWSCli

aws_cli = AWSCli()


def describe_eb_vpc():
    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()
    if eb_vpc_id is None:
        return False
    else:
        return eb_vpc_id


def describe_eb_subnets(vpc_id=None):
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
        result = aws_cli.run(cmd)
        if not result['NatGateways']:
            return False
    except Exception:
        return False

    return True


def describe_eb_route_tables(vpc_id=None):
    cmd = ['ec2', 'describe-route-tables']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['RouteTables']:
        return False
    else:
        return True


def describe_eb_security_groups(vpc_id):
    if not vpc_id:
        return False

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['SecurityGroups']:
        return False
    else:
        return True


def describe_rds_vpc():
    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()
    if rds_vpc_id is None:
        return False
    else:
        return rds_vpc_id


def describe_rds_subnets(vpc_id=None):
    cmd = ['rds', 'describe-db-subnet-groups']
    result = aws_cli.run(cmd, ignore_error=True)

    group_list = result['DBSubnetGroups']
    for group in group_list:
        if group['VpcId'] == vpc_id:
            return True
    return False


def describe_rds_route_tables(vpc_id=None):
    cmd = ['ec2', 'describe-route-tables']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['RouteTables']:
        return False
    else:
        return True


def describe_rds_security_groups(vpc_id):
    if not vpc_id:
        return False

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters=Name=vpc-id,Values=%s' % vpc_id]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['SecurityGroups']:
        return False
    else:
        return True


def describe_vpc_peering_connection(vpc_id_1, vpc_id_2):
    filter_1 = 'Name=accepter-vpc-info.vpc-id,Values=%s' % vpc_id_1
    filter_2 = 'Name=requester-vpc-info.vpc-id,Values=%s' % vpc_id_2
    cmd = ['ec2', 'describe-vpc-peering-connections']
    cmd += ['--filters=%s,%s' % (filter_1, filter_2)]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['VpcPeeringConnections']:
        return False
    else:
        return True


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()
current_eb_vpc_id = None

if not describe_eb_vpc():
    results.append(['EC2 VPC', 'X'])
else:
    current_eb_vpc_id = describe_eb_vpc()
    results.append(['EC2 VPC', 'O'])

if not describe_eb_subnets(current_eb_vpc_id):
    results.append(['EC2 Subnets', 'X'])
else:
    results.append(['EC2 Subnets', 'O'])

if not describe_internet_gateways(current_eb_vpc_id):
    results.append(['EC2 Internet Gateway', 'X'])
else:
    results.append(['EC2 Internet Gateway', 'O'])

if not describe_addressed():
    results.append(['EC2 EIP', 'X'])
else:
    results.append(['EC2 EIP', 'O'])

if not describe_nat_gateways(current_eb_vpc_id):
    results.append(['EC2 Nat Gateway', 'X'])
else:
    results.append(['EC2 Nat Gateway', 'O'])

if not describe_eb_route_tables(current_eb_vpc_id):
    results.append(['EC2 Route', 'X'])
else:
    results.append(['EC2 Route', 'O'])

if not describe_eb_security_groups(current_eb_vpc_id):
    results.append(['EC2 Security Group', 'X'])
else:
    results.append(['EC2 Security Group', 'O'])

print('#' * 80)

for r in results:
    print('%-25s -------------- %s' % (r[0], r[1]))

print('#' * 80)

results = list()

current_rds_vpc_id = None

if not describe_rds_vpc():
    results.append(['RDS VPC', 'X'])
else:
    current_rds_vpc_id = describe_rds_vpc()
    results.append(['RDS VPC', 'O'])

if not describe_rds_subnets(current_rds_vpc_id):
    results.append(['RDS Subnets', 'X'])
else:
    results.append(['RDS Subnets', 'O'])

if not describe_rds_route_tables(current_rds_vpc_id):
    results.append(['RDS Route', 'X'])
else:
    results.append(['RDS Route', 'O'])

if not describe_rds_security_groups(current_rds_vpc_id):
    results.append(['RDS Security Group', 'X'])
else:
    results.append(['RDS Security Group', 'O'])

if not describe_vpc_peering_connection(current_eb_vpc_id, current_rds_vpc_id):
    results.append(['VPC Peering Connection', 'X'])
else:
    results.append(['VPC Peering Connection', 'O'])

print('#' * 80)

for r in results:
    print('%-25s -------------- %s' % (r[0], r[1]))

print('#' * 80)
