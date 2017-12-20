#!/usr/bin/env python3
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
    base_path = '%s/%s' % (name, settings.get('BASE_PATH', ''))
    common_path = '%s/%s' % (name, settings.get('COMMON_PATH', 'common'))

    template_path = 'template/%s' % template_name
    environment_path = '%s/s3/%s' % (template_path, name)
    app_root_path = os.path.normpath('%s/%s' % (environment_path, base_path))
    common_root_path = os.path.normpath('%s/%s' % (environment_path, common_path))

    deploy_bucket_name = settings['BUCKET_NAME']
    bucket_prefix = settings.get('BUCKET_PREFIX', '')
    deploy_bucket_prefix = os.path.normpath('%s/%s' % (deploy_bucket_name, bucket_prefix))

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    ################################################################################
    print_session('create %s' % name)

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd=environment_path).communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url, name]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url, name]
    subprocess.Popen(git_command, cwd=environment_path).communicate()
    if not os.path.exists(app_root_path):
        raise Exception()

    git_clone_folder = '%s/%s' % (environment_path, name)
    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd=git_clone_folder).communicate()[0]
    subprocess.Popen(['rm', '-rf', './.git'], cwd=git_clone_folder).communicate()
    subprocess.Popen(['rm', '-rf', './.gitignore'], cwd=git_clone_folder).communicate()

    ################################################################################
    print_message('bower install')

    if not os.path.exists('%s/bower.json' % app_root_path):
        subprocess.Popen(['cp', '%s/bower.json' % common_root_path, app_root_path]).communicate()

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
    option_list.append(['phase', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(var %s) .*' % oo[0], '\\1 = \'%s\';' % oo[1])
    write_file('%s/app/scripts/settings-local.js' % app_root_path, lines)

    ################################################################################
    print_message('grunt build')

    if not os.path.exists('%s/package.json' % app_root_path):
        subprocess.Popen(['cp', '%s/package.json' % common_root_path, app_root_path]).communicate()

    npm_process = subprocess.Popen(['npm', 'install'], cwd=app_root_path)
    npm_result, error = npm_process.communicate()

    if error:
        print(error)
        raise Exception()

    if npm_process.returncode != 0:
        print(' '.join(['NPM exited with:', str(npm_process.returncode)]))
        raise Exception()

    grunt_process = subprocess.Popen(['grunt'], cwd=app_root_path)
    grunt_result, error = grunt_process.communicate()

    if error:
        print(error)
        raise Exception()

    if grunt_process.returncode != 0:
        print(' '.join(['Grunt exited with:', str(grunt_process.returncode)]))
        raise Exception()

    ################################################################################
    print_message('upload to temp bucket')

    app_dist_path = '%s/dist' % app_root_path
    temp_bucket_name = aws_cli.get_temp_bucket()
    timestamp = int(time.time())
    temp_bucket_prefix = '%s/%s/%s/%s/%s' % (temp_bucket_name, template_name, name, base_path, timestamp)
    temp_bucket_prefix = os.path.normpath(temp_bucket_prefix)
    temp_bucket_uri = 's3://%s' % temp_bucket_prefix

    cmd = ['s3', 'cp', '.', temp_bucket_uri, '--recursive']
    upload_result = aws_cli.run(cmd, cwd=app_dist_path)
    for ll in upload_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('delete old files from deploy bucket')

    delete_excluded_files = list(settings.get('DELETE_EXCLUDED_FILES', ''))
    if len(delete_excluded_files) > 0:
        cmd = ['s3', 'rm', 's3://%s' % deploy_bucket_prefix, '--recursive']
        for ff in delete_excluded_files:
            cmd += ['--exclude', '%s' % ff]
        delete_result = aws_cli.run(cmd)
        for ll in delete_result.split('\n'):
            print(ll)

    ################################################################################
    print_message('sync to deploy bucket')

    cmd = ['s3', 'sync', temp_bucket_uri, 's3://%s' % deploy_bucket_prefix]
    if len(delete_excluded_files) < 1:
        cmd += ['--delete']
    sync_result = aws_cli.run(cmd)
    for ll in sync_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('tag to deploy bucket')

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
    tag_dict['git_hash_template'] = git_hash_template.decode('utf-8')
    tag_dict['git_hash_%s' % name] = git_hash_app.decode('utf-8')
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
        path_list = list(settings['INVALIDATE_PATHS'])
        cmd = ['cloudfront', 'create-invalidation', '--distribution-id', cf_dist_id, '--paths', ' '.join(path_list)]
        invalidate_result = aws_cli.run(cmd)
        print(invalidate_result)


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
