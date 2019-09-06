#!/usr/bin/env python3
import json
import sys

from run_common import AWSCli

command_list = list()
command_list.append('create')
command_list.append('create_cloudwatch_alarm')
command_list.append('create_cloudwatch_dashboard')
command_list.append('create_codebuild')
command_list.append('create_eb')
command_list.append('create_iam')
command_list.append('create_lambda')
command_list.append('create_rds')
command_list.append('create_s3')
command_list.append('create_ses')
command_list.append('create_sns')
command_list.append('create_sqs')
command_list.append('create_vpc')

command_list.append('terminate')
command_list.append('terminate_cloudwatch_alarm')
command_list.append('terminate_cloudwatch_dashboard')
command_list.append('terminate_codebuild')
command_list.append('terminate_eb')
command_list.append('terminate_eb_old_environment')
command_list.append('terminate_eb_old_environment_version')
command_list.append('terminate_iam')
command_list.append('terminate_lambda')
command_list.append('terminate_rds')
command_list.append('terminate_s3')
command_list.append('terminate_ses')
command_list.append('terminate_sns')
command_list.append('terminate_sqs')
command_list.append('terminate_vpc')

command_list.append('describe')
command_list.append('describe_cloudwatch')
command_list.append('describe_codebuild')
command_list.append('describe_eb')
command_list.append('describe_lambda')
command_list.append('describe_rds')
command_list.append('describe_sns')
command_list.append('describe_vpc')

command_list.append('export_cloudwatch_dashboard')
command_list.append('reset_template')


def print_usage():
    print('#' * 80)
    print('How to Play')
    print('')
    print('-' * 80)
    for cc in command_list:
        print('    ./run.py [OPTIONS] %s' % cc)
    print('-' * 80)
    print('    ./run.py [OPTIONS] -- [AWS CLI COMMAND]\t\t' +
          '(ex: \'./run.py -- aws ec2 describe-instances\')')
    print('    cd nova; ../run.py [OPTIONS] -- [EB CLI COMMAND]\t' +
          '(ex: \'cd nova; ../run.py -- eb list --region ap-northeast-2\')')
    print('-' * 80)
    print('OPTIONS')
    print('')
    print('`--force` or `-f`')
    print('\tAttempt to execute the commend without prompting for phase confirmation.')
    print('')
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

    if len(args) != 2:
        print_usage()
        sys.exit(0)

    if command not in command_list:
        print_usage()
        sys.exit(0)

    command = 'run_%s' % command
    if command == 'run_create':
        __import__('run_create_iam')
        __import__('run_create_vpc')
        __import__('run_create_rds')
        __import__('run_create_sqs')
        __import__('run_create_eb')
        __import__('run_create_sns')
        __import__('run_create_lambda')
        __import__('run_create_s3')
        __import__('run_create_ses')
        __import__('run_create_cloudwatch_alarm')
        __import__('run_create_cloudwatch_dashboard')
    elif command == 'run_terminate':
        __import__('run_terminate_cloudwatch_dashboard')
        __import__('run_terminate_cloudwatch_alarm')
        __import__('run_terminate_ses')
        __import__('run_terminate_s3')
        __import__('run_terminate_lambda')
        __import__('run_terminate_sns')
        __import__('run_terminate_eb')
        __import__('run_terminate_sqs')
        __import__('run_terminate_rds')
        __import__('run_terminate_vpc')
        __import__('run_terminate_iam')
    elif command == 'run_describe':
        __import__('run_describe_eb')
        __import__('run_describe_vpc')
        __import__('run_describe_rds')
        __import__('run_describe_lambda')
        __import__('run_describe_cloudwatch')
        __import__('run_describe_sns')
        __import__('run_describe_codebuild')
    else:
        __import__(command)
