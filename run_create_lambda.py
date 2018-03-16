#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session
from run_create_lambda_cron import run_create_lambda_cron
from run_create_lambda_default import run_create_lambda_default
from run_create_lambda_sns import run_create_lambda_sns

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def create_iam_for_lambda():
    sleep_required = False

    role_name = 'aws-lambda-default-role'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role')

        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-lambda-default-role.json']
        aws_cli.run(cmd)
        sleep_required = True

    policy_name = 'aws-lambda-default-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message('put iam role policy')

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', 'file://aws_iam/aws-lambda-default-policy.json']
        aws_cli.run(cmd)
        sleep_required = True

    if sleep_required:
        print_message('wait two minutes to let iam role and policy propagated to all regions...')
        time.sleep(120)


################################################################################
#
# start
#
################################################################################
print_session('create lambda')

################################################################################
check_template_availability()

create_iam_for_lambda()

_lambda = env['lambda']
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in _lambda:
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
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    for lambda_env in _lambda:
        if lambda_env['TYPE'] == 'default':
            run_create_lambda_default(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_create_lambda_cron(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sns':
            run_create_lambda_sns(lambda_env['NAME'], lambda_env)
            continue
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
