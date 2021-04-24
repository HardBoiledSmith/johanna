#!/usr/bin/env python3
import json
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


def run_create_lambda_ses_sqs(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])
    aws_cli_us_east_1 = AWSCli('us-east-1')

    description = settings['DESCRIPTION']
    folder_name = settings.get('FOLDER_NAME', function_name)
    git_url = settings['GIT_URL']
    phase = env['common']['PHASE']
    sqs_name = settings['SQS_NAME']

    mm = re.match(r'^.+/(.+)\.git$', git_url)
    if not mm:
        raise Exception()
    git_folder_name = mm.group(1)

    ################################################################################
    print_session(f'create {function_name}')

    ################################################################################
    print_message(f'download template: {git_folder_name}')

    subprocess.Popen(['mkdir', '-p', './template']).communicate()

    if not os.path.exists(f'template/{git_folder_name}'):
        if phase == 'dv':
            git_command = ['git', 'clone', '--depth=1', git_url]

        else:
            git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
        subprocess.Popen(git_command, cwd='template').communicate()
        if not os.path.exists(f'template/{git_folder_name}'):
            raise Exception()

    deploy_folder = f'template/{git_folder_name}/lambda/{folder_name}'

    ################################################################################
    cmd = ['sqs', 'get-queue-url']
    cmd += ['--queue-name', sqs_name]
    queue_url = aws_cli.run(cmd)['QueueUrl']

    cmd = ['sqs', 'get-queue-attributes']
    cmd += ['--queue-url', queue_url]
    cmd += ['--attribute-names', 'QueueArn']
    queue_arn = aws_cli.run(cmd)['Attributes']['QueueArn']

    ################################################################################
    print_message(f'creating templates(us-east-1): {function_name}')

    cmd = ['ses', 'list-templates']
    current_templates_list = aws_cli_us_east_1.run(cmd)['TemplatesMetadata']
    current_templates_name_list = [tt['Name'] for tt in current_templates_list]

    templates_information_list = json.loads(open(f'{deploy_folder}/templates/templates.json').read())

    subprocess.Popen(['mkdir', '-p', f'{deploy_folder}/templates/tmp']).communicate()

    for tt in templates_information_list:
        template_name = tt['TemplateName']
        subject_part = tt['SubjectPart']
        text_part = tt['TextPart']

        if 'HtmlPart' in tt:
            html_part = tt['HtmlPart']
        else:
            with open(f'{deploy_folder}/templates/{template_name}.html', 'r') as ff:
                html_part = ff.read()

        template = {
            "Template": {
                'TemplateName': template_name,
                'SubjectPart': subject_part,
                'HtmlPart': html_part,
                'TextPart': text_part,
            }
        }

        template_json = f'{deploy_folder}/templates/tmp/{template_name}.json'

        with open(template_json, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False)

        if tt['TemplateName'] in current_templates_name_list:
            cmd = ['ses', 'update-template']
        else:
            cmd = ['ses', 'create-template']
        cmd += ['--cli-input-json', f'file://{template_json}']

        aws_cli_us_east_1.run(cmd)

    ###############################################################################
    print_message(f'packaging lambda: {function_name}')

    print_message('cleanup generated files')
    subprocess.Popen(['git', 'clean', '-d', '-f', '-x'], cwd=deploy_folder).communicate()

    requirements_path = f'{deploy_folder}/requirements.txt'
    if os.path.exists(requirements_path):
        print_message('install dependencies')

        cmd = ['pip3', 'install', '-r', requirements_path, '-t', deploy_folder]
        subprocess.Popen(cmd).communicate()

    settings_path = f'{deploy_folder}/settings_local_sample.py'
    if os.path.exists(settings_path):
        print_message('create environment values')

        lines = read_file(settings_path)
        option_list = list()
        option_list.append(['PHASE', phase])
        for key in settings:
            value = settings[key]
            option_list.append([key, value])
        for oo in option_list:
            lines = re_sub_lines(lines, f'^({oo[0]}) .*', f'\\1 = \'{oo[1]}\'')
        write_file(f'{deploy_folder}/settings_local.py', lines)

    print_message('zip files')

    cmd = ['zip', '-r', 'deploy.zip', '.']
    subprocess.Popen(cmd, cwd=deploy_folder).communicate()

    print_message('create lambda function')

    role_arn = aws_cli.get_role_arn('aws-lambda-default-role')

    git_hash_johanna = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                         stdout=subprocess.PIPE,
                                         cwd=f'template/{git_folder_name}').communicate()[0]

    tags = list()
    # noinspection PyUnresolvedReferences
    tags.append(f"git_hash_johanna={git_hash_johanna.decode('utf-8').strip()}")
    # noinspection PyUnresolvedReferences
    tags.append(f"git_hash_{git_folder_name}={git_hash_template.decode('utf-8').strip()}")

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
        print_session(f'update lambda: {function_name}')

        cmd = ['lambda', 'update-function-code',
               '--function-name', function_name,
               '--zip-file', 'fileb://deploy.zip']
        result = aws_cli.run(cmd, cwd=deploy_folder)

        function_arn = result['FunctionArn']

        cmd = ['lambda', 'update-function-configuration',
               '--function-name', function_name,
               '--description', description,
               '--role', role_arn,
               '--handler', 'lambda.handler',
               '--runtime', 'python3.7',
               '--timeout', '120']
        aws_cli.run(cmd, cwd=deploy_folder)

        print_message('update lambda tags')

        cmd = ['lambda', 'tag-resource',
               '--resource', function_arn,
               '--tags', ','.join(tags)]
        aws_cli.run(cmd, cwd=deploy_folder)

        print_message(f'update sqs event source for {function_name}')

        cmd = ['lambda', 'list-event-source-mappings',
               '--function-name', function_name]
        mappings = aws_cli.run(cmd)['EventSourceMappings']

        for mapping in mappings:
            cmd = ['lambda', 'delete-event-source-mapping',
                   '--uuid', mapping['UUID']]
            aws_cli.run(cmd)

        print_message('wait 120 seconds until deletion is complete')
        time.sleep(120)

        cmd = ['lambda', 'create-event-source-mapping',
               '--event-source-arn', queue_arn,
               '--function-name', function_name]
        aws_cli.run(cmd)
        return

    ################################################################################
    print_session(f'create lambda: {function_name}')

    cmd = ['lambda', 'create-function',
           '--function-name', function_name,
           '--description', description,
           '--zip-file', 'fileb://deploy.zip',
           '--role', role_arn,
           '--handler', 'lambda.handler',
           '--runtime', 'python3.7',
           '--tags', ','.join(tags),
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

    print_message(f'create sqs event source for {function_name}')

    cmd = ['lambda', 'create-event-source-mapping',
           '--event-source-arn', queue_arn,
           '--function-name', function_name]
    aws_cli.run(cmd)
