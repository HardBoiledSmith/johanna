#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

db_instance_name = env['rds']['DB_NAME']
db_instance_class = env['rds']['DB_CLASS']
db_subnet_group_name = env['rds']['DB_SUBNET_NAME']
master_user_name = env['rds']['USER_NAME']
master_user_password = env['rds']['USER_PASSWORD']
engine = env['rds']['ENGINE']
allocated_storage = env['rds']['DB_SIZE']

cidr_subnet = aws_cli.cidr_subnet

################################################################################
#
# start
#
################################################################################
print_session('create rds')

################################################################################
print_message('get vpc id')

eb_vpc_id = aws_cli.get_vpc_id()

if not eb_vpc_id:
    print('ERROR!!! No VPC found')
    raise Exception()

################################################################################
print_message('get subnet id')

subnet_id_1 = None
subnet_id_2 = None

cmd = ['ec2', 'describe-subnets']
result = aws_cli.run(cmd)
for r in result['Subnets']:
    if r['VpcId'] != eb_vpc_id:
        continue
    if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
        subnet_id_1 = r['SubnetId']
    if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
        subnet_id_2 = r['SubnetId']

################################################################################
print_message('get security group id')

security_group_id = None
cmd = ['ec2', 'describe-security-groups']
result = aws_cli.run(cmd)
for r in result['SecurityGroups']:
    if r['VpcId'] != eb_vpc_id:
        continue
    if r['GroupName'] == 'eb_public':
        security_group_id = r['GroupId']
        break

###############################################################################
print_message('create rds subnet group')

cmd = ['rds', 'create-db-subnet-group']
cmd += ['--db-subnet-group-name', db_subnet_group_name]
cmd += ['--db-subnet-group-description', db_subnet_group_name]
cmd += ['--subnet-ids', subnet_id_1, subnet_id_2]
aws_cli.run(cmd)

################################################################################
print_message('create rds')

cmd = ['rds', 'create-db-instance']
cmd += ['--db-instance-identifier', db_instance_name]
cmd += ['--db-instance-class', db_instance_class]
cmd += ['--engine', engine]
cmd += ['--master-username', master_user_name]
cmd += ['--master-user-password', master_user_password]
cmd += ['--allocated-storage', allocated_storage]
cmd += ['--vpc-security-group-ids', security_group_id]
cmd += ['--db-subnet-group-name', db_subnet_group_name]
aws_cli.run(cmd)
