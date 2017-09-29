#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

db_instance_id = env['rds']['DB_INSTANCE_ID']
engine = env['rds']['ENGINE']

################################################################################
#
# Start
#
################################################################################
print_session('terminate rds')

################################################################################
print_message('delete rds')

if engine == 'mysql':
    cmd = ['rds', 'delete-db-instance']
    cmd += ['--db-instance-identifier', db_instance_id]
    cmd += ['--skip-final-snapshot']
    aws_cli.run(cmd, ignore_error=True)
elif engine == 'aurora':
    cmd = ['rds', 'delete-db-instance']
    cmd += ['--db-instance-identifier', db_instance_id]
    cmd += ['--skip-final-snapshot']
    aws_cli.run(cmd, ignore_error=True)
    cmd = ['rds', 'delete-db-cluster']
    cmd += ['--db-cluster-identifier', env['rds']['DB_CLUSTER_ID']]
    cmd += ['--skip-final-snapshot']
    aws_cli.run(cmd, ignore_error=True)
else:
    raise Exception()
