#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_db_subnet_groups():
    cmd = ['rds', 'describe-db-subnet-groups']
    cmd += ['--db-subnet-group-name', env['rds']['DB_SUBNET_NAME']]
    # noinspection PyBroadException
    try:
        aws_cli.run(cmd)
    except:
        return False

    return True


def describe_db_instances():
    cmd = ['rds', 'describe-db-instances']
    cmd += ['--db-instance-identifier', env['rds']['DB_NAME']]

    # noinspection PyBroadException
    try:
        aws_cli.run(cmd)
    except:
        return False

    return True


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()

if not describe_db_subnet_groups():
    results.append('RDS Subnet Group -------------- X')
else:
    results.append('RDS Subnet Group -------------- O')

if not describe_db_instances():
    results.append('RDS Instance -------------- X')
else:
    results.append('RDS Instance -------------- O')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
