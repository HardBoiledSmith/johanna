#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def terminate_iam_for_lambda():
    print_message('delete iam role policy')

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', 'aws-lambda-default-role']
    cmd += ['--policy-name', 'aws-lambda-default-policy']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete iam role')

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', 'aws-lambda-default-role']
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_default_lambda(name, settings):
    function_name = settings['NAME']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


def run_terminate_cron_lambda(name, settings):
    function_name = settings['NAME']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

    print_message('unlink event and lambda')

    cmd = ['events', 'remove-targets',
           '--rule', function_name + 'CronRule',
           '--ids', '["1"]']
    aws_cli.run(cmd, ignore_error=True)

    print_message('remove event permission')

    cmd = ['lambda', 'remove-permission',
           '--function-name', function_name,
           '--statement-id', function_name + 'StatementId']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete cron event')

    cmd = ['events', 'delete-rule',
           '--name', function_name + 'CronRule']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate lambda')

lambda_env_list = env['lambda']
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in lambda_env_list:
        if lambda_env['NAME'] == target_lambda_name:
            target_lambda_name_exists = True
            if lambda_env['TYPE'] == 'default':
                run_terminate_default_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'cron':
                run_terminate_cron_lambda(lambda_env['NAME'], lambda_env)
                break
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    for lambda_env in lambda_env_list:
        if lambda_env['TYPE'] == 'default':
            run_terminate_default_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_terminate_cron_lambda(lambda_env['NAME'], lambda_env)
            continue
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
    terminate_iam_for_lambda()
