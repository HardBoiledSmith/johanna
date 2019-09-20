#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()


def terminate_iam_for_rds():
    print_message('delete iam role')

    cc = ['iam', 'detach-role-policy']
    cc += ['--role-name', 'rds-monitoring-role']
    cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole']
    aws_cli.run(cc, ignore_error=True)

    cc = ['iam', 'delete-role']
    cc += ['--role-name', 'rds-monitoring-role']
    aws_cli.run(cc, ignore_error=True)


################################################################################
#
# Start
#
################################################################################
print_session('terminate rds')

################################################################################
print_message('delete rds')

cmd = ['rds', 'describe-db-clusters']
cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
result = aws_cli.run(cmd, ignore_error=True)

if type(result) == dict:
    cluster_list = result.get('DBClusters', list())
    for cc in cluster_list:
        member_list = cc['DBClusterMembers']
        for mm in member_list:
            cmd = ['rds', 'delete-db-instance']
            cmd += ['--db-instance-identifier', mm['DBInstanceIdentifier']]
            cmd += ['--skip-final-snapshot']
            aws_cli.run(cmd, ignore_error=True)

cmd = ['rds', 'delete-db-cluster']
cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
cmd += ['--skip-final-snapshot']
aws_cli.run(cmd, ignore_error=True)
terminate_iam_for_rds()
