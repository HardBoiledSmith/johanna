#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()


def describe_db_subnet_groups():
    cmd = ['rds', 'describe-db-subnet-groups']
    cmd += ['--db-subnet-group-name', env['rds']['DB_SUBNET_NAME']]
    try:
        aws_cli.run(cmd)
    except:
        return False

    return True


def describe_db_instances():
    cmd = ['rds', 'describe-db-instances']
    cmd += ['--db-instance-identifier', env['rds']['DB_NAME']]

    try:
        aws_cli.run(cmd)
    except:
        return False

    return True


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()

if describe_db_subnet_groups() == False:
   results.append('RDS Subnet Group -------------- X')
else:
   results.append('RDS Subnet Group -------------- O')

if describe_db_instances() == False:
   results.append('RDS Instance -------------- X')
else:
   results.append('RDS Instance -------------- O')

print('#' * 80)

for r in results:
   print(r)

print('#' * 80)
