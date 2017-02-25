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

db_allocated_storage = env['rds']['DB_SIZE']
db_backup_retention_period = env['rds']['BACKUP_RETENTION_PERIOD']
db_instance_class = env['rds']['DB_CLASS']
db_instance_id = env['rds']['DB_ID']
db_iops = env['rds']['IOPS']
db_multi_az = env['rds']['MULTI_AZ']
db_subnet_group_name = env['rds']['DB_SUBNET_NAME']
engine = env['rds']['ENGINE']
engine_version = env['rds']['ENGINE_VERSION']
license_model = env['rds']['LICENSE_MODEL']
master_user_name = env['rds']['USER_NAME']
master_user_password = env['rds']['USER_PASSWORD']
storage_type = env['rds']['STORAGE_TYPE']

cidr_subnet = aws_cli.cidr_subnet

################################################################################
#
# start
#
################################################################################
print_session('create rds')

################################################################################
print_message('get vpc id')

rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

if not rds_vpc_id or not eb_vpc_id:
    print('ERROR!!! No VPC found')
    raise Exception()

################################################################################
print_message('get security group id')

security_group_id = None
cmd = ['ec2', 'describe-security-groups']
result = aws_cli.run(cmd)
for r in result['SecurityGroups']:
    if r['VpcId'] != rds_vpc_id:
        continue
    if r['GroupName'] == 'default':
        continue
    if not security_group_id:
        security_group_id = r['GroupId']
    else:
        raise Exception()

################################################################################
print_message('create rds')

cmd = ['rds', 'create-db-instance']
cmd += ['--db-instance-identifier', db_instance_id]
cmd += ['--allocated-storage', db_allocated_storage]
cmd += ['--db-instance-class', db_instance_class]
cmd += ['--engine', engine]
cmd += ['--master-username', master_user_name]
cmd += ['--master-user-password', master_user_password]
cmd += ['--vpc-security-group-ids', security_group_id]
cmd += ['--db-subnet-group-name', db_subnet_group_name]
cmd += ['--backup-retention-period', db_backup_retention_period]
cmd += [db_multi_az]
cmd += ['--engine-version', engine_version]
cmd += ['--license-model', license_model]
cmd += ['--iops', db_iops]
cmd += ['--storage-type', storage_type]
aws_cli.run(cmd)
