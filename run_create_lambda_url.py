# !/usr/bin/env python3
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
from run_create_lambda_iam import create_iam_for_lambda


def run_create_lambda_url(function_name, settings, options):
    aws_cli = AWSCli(settings['AWS_REGION'])

    description = settings['DESCRIPTION']
    folder_name = settings.get('FOLDER_NAME', function_name)
    git_url = settings['GIT_URL']
    phase = env['common']['PHASE']
    url_auth_type = settings.get('URL_AUTH_TYPE', 'NONE')
    url_cors = settings.get('URL_CORS', {})

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
        branch = options.get('branch', 'master' if phase == 'dv' else phase)
        print(f'branch: {branch}')
        git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
        subprocess.Popen(git_command, cwd='template').communicate()
        if not os.path.exists(f'template/{git_folder_name}'):
            raise Exception()

    deploy_folder = f'template/{git_folder_name}/lambda/{folder_name}'

    ################################################################################
    print_message(f'create iam: {function_name}')

    role_created = create_iam_for_lambda(git_folder_name, folder_name, function_name)
    if role_created:
        print_message('wait 10 seconds to let iam role and policy propagated to all regions...')
        time.sleep(10)

    ################################################################################
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

    replaced_function_name = function_name.replace('_', '-')
    role_arn = aws_cli.get_role_arn(f'lambda-{replaced_function_name}-role')

    git_hash_johanna = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                         stdout=subprocess.PIPE,
                                         cwd=f'template/{git_folder_name}').communicate()[0]

    tags = list()
    tags.append(f"git_hash_johanna={git_hash_johanna.decode('utf-8').strip()}")
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

        print_message('wait few seconds until function is updated')
        time.sleep(10)

        function_arn = result['FunctionArn']

        cmd = ['lambda', 'update-function-configuration',
               '--function-name', function_name,
               '--description', description,
               '--role', role_arn,
               '--handler', 'lambda.handler',
               '--runtime', 'python3.12',
               '--timeout', '480']
        if settings.get('MEMORY_SIZE'):
            cmd += ['--memory-size', settings['MEMORY_SIZE']]
        aws_cli.run(cmd, cwd=deploy_folder)

        print_message('update lambda tags')

        cmd = ['lambda', 'tag-resource',
               '--resource', function_arn,
               '--tags', ','.join(tags)]
        aws_cli.run(cmd, cwd=deploy_folder)

        # noinspection PyBroadException
        try:
            print_message('checking existing function URL configuration')
            cmd = ['lambda', 'get-function-url-config',
                   '--function-name', function_name]
            aws_cli.run(cmd)

            print_message('updating function URL configuration')
            cmd = ['lambda', 'update-function-url-config',
                   '--function-name', function_name,
                   '--auth-type', url_auth_type]
            if url_cors:
                cmd.extend(['--cors', json.dumps(url_cors)])
            url_result = aws_cli.run(cmd)
        except Exception:
            print_message('creating new function URL configuration')
            cmd = ['lambda', 'create-function-url-config',
                   '--function-name', function_name,
                   '--auth-type', url_auth_type]
            if url_cors:
                cmd.extend(['--cors', json.dumps(url_cors)])
            url_result = aws_cli.run(cmd)

        result['FunctionUrl'] = url_result.get('FunctionUrl')
        return result

    ################################################################################
    print_session(f'create lambda: {function_name}')

    cmd = [
        'lambda', 'create-function',
        '--function-name', function_name,
        '--description', description,
        '--zip-file', 'fileb://deploy.zip',
        '--role', role_arn,
        '--handler', 'lambda.handler',
        '--runtime', 'python3.12',
        '--tags', ','.join(tags),
        '--timeout', '480',
        '--architectures', 'arm64',
    ]
    if settings.get('MEMORY_SIZE'):
        cmd += ['--memory-size', settings['MEMORY_SIZE']]
    result = aws_cli.run(cmd, cwd=deploy_folder)

    print_message('creating function URL configuration')
    cmd = ['lambda', 'create-function-url-config',
           '--function-name', function_name,
           '--auth-type', url_auth_type]
    if url_cors:
        cmd.extend(['--cors', json.dumps(url_cors)])
    url_result = aws_cli.run(cmd)
    result['FunctionUrl'] = url_result.get('FunctionUrl')
    print_message(f'function URL: {result["FunctionUrl"]}')

    print_message('adding public access permission for function URL')
    cmd = ['lambda', 'add-permission',
           '--function-name', function_name,
           '--statement-id', function_name + 'StatementId',
           '--action', 'lambda:InvokeFunctionUrl',
           '--principal', '*',
           '--function-url-auth-type', url_auth_type]
    aws_cli.run(cmd)

    return result
