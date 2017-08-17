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

db_backup_retention_period = env['rds']['BACKUP_RETENTION_PERIOD']
db_instance_class = env['rds']['DB_CLASS']
db_instance_id = env['rds']['DB_INSTANCE_ID']
db_iops = env['rds']['IOPS']
db_multi_az = env['rds']['MULTI_AZ']
db_subnet_group_name = env['rds']['DB_SUBNET_NAME']
engine = env['rds']['ENGINE']
engine_version = env['rds']['ENGINE_VERSION']
license_model = env['rds']['LICENSE_MODEL']
master_user_name = env['rds']['USER_NAME']
master_user_password = env['rds']['USER_PASSWORD']

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

if engine == 'mysql':
    cmd = ['rds', 'create-db-instance']
    cmd += ['--allocated-storage', env['rds']['DB_SIZE']]
    cmd += ['--backup-retention-period', db_backup_retention_period]
    cmd += ['--db-instance-class', db_instance_class]
    cmd += ['--db-instance-identifier', db_instance_id]
    cmd += ['--db-subnet-group-name', db_subnet_group_name]
    cmd += ['--engine', engine]
    cmd += ['--engine-version', engine_version]
    cmd += ['--iops', db_iops]
    cmd += ['--license-model', license_model]
    cmd += ['--master-user-password', master_user_password]
    cmd += ['--master-username', master_user_name]
    cmd += ['--storage-type', env['rds']['STORAGE_TYPE']]
    cmd += ['--vpc-security-group-ids', security_group_id]
    cmd += [db_multi_az]
    aws_cli.run(cmd)
elif engine == 'aurora':
    cmd = ['rds', 'create-db-cluster']
    cmd += ['--backup-retention-period', db_backup_retention_period]
    cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
    cmd += ['--db-subnet-group-name', db_subnet_group_name]
    cmd += ['--engine', engine]
    cmd += ['--engine-version', engine_version]
    cmd += ['--master-user-password', master_user_password]
    cmd += ['--master-username', master_user_name]
    cmd += ['--vpc-security-group-ids', security_group_id]
    aws_cli.run(cmd)
    cmd = ['rds', 'create-db-instance']
    cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
    cmd += ['--db-instance-class', db_instance_class]
    cmd += ['--db-instance-identifier', db_instance_id]
    cmd += ['--engine', engine]
    cmd += ['--iops', db_iops]
    cmd += ['--license-model', license_model]
    cmd += [db_multi_az]
    aws_cli.run(cmd)
else:
    raise Exception()
