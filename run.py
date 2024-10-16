#!/usr/bin/env python3.12
import json
import sys

from run_common import AWSCli

command_list = list()
command_list.append('create')
command_list.append('create_appstream_builder')
command_list.append('create_appstream_fleet_autoscale')
command_list.append('create_appstream_stack_fleet')
command_list.append('create_athena')
command_list.append('create_cloudfront')
command_list.append('create_cloudwatch_alarm')
command_list.append('create_cloudwatch_dashboard')
command_list.append('create_codebuild')
command_list.append('create_codedeploy_ramiel')
command_list.append('create_eb')
command_list.append('create_ec2_client_vpn')
command_list.append('create_ec2_keypair')
command_list.append('create_ec2_route53')
command_list.append('create_lambda')
command_list.append('create_ramiel_iam')
command_list.append('create_rds')
command_list.append('create_s3')
command_list.append('create_ses')
command_list.append('create_sns')
command_list.append('create_sqs')
command_list.append('create_vpc')

command_list.append('terminate')
command_list.append('terminate_appstream_builder')
command_list.append('terminate_appstream_fleet_autoscale')
command_list.append('terminate_appstream_stack_fleet')
command_list.append('terminate_athena')
command_list.append('terminate_cloudfront')
command_list.append('terminate_cloudwatch_alarm')
command_list.append('terminate_cloudwatch_dashboard')
command_list.append('terminate_codebuild')
command_list.append('terminate_eb')
command_list.append('terminate_eb_old_environment')
command_list.append('terminate_eb_old_environment_version')
command_list.append('terminate_ec2_client_vpn')
command_list.append('terminate_ec2_keypair')
command_list.append('terminate_ec2_route53')
command_list.append('terminate_lambda')
command_list.append('terminate_ramiel_iam')
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

command_list.append('reset_template')
command_list.append('reset_database')


def print_usage():
    print('#' * 80)
    print('How to Play')
    print('')
    print('-' * 80)
    for cc in command_list:
        print(f'    ./run.py [OPTIONS] {cc}')
    print('-' * 80)
    print('    ./run_create_eb.py [OPTIONS] <eb-environment-name>\t\t' +
          '(ex: \'./run_create_eb.py sachiel\')')
    print('    ./run_create_lambda.py [OPTIONS] <lambda-function-name>\t\t' +
          '(ex: \'./run_create_eb.py sachiel_send_email\')')
    print('    ./run_create_s3.py [OPTIONS] <s3-bucket-name>\t\t' +
          '(ex: \'./run_create_eb.py dv-hbsmith-web\')')
    print('-' * 80)
    print('    ./run.py [OPTIONS] -- [AWS CLI COMMAND]\t\t' +
          '(ex: \'./run.py -- aws ec2 describe-instances\')')
    print('-' * 80)
    print('OPTIONS')
    print('')
    print('`--force` or `-f`')
    print('\tAttempt to execute the commend without prompting for phase confirmation.')
    print('`--branch` or `-b`')
    print('\tAttempt to execute the command with specific branch.')
    print('`--region` or `-r`')
    print('\tAttempt to execute the command on specific region.')
    print('')
    print('#' * 80)


if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args(True)

    if len(args) < 2:
        print_usage()
        sys.exit(0)

    command = args[1]

    if command == 'aws':
        aws_cli = AWSCli()
        result = aws_cli.run(args[2:], ignore_error=True)
        if isinstance(result, dict):
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

    command = f'run_{command}'
    if command == 'run_create':
        __import__('run_create_vpc')
        __import__('run_create_rds')
        __import__('run_create_ec2_client_vpn')
        __import__('run_create_sqs')
        __import__('run_reset_database')
        __import__('run_create_eb')
        __import__('run_create_sns')
        __import__('run_create_athena')
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
        __import__('run_terminate_athena')
        __import__('run_terminate_sns')
        __import__('run_terminate_eb')
        __import__('run_terminate_sqs')
        __import__('run_terminate_rds')
        __import__('run_terminate_ec2_client_vpn')
        __import__('run_terminate_vpc')
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
