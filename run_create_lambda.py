#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_create_lambda_cron import run_create_lambda_cron
from run_create_lambda_default import run_create_lambda_default
from run_create_lambda_event import run_create_lambda_event
from run_create_lambda_ses_sqs import run_create_lambda_ses_sqs
from run_create_lambda_sns import run_create_lambda_sns
from run_create_lambda_sqs import run_create_lambda_sqs

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def create_iam_for_lambda(git_folder_name, function_name):
    sleep_required = False

    function_name = function_name.replace('_', '-')

    role_name = f'aws-lambda-{function_name}-role'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role')

        role_file_path = f'file://template/{git_folder_name}/lambda/{function_name}/iam/role.json'
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', role_file_path]
        aws_cli.run(cmd)
        sleep_required = True

    policy_name = f'aws-lambda-{function_name}-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message('put iam role policy')

        policy_file_path = f'file://template/{git_folder_name}/lambda/{function_name}/iam/policy.json'
        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', policy_file_path]
        aws_cli.run(cmd)
        sleep_required = True

    return sleep_required


################################################################################
#
# start
#
################################################################################
print_session('create lambda')

################################################################################

lambdas_list = env['lambda']
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in lambdas_list:
        if lambda_env['NAME'] == target_lambda_name:
            target_lambda_name_exists = True
            if lambda_env['TYPE'] == 'default':
                run_create_lambda_default(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'cron':
                run_create_lambda_cron(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sns':
                run_create_lambda_sns(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sqs':
                run_create_lambda_sqs(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'ses_sqs':
                run_create_lambda_ses_sqs(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'event':
                run_create_lambda_event(lambda_env['NAME'], lambda_env)
                break
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    for lambda_env in lambdas_list:
        if lambda_env['TYPE'] == 'default':
            run_create_lambda_default(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_create_lambda_cron(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sns':
            run_create_lambda_sns(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sqs':
            run_create_lambda_sqs(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'ses_sqs':
            run_create_lambda_ses_sqs(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'event':
            run_create_lambda_event(lambda_env['NAME'], lambda_env)
            break
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
