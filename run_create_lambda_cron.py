#!/usr/bin/env python3
import os
import re
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file
from run_create_lambda_iam import create_iam_for_lambda


def run_create_lambda_cron(function_name, settings, options):
    aws_cli = AWSCli(settings['AWS_REGION'])

    description = settings['DESCRIPTION']
    folder_name = settings.get('FOLDER_NAME', function_name)
    git_url = settings['GIT_URL']
    phase = env['common']['PHASE']
    schedule_expression = settings['SCHEDULE_EXPRESSION']
    concurrency = settings.get('CONCURRENCY', None)

    mm = re.match(r'^.+/(.+)\.git$', git_url)
    if not mm:
        raise Exception()
    git_folder_name = mm.group(1)

    ################################################################################
    print_session('create %s' % function_name)

    ################################################################################
    print_message('download template: %s' % git_folder_name)

    subprocess.Popen(['mkdir', '-p', './template']).communicate()

    if not os.path.exists('template/%s' % git_folder_name):
        branch = options.get('branch', 'master' if phase == 'dv' else phase)
        print(f'branch: {branch}')
        git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
        subprocess.Popen(git_command, cwd='template').communicate()
        if not os.path.exists('template/%s' % git_folder_name):
            raise Exception()

    deploy_folder = 'template/%s/lambda/%s' % (git_folder_name, folder_name)

    ################################################################################
    print_message(f'create iam: {function_name}')

    role_created = create_iam_for_lambda(git_folder_name, folder_name, function_name)
    if role_created:
        print_message('wait 10 seconds to let iam role and policy propagated to all regions...')
        time.sleep(10)

    ################################################################################
    print_message('packaging lambda: %s' % function_name)

    print_message('cleanup generated files')
    subprocess.Popen(['git', 'clean', '-d', '-f', '-x'], cwd=deploy_folder).communicate()

    requirements_path = '%s/requirements.txt' % deploy_folder
    if os.path.exists(requirements_path):
        print_message('install dependencies')

        cmd = ['pip3', 'install', '-r', requirements_path, '-t', deploy_folder]
        subprocess.Popen(cmd).communicate()

    settings_path = '%s/settings_local_sample.py' % deploy_folder
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

    replaced_function_name = function_name.replace('_', '-')
    role_arn = aws_cli.get_role_arn(f'lambda-{replaced_function_name}-role')

    git_hash_johanna = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                         stdout=subprocess.PIPE,
                                         cwd='template/%s' % git_folder_name).communicate()[0]

    tags = list()
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_johanna=%s' % git_hash_johanna.decode('utf-8').strip())
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_%s=%s' % (git_folder_name, git_hash_template.decode('utf-8').strip()))

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
        result = aws_cli.run(cmd, cwd=deploy_folder)

        print_message('wait few seconds until function is updated')
        time.sleep(10)

        function_arn = result['FunctionArn']

        cmd = ['lambda', 'update-function-configuration',
               '--function-name', function_name,
               '--description', description,
               '--role', role_arn,
               '--handler', 'lambda.handler',
               '--runtime', 'python3.7',
               '--timeout', '900']
        if settings.get('memory_size'):
            cmd += ['--memory-size', settings['memory_size']]
        aws_cli.run(cmd, cwd=deploy_folder)

        print_message('update lambda tags')

        cmd = ['lambda', 'tag-resource',
               '--resource', function_arn,
               '--tags', ','.join(tags)]
        aws_cli.run(cmd, cwd=deploy_folder)

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
           '--runtime', 'python3.7',
           '--tags', ','.join(tags),
           '--timeout', '900']
    if settings.get('memory_size'):
        cmd += ['--memory-size', settings['memory_size']]
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

    if concurrency:
        cmd = ['lambda', 'put-function-concurrency']
        cmd += ['--function-name', function_name]
        cmd += ['--reserved-concurrent-executions', concurrency]
