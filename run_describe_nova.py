#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_environments():
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]

    # noinspection PyBroadException
    try:
        result = aws_cli.run(cmd)
    except:
        return False

    return result


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()

if not describe_environments():
    results.append('Nova -------------- X')
else:
    results.append('Nova -------------- O')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
