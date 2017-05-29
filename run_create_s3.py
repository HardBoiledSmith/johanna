#!/usr/bin/env python3
from __future__ import print_function

import json
import os
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import check_template_availability
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


def run_create_s3_webapp(name, settings):
    git_url = settings['GIT_URL']
    phase = env['common']['PHASE']
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    environment_path = '%s/s3/%s' % (template_path, name)
    app_root_path = '%s/%s' % (environment_path, name)

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    ################################################################################
    print_session('create %s' % name)

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd=environment_path).communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd=environment_path).communicate()
    if not os.path.exists(app_root_path):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd=app_root_path).communicate()[0]

    subprocess.Popen(['rm', '-rf', './.git'], cwd=app_root_path).communicate()
    subprocess.Popen(['rm', '-rf', './.gitignore'], cwd=app_root_path).communicate()

    ################################################################################
    print_message('bower install')

    bower_process = subprocess.Popen(['bower', 'install'], cwd=app_root_path)
    bower_result, error = bower_process.communicate()

    if error:
        print(error)
        raise Exception()

    if bower_process.returncode != 0:
        print(' '.join(['Bower returns:', str(bower_process.returncode)]))
        raise Exception()

    ################################################################################
    print_message('configure %s' % name)

    lines = read_file('%s/configuration/app/scripts/settings-local-sample.js' % environment_path)
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(var %s) .*' % oo[0], '\\1 = \'%s\';' % oo[1])
    write_file('%s/app/scripts/settings-local.js' % app_root_path, lines)

    ################################################################################
    print_message('grunt build')

    npm_process = subprocess.Popen(['npm', 'install'], cwd=app_root_path)
    npm_result, error = npm_process.communicate()

    if error:
        print(error)
        raise Exception()

    if npm_process.returncode != 0:
        print(' '.join(['NPM returns:', str(npm_process.returncode)]))
        raise Exception()

    subprocess.Popen(['grunt', 'build'], cwd=app_root_path).communicate()

    ################################################################################
    print_message('upload to temp bucket')

    app_dist_path = '%s/dist' % app_root_path
    temp_bucket_name = aws_cli.get_temp_bucket()
    timestamp = int(time.time())
    temp_folder = 's3://%s/%s/%s/%s' % (temp_bucket_name, template_name, name, timestamp)
    cmd = ['s3', 'cp', '.', temp_folder, '--recursive']
    upload_result = aws_cli.run(cmd, cwd=app_dist_path)
    for ll in upload_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('sync to deploy bucket')

    deploy_bucket_name = settings['BUCKET_NAME']

    cmd = ['s3', 'sync', temp_folder, 's3://%s' % deploy_bucket_name, '--delete']
    sync_result = aws_cli.run(cmd)
    for ll in sync_result.split('\n'):
        print(ll)

    tag_format = '{Key=%s, Value=%s}'
    tag_list = list()
    tag_list.append(tag_format % ('phase', phase))
    tag_list.append(tag_format % ('git_hash_johanna', git_hash_johanna.decode('utf-8')))
    tag_list.append(tag_format % ('git_hash_template', git_hash_template.decode('utf-8')))
    tag_list.append(tag_format % ('git_hash_app', git_hash_app.decode('utf-8')))
    tag_list.append(tag_format % ('timestamp', timestamp))

    cmd = ['s3api', 'put-bucket-tagging', '--bucket', deploy_bucket_name, '--tagging',
           'TagSet=[%s]' % ','.join(tag_list)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('cleanup temp bucket')

    cmd = ['s3', 'rm', temp_folder, '--recursive']
    upload_result = aws_cli.run(cmd)
    for ll in upload_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('purge cache from cloudflare')

    cf_api_key = env['common']['CLOUDFLARE_API_KEY']
    cf_auth_email = env['common']['CLOUDFLARE_AUTH_EMAIL']
    cf_zone_id = env['common']['CLOUDFLARE_ZONE_ID']
    cf_endpoint = 'https://api.cloudflare.com/client/v4/zones/%s/purge_cache' % cf_zone_id

    data = dict()
    data['files'] = list(settings['PURGE_FILES'])

    cmd = ['curl', '-X', 'DELETE', cf_endpoint,
           '-H', 'X-Auth-Email: %s' % cf_auth_email,
           '-H', 'X-Auth-Key: %s' % cf_api_key,
           '-H', 'Content-Type: application/json',
           '--data', json.dumps(data)]

    subprocess.Popen(cmd).communicate()


################################################################################
#
# start
#
################################################################################
print_session('create s3')

################################################################################
check_template_availability()

s3 = env['s3']
if len(args) == 2:
    target_s3_name = args[1]
    target_s3_name_exists = False
    for s3_env in s3:
        if s3_env['NAME'] == target_s3_name:
            target_s3_name_exists = True
            if s3_env['TYPE'] == 'angular-app':
                run_create_s3_webapp(s3_env['NAME'], s3_env)
                break
    if not target_s3_name_exists:
        print('"%s" is not exists in config.json' % target_s3_name)
else:
    for s3_env in s3:
        if s3_env['TYPE'] == 'angular-app':
            run_create_s3_webapp(s3_env['NAME'], s3_env)
            continue
        print('"%s" is not supported' % s3_env['TYPE'])
        raise Exception()
