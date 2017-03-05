#!/usr/bin/env python3
from __future__ import print_function

import os
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import download_template
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file

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
        print_message('wait few minutes to iam role and policy propagated...')
        time.sleep(60)


def run_create_default_lambda(name, settings):
    description = settings['DESCRIPTION']
    function_name = settings['NAME']
    phase = env['common']['PHASE']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, name)

    ################################################################################
    gitignore_path = '%s/.gitignore' % deploy_folder
    if os.path.exists(gitignore_path):
        ll = read_file(gitignore_path)
        print_message('cleanup generated files')
        subprocess.Popen(' '.join(['rm', '-rf'] + ll), shell=True, cwd=deploy_folder).communicate()

    print_session('create lambda: %s' % function_name)

    print_message('install dependencies')

    requirements_path = '%s/requirements.txt' % deploy_folder
    if os.path.exists(requirements_path):
        print_message('install dependencies')

        cmd = ['pip', 'install', '-r', requirements_path, '-t', deploy_folder]
        subprocess.Popen(cmd).communicate()

    settings_path = '%s/settings_local.py.sample' % deploy_folder
    if os.path.exists(settings_path):
        print_message('create environment values')

        lines = read_file(settings_path)
        option_list = list()
        option_list.append(['PHASE', phase])
        for key in settings:
            value = settings[key]
            option_list.append([key, value])
        for oo in option_list:
            lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
        write_file('%s/settings_local.py' % deploy_folder, lines)

    print_message('zip files')

    cmd = ['zip', '-r', 'deploy.zip', '.']
    subprocess.Popen(cmd, cwd=deploy_folder).communicate()

    print_message('create lambda function')

    role_arn = aws_cli.get_role_arn('aws-lambda-default-role')

    cmd = ['lambda', 'create-function',
           '--function-name', function_name,
           '--description', description,
           '--zip-file', 'fileb://deploy.zip',
           '--role', role_arn,
           '--handler', 'lambda.handler',
           '--runtime', 'python2.7']
    aws_cli.run(cmd, cwd=deploy_folder)


def run_create_cron_lambda(name, settings):
    description = settings['DESCRIPTION']
    function_name = settings['NAME']
    phase = env['common']['PHASE']
    schedule_expression = settings['SCHEDULE_EXPRESSION']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, name)

    ################################################################################
    gitignore_path = '%s/.gitignore' % deploy_folder
    if os.path.exists(gitignore_path):
        ll = read_file(gitignore_path)
        print_message('cleanup generated files')
        subprocess.Popen(' '.join(['rm', '-rf'] + ll), shell=True, cwd=deploy_folder).communicate()

    print_session('create lambda: %s' % function_name)

    requirements_path = '%s/requirements.txt' % deploy_folder
    if os.path.exists(requirements_path):
        print_message('install dependencies')

        cmd = ['pip', 'install', '-r', requirements_path, '-t', deploy_folder]
        subprocess.Popen(cmd).communicate()

    settings_path = '%s/settings_local.py.sample' % deploy_folder
    if os.path.exists(settings_path):
        print_message('create environment values')

        lines = read_file(settings_path)
        option_list = list()
        option_list.append(['PHASE', phase])
        for key in settings:
            value = settings[key]
            option_list.append([key, value])
        for oo in option_list:
            lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
        write_file('%s/settings_local.py' % deploy_folder, lines)

    print_message('zip files')

    cmd = ['zip', '-r', 'deploy.zip', '.']
    subprocess.Popen(cmd, cwd=deploy_folder).communicate()

    print_message('create lambda function')

    role_arn = aws_cli.get_role_arn('aws-lambda-default-role')

    cmd = ['lambda', 'create-function',
           '--function-name', function_name,
           '--description', description,
           '--zip-file', 'fileb://deploy.zip',
           '--role', role_arn,
           '--handler', 'lambda.handler',
           '--runtime', 'python2.7']
    result = aws_cli.run(cmd, cwd=deploy_folder)

    function_arn = result['FunctionArn']

    print_message('create cron event')

    cmd = ['events', 'put-rule',
           '--name', function_name + 'CronRule',
           '--description', description,
           '--schedule-expression', schedule_expression]
    result = aws_cli.run(cmd)

    rule_arn = result['RuleArn']

    print_message('give event permission')

    cmd = ['lambda', 'add-permission',
           '--function-name', function_name,
           '--statement-id', function_name + 'StatementId',
           '--action', 'lambda:InvokeFunction',
           '--principal', 'events.amazonaws.com',
           '--source-arn', rule_arn]
    aws_cli.run(cmd)

    print_message('link event and lambda')

    cmd = ['events', 'put-targets',
           '--rule', function_name + 'CronRule',
           '--targets', '{"Id" : "1", "Arn": "%s"}' % function_arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
if not os.path.exists('template/%s' % env['template']['NAME']):
    download_template()

################################################################################
print_session('create lambda')

create_iam_for_lambda()

lambda_env_list = env['lambda']
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in lambda_env_list:
        if lambda_env['NAME'] == target_lambda_name:
            target_lambda_name_exists = True
            if lambda_env['TYPE'] == 'default':
                run_create_default_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'cron':
                run_create_cron_lambda(lambda_env['NAME'], lambda_env)
                break
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    for lambda_env in lambda_env_list:
        if lambda_env['TYPE'] == 'default':
            run_create_default_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_create_cron_lambda(lambda_env['NAME'], lambda_env)
            continue
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
