#!/usr/bin/env python3
import datetime
import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()


def create_iam_for_rds():
    sleep_required = False

    role_name = 'rds-monitoring-role'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role')

        cc = ['iam', 'create-role']
        cc += ['--role-name', role_name]
        cc += ['--assume-role-policy-document', 'file://aws_iam/rds-monitoring-role.json']
        aws_cli.run(cc)

        cc = ['iam', 'attach-role-policy']
        cc += ['--role-name', role_name]
        cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole']
        aws_cli.run(cc)
        sleep_required = True

    if sleep_required:
        print_message('wait 120 seconds to let iam role and policy propagated to all regions...')
        time.sleep(120)


db_backup_retention_period = env['rds']['BACKUP_RETENTION_PERIOD']
db_instance_class = env['rds']['DB_CLASS']
db_instance_id = env['rds']['DB_INSTANCE_ID']
db_iops = env['rds']['IOPS']
db_multi_az = env['rds']['MULTI_AZ']
db_subnet_group_name = env['rds']['DB_SUBNET_NAME']
license_model = env['rds']['LICENSE_MODEL']
logs_export_to_cloudwatch = json.dumps(['error', 'general', 'audit', 'slowquery'])
master_user_name = env['rds']['USER_NAME']
master_user_password = env['rds']['USER_PASSWORD']
monitoring_interval = env['rds']['MONITORING_INTERVAL']

cidr_subnet = aws_cli.cidr_subnet

################################################################################
#
# start
#
################################################################################
print_session('create rds')

create_iam_for_rds()

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
print_message('get rds role arn')

monitoring_role_arn = aws_cli.get_role_arn('rds-monitoring-role')

################################################################################
print_message('create rds')

cmd = ['rds', 'create-db-cluster']
cmd += ['--backup-retention-period', db_backup_retention_period]
cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
cmd += ['--db-subnet-group-name', db_subnet_group_name]
cmd += ['--enable-cloudwatch-logs-exports', logs_export_to_cloudwatch]
cmd += ['--engine', 'aurora-mysql']
cmd += ['--engine-version', '5.7.mysql_aurora.2.04.5']
cmd += ['--master-user-password', master_user_password]
cmd += ['--master-username', master_user_name]
cmd += ['--vpc-security-group-ids', security_group_id]
aws_cli.run(cmd)

aws_cli.wait_create_rds_cluster(env['rds']['DB_CLUSTER_ID'])

cmd = ['rds', 'create-db-instance']
cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
cmd += ['--db-instance-class', db_instance_class]
cmd += ['--db-instance-identifier', db_instance_id]
cmd += ['--engine', 'aurora-mysql']
cmd += ['--iops', db_iops]
cmd += ['--license-model', license_model]
cmd += ['--monitoring-interval', monitoring_interval]
cmd += ['--monitoring-role-arn', monitoring_role_arn]
aws_cli.run(cmd)

if db_multi_az == '--multi-az':
    cmd = ['rds', 'create-db-instance']
    cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
    ss = datetime.datetime.today().strftime('%Y%m%d')
    cmd += ['--db-instance-identifier', '%s-%s' % (db_instance_id, ss)]
    cmd += ['--db-instance-class', db_instance_class]
    cmd += ['--engine', 'aurora-mysql']
    aws_cli.run(cmd)
