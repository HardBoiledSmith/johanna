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

db_instance_id = env['rds']['DB_ID']

################################################################################
#
# Start
#
################################################################################
print_session('terminate rds')

################################################################################
print_message('delete rds')

cmd = ['rds', 'delete-db-instance']
cmd += ['--db-instance-identifier', db_instance_id]
cmd += ['--skip-final-snapshot']
aws_cli.run(cmd, ignore_error=True)
