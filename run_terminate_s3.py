#!/usr/bin/env python3
import os

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def run_terminate_s3_webapp(name, settings):
    deploy_bucket_name = settings['BUCKET_NAME']
    bucket_prefix = settings.get('BUCKET_PREFIX', '')
    deploy_bucket_prefix = os.path.normpath('%s/%s' % (deploy_bucket_name, bucket_prefix))

    ################################################################################
    print_message('terminate %s' % name)

    ################################################################################
    print_message('cleanup deploy bucket')

    cmd = ['s3', 'rm', 's3://%s' % deploy_bucket_prefix, '--recursive']
    delete_excluded_files = list(settings.get('DELETE_EXCLUDED_FILES', ''))
    for ff in delete_excluded_files:
        cmd += ['--exclude', '%s' % ff]
    delete_result = aws_cli.run(cmd)
    for ll in delete_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('remove tag from deploy bucket')

    cmd = ['s3api', 'delete-bucket-tagging', '--bucket', deploy_bucket_name]
    aws_cli.run(cmd)

    ################################################################################
    print_message('invalidate cache from cloudfront')

    cf_dist_id = settings['CLOUDFRONT_DIST_ID']
    path_list = list(settings['INVALIDATE_PATHS'])

    cmd = ['cloudfront', 'create-invalidation', '--distribution-id', cf_dist_id, '--paths', ' '.join(path_list)]
    invalidate_result = aws_cli.run(cmd)
    print(invalidate_result)


################################################################################
#
# start
#
################################################################################
print_session('terminate s3')

s3 = env['s3']
if len(args) == 2:
    target_s3_name = args[1]
    target_s3_name_exists = False
    for s3_env in s3:
        if s3_env['NAME'] == target_s3_name:
            target_s3_name_exists = True
            if s3_env['TYPE'] == 'angular-app':
                run_terminate_s3_webapp(s3_env['NAME'], s3_env)
                break
    if not target_s3_name_exists:
        print('"%s" is not exists in config.json' % target_s3_name)
else:
    for s3_env in s3:
        if s3_env['TYPE'] == 'angular-app':
            run_terminate_s3_webapp(s3_env['NAME'], s3_env)
            continue
        print('"%s" is not supported' % s3_env['TYPE'])
        raise Exception()
