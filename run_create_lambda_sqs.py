#!/usr/bin/env python3
import os
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file


def run_create_lambda_sqs(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    description = settings['DESCRIPTION']
    folder_name = settings.get('FOLDER_NAME', name)
    function_name = name
    sqs_name = settings['SQS_NAME']
    phase = env['common']['PHASE']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    queue_arn = _get_queue_arn(aws_cli, sqs_name)
    build_info = _build(deploy_folder, function_name, phase, settings, template_name, template_path)
    if _check_need_update(aws_cli, function_name):
        _update(aws_cli, deploy_folder, function_name, build_info, queue_arn)
    else:
        _create(aws_cli, deploy_folder, description, function_name, build_info, queue_arn)


def _get_queue_arn(aws_cli, sqs_name):
    cmd = ['sqs', 'get-queue-url']
    cmd += ['--queue-name', sqs_name]
    queue_url = aws_cli.run(cmd)['QueueUrl']
    cmd = ['sqs', 'get-queue-attributes']
    cmd += ['--queue-url', queue_url]
    cmd += ['--attribute-names', 'QueueArn']
    return aws_cli.run(cmd)['Attributes']['QueueArn']


def _create(aws_cli, deploy_folder, description, function_name, build_info, queue_arn):
    print_session('create lambda: %s' % function_name)
    role_arn = aws_cli.get_role_arn('aws-lambda-sqs-role')
    cmd = ['lambda', 'create-function',
           '--function-name', function_name,
           '--description', description,
           '--zip-file', 'fileb://deploy.zip',
           '--role', role_arn,
           '--handler', 'lambda.handler',
           '--runtime', 'python3.6',
           '--tags', ','.join(build_info),
           '--timeout', '120']
    aws_cli.run(cmd, cwd=deploy_folder)
    print_message('give event permission')
    cmd = ['lambda', 'add-permission',
           '--function-name', function_name,
           '--statement-id', function_name + 'StatementId',
           '--action', 'lambda:InvokeFunction',
           '--principal', 'events.amazonaws.com',
           '--source-arn', queue_arn]
    aws_cli.run(cmd)
    print_message('create sqs event source for %s' % function_name)
    cmd = ['lambda', 'create-event-source-mapping',
           '--event-source-arn', queue_arn,
           '--function-name', function_name]
    aws_cli.run(cmd)


def _update(aws_cli, deploy_folder, function_name, build_info, queue_arn):
    print_session('update lambda: %s' % function_name)
    cmd = ['lambda', 'update-function-code',
           '--function-name', function_name,
           '--zip-file', 'fileb://deploy.zip']
    result = aws_cli.run(cmd, cwd=deploy_folder)
    function_arn = result['FunctionArn']
    print_message('update lambda tags')
    cmd = ['lambda', 'tag-resource',
           '--resource', function_arn,
           '--tags', ','.join(build_info)]
    aws_cli.run(cmd, cwd=deploy_folder)
    'aws lambda  --function-name sachiel_send_email'
    print_message('update sqs event source for %s' % function_name)
    cmd = ['lambda', 'list-event-source-mappings',
           '--function-name', function_name]
    mappings = aws_cli.run(cmd)['EventSourceMappings']
    for mapping in mappings:
        cmd = ['lambda', 'delete-event-source-mapping',
               '--uuid', mapping['UUID']]
        aws_cli.run(cmd)
    print_message('wait two minutes until deletion is complete')
    time.sleep(120)
    cmd = ['lambda', 'create-event-source-mapping',
           '--event-source-arn', queue_arn,
           '--function-name', function_name]
    aws_cli.run(cmd)


def _check_need_update(aws_cli, function_name):
    print_message('check previous version')
    need_update = False
    cmd = ['lambda', 'list-functions']
    result = aws_cli.run(cmd)
    for ff in result['Functions']:
        if function_name == ff['FunctionName']:
            need_update = True
            break
    return need_update


def _build(deploy_folder, function_name, phase, settings, template_name, template_path):
    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    print_session('packaging lambda: %s' % function_name)
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
    return [
        'git_hash_johanna=%s' % git_hash_johanna.decode('utf-8').strip(),
        'git_hash_%s=%s' % (template_name, git_hash_template.decode('utf-8').strip())
    ]
