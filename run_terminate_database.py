#!/usr/bin/env python3
from __future__ import print_function

import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

db_instance_name = env['rds']['DB_NAME']
db_subnet_group_name = env['rds']['DB_SUBNET_NAME']

################################################################################
#
# Start
#
################################################################################
print_session('terminate database')

################################################################################
print_message('delete database')

cmd = ['rds', 'delete-db-instance']
cmd += ['--db-instance-identifier', db_instance_name]
cmd += ['--skip-final-snapshot', '']

aws_cli.run(cmd, ignore_error=True)

###############################################################################
print_message('delete database subnet group')

elapsed_time = 0
while True:
     cmd = ['rds', 'describe-db-instances']
     
     result = aws_cli.run(cmd)

     if result['DBInstances'] == []:
        break

     print('deleting the environment... (elapsed time: \'%d\' seconds)' % elapsed_time)
     time.sleep(5)
     elapsed_time += 5

cmd = ['rds', 'delete-db-subnet-group']
cmd += ['--db-subnet-group-name', db_subnet_group_name]
aws_cli.run(cmd, ignore_error=True)
