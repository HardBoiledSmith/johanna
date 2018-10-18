#!/usr/bin/env python3
import os
import subprocess

from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def run_create_lambda_cron(name, settings):
    aws_cli = AWSCli()
    description = settings['DESCRIPTION']
    function_name = name
    phase = settings['PHASE']
    git_url = settings['GIT_URL']
    schedule_expression = settings['SCHEDULE_EXPRESSION']
    source_path = settings['SOURCE_PATH']
    environment_variables = settings['ENVIRONMENT_VARIABLES']

    ################################################################################
    print_message('git clone')

    cmd = ['rm', '-rf', 'template/kaji']
    subprocess.Popen(cmd).communicate()

    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]

    subprocess.Popen(git_command, cwd='template').communicate()
    if not os.path.exists('%s' % source_path):
        raise Exception()

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=source_path).communicate()[0]

    ################################################################################
    print_session('packaging lambda: %s' % function_name)

    print_message('create environment values')
    with open('%s/settings_local.py' % source_path, 'w') as f:
        for key in environment_variables:
            f.write('%s = \'%s\'' % (key, environment_variables[key]))
        f.close()

    requirements_path = '%s/requirements.txt' % source_path
    if os.path.exists(requirements_path):
        print_message('install dependencies')

        cmd = ['pip3', 'install', '-r', requirements_path, '-t', source_path]
        subprocess.Popen(cmd).communicate()

    print_message('zip files')

    cmd = ['zip', '-r', 'deploy.zip', '.']
    subprocess.Popen(cmd, cwd=source_path).communicate()

    print_message('create lambda function')

    role_arn = aws_cli.get_role_arn('aws-lambda-default-role')

    tags = list()
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_johanna=%s' % git_hash_johanna.decode('utf-8').strip())
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_%s=%s' % (source_path, git_hash_template.decode('utf-8').strip()))

    ################################################################################
    print_message('check previous version')

    need_update = False
    cmd = ['lambda', 'list-functions']
    result = aws_cli.run(cmd)
    for ff in result['Functions']:
        if function_name == ff['FunctionName']:
            need_update = True
            break

    ################################################################################
    if need_update:
        print_session('update lambda: %s' % function_name)

        cmd = ['lambda', 'update-function-code',
               '--function-name', function_name,
               '--zip-file', 'fileb://deploy.zip']
        result = aws_cli.run(cmd, cwd=source_path)

        function_arn = result['FunctionArn']

        print_message('update lambda tags')

        cmd = ['lambda', 'tag-resource',
               '--resource', function_arn,
               '--tags', ','.join(tags)]
        aws_cli.run(cmd, cwd=source_path)

        print_message('update cron event')

        cmd = ['events', 'put-rule',
               '--name', function_name + 'CronRule',
               '--description', description,
               '--schedule-expression', schedule_expression]
        aws_cli.run(cmd)
        return

    ################################################################################
    print_session('create lambda: %s' % function_name)

    cmd = ['lambda', 'create-function',
           '--function-name', function_name,
           '--description', description,
           '--zip-file', 'fileb://deploy.zip',
           '--role', role_arn,
           '--handler', 'lambda.handler',
           '--runtime', 'python3.6',
           '--tags', ','.join(tags),
           '--timeout', '120']
    result = aws_cli.run(cmd, cwd=source_path)

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
