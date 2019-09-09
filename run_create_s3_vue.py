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


def run_create_s3_vue(name, settings):
    aws_cli = AWSCli()

    deploy_bucket_name = settings['BUCKET_NAME']
    git_url = settings['GIT_URL']
    phase = env['common']['PHASE']

    mm = re.match(r'^.+/(.+)\.git$', git_url)
    if not mm:
        raise Exception()
    git_folder_name = mm.group(1)

    ################################################################################
    print_session('create %s' % name)

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', './%s' % git_folder_name], cwd='template').communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd='template').communicate()
    if not os.path.exists('template/%s' % git_folder_name):
        raise Exception()

    git_hash_app = subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                    stdout=subprocess.PIPE,
                                    cwd='template/%s' % git_folder_name).communicate()[0]
    subprocess.Popen(['rm', '-rf', './.git'], cwd='template/%s' % git_folder_name).communicate()
    subprocess.Popen(['rm', '-rf', './.gitignore'], cwd='template/%s' % git_folder_name).communicate()

    ################################################################################
    print_message('npm install')

    npm_process = subprocess.Popen(['npm', 'install'], cwd='template/%s' % git_folder_name)
    npm_result, error = npm_process.communicate()

    if error:
        print(error)
        raise Exception()

    if npm_process.returncode != 0:
        print(' '.join(['npm returns:', str(npm_process.returncode)]))
        raise Exception()

    ################################################################################
    print_message('configure %s' % name)

    lines = read_file('template/%s/%s/static/settings-local-sample.js' % (git_folder_name, name))
    option_list = list()
    option_list.append(['phase', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(const %s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
    write_file('template/%s/%s/static/settings-local.js' % (git_folder_name, name), lines)

    ################################################################################
    print_message('npm build')

    nm = os.path.abspath('template/%s/node_modules' % git_folder_name)
    subprocess.Popen(['ln', '-s', nm, 'node_modules'], cwd='template/%s/%s' % (git_folder_name, name)).communicate()

    npm_process = subprocess.Popen(['npm', 'run', 'build-%s' % name], cwd='template/%s' % git_folder_name)
    npm_result, error = npm_process.communicate()

    if error:
        print(error)
        raise Exception()

    if npm_process.returncode != 0:
        print(' '.join(['Npm exited with:', str(npm_process.returncode)]))
        raise Exception()

    ################################################################################
    print_message('upload to temp bucket')

    temp_bucket_name = aws_cli.get_temp_bucket()
    timestamp = int(time.time())
    temp_bucket_prefix = '%s/%s/%s/%s' % (temp_bucket_name, git_folder_name, name, timestamp)
    temp_bucket_uri = 's3://%s' % temp_bucket_prefix

    cmd = ['s3', 'cp', '.', temp_bucket_uri, '--recursive']
    upload_result = aws_cli.run(cmd, cwd='template/%s/%s/dist' % (git_folder_name, name))
    for ll in upload_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('create deploy bucket if not exists')

    cmd = ['s3', 'mb', 's3://%s' % deploy_bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete public access block')

    cmd = ['s3api', 'delete-public-access-block']
    cmd += ['--bucket', deploy_bucket_name]
    aws_cli.run(cmd)

    print_message('wait public access block has deleted...')
    time.sleep(10)

    ################################################################################
    print_message('set bucket policy')

    lines = read_file('aws_iam/aws-s3-bucket-policy-for-website.json')
    lines = re_sub_lines(lines, 'BUCKET_NAME', deploy_bucket_name)
    pp = ' '.join(lines)

    cmd = ['s3api', 'put-bucket-policy']
    cmd += ['--bucket', deploy_bucket_name]
    cmd += ['--policy', pp]
    aws_cli.run(cmd)

    ################################################################################
    print_message('set website configuration')

    cmd = ['s3api', 'put-bucket-website']
    cmd += ['--bucket', deploy_bucket_name]
    cmd += ['--website-configuration',
            'file://aws_iam/aws-s3-website-configuration.json']
    aws_cli.run(cmd)

    ################################################################################
    print_message('sync to deploy bucket')

    cmd = ['s3', 'sync', temp_bucket_uri, 's3://%s' % deploy_bucket_name, '--delete']
    sync_result = aws_cli.run(cmd)
    for ll in sync_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('tag to deploy bucket')

    git_hash_johanna = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).communicate()[0]

    tag_dict = dict()

    cmd = ['s3api', 'get-bucket-tagging', '--bucket', deploy_bucket_name]
    tag_result = aws_cli.run(cmd, ignore_error=True)
    if tag_result:
        tag_result = dict(tag_result)
        for tt in tag_result['TagSet']:
            key = tt['Key']
            value = tt['Value']
            tag_dict[key] = value

    tag_dict['phase'] = phase
    tag_dict['git_hash_johanna'] = git_hash_johanna.decode('utf-8')
    tag_dict['git_hash_%s/%s' % (git_folder_name, name)] = git_hash_app.decode('utf-8')
    tag_dict['timestamp_%s' % name] = timestamp

    tag_format = '{Key=%s, Value=%s}'
    tag_list = list()
    for key in tag_dict:
        value = tag_dict[key]
        tag_list.append(tag_format % (key, value))

    cmd = ['s3api', 'put-bucket-tagging', '--bucket', deploy_bucket_name, '--tagging',
           'TagSet=[%s]' % ','.join(tag_list)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('cleanup temp bucket')

    cmd = ['s3', 'rm', temp_bucket_uri, '--recursive']
    upload_result = aws_cli.run(cmd)
    for ll in upload_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('invalidate cache from cloudfront')

    cf_dist_id = settings.get('CLOUDFRONT_DIST_ID', '')
    if len(cf_dist_id) > 0:
        cmd = ['cloudfront', 'create-invalidation', '--distribution-id', cf_dist_id, '--paths', '/*']
        invalidate_result = aws_cli.run(cmd)
        print(invalidate_result)
