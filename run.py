#!/usr/bin/env python3
from __future__ import print_function

import json
import sys

from run_common import AWSCli

command_list = list()
command_list.append('create')
command_list.append('create_nova')
command_list.append('create_vpc')
command_list.append('create_sqs')
command_list.append('terminate')
command_list.append('terminate_eb_old_environment')
command_list.append('terminate_nova')
command_list.append('terminate_vpc')


def print_usage():
    print('#' * 80)
    print('How to Play')
    print()
    print('-' * 80)
    for cc in command_list:
        print('    ./run.py ' + cc)
    print('-' * 80)
    print('    ./run.py [AWS CLI COMMAND]                 ' +
          '(ex: \'./run.py -- aws ec2 describe-instances\')')
    print('    cd [EB DIR]; ../run.py [EB CLI COMMAND]    ' +
          '(ex: \'cd nova; ../run.py -- eb list --region ap-northeast-2\')')
    print()
    print('#' * 80)


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args(True)

    if len(args) < 2:
        print_usage()
        sys.exit(0)

    command = args[1]

    if command == 'aws':
        aws_cli = AWSCli()
        result = aws_cli.run(args[2:], ignore_error=True)
        if type(result) == dict:
            print(json.dumps(result, sort_keys=True, indent=4))
        else:
            print(result)
        sys.exit(0)
    elif command == 'eb':
        aws_cli = AWSCli()
        result = aws_cli.run_eb(args[2:], ignore_error=True)
        print(result)
        sys.exit(0)

    if len(args) != 2:
        print_usage()
        sys.exit(0)

    if command not in command_list:
        print_usage()
        sys.exit(0)

    command = 'run_' + command
    if command == 'run_create':
        __import__('run_create_vpc')
        __import__('run_create_nova')
        __import__('run_create_sqs')
    elif command == 'run_terminate':
        __import__('run_terminate_nova')
        __import__('run_terminate_vpc')
    else:
        __import__(command)
