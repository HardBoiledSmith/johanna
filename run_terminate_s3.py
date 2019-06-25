#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_s3_bucket import run_terminate_s3_bucket

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def run_terminate_s3_webapp(name, settings):
    deploy_bucket_name = settings['BUCKET_NAME']

    ################################################################################
    print_message('terminate %s' % name)

    ################################################################################
    print_message('cleanup deploy bucket')

    cmd = ['s3', 'rm', 's3://%s' % deploy_bucket_name, '--recursive']
    delete_result = aws_cli.run(cmd, ignore_error=True)
    for ll in delete_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('remove tag from deploy bucket')

    cmd = ['s3api', 'delete-bucket-tagging', '--bucket', deploy_bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('invalidate cache from cloudfront')

    cf_dist_id = settings.get('CLOUDFRONT_DIST_ID', '')
    if len(cf_dist_id) > 0:
        cmd = ['cloudfront', 'create-invalidation', '--distribution-id', cf_dist_id, '--paths', '/*']
        invalidate_result = aws_cli.run(cmd, ignore_error=True)
        print(invalidate_result)


################################################################################
#
# start
#
################################################################################
print_session('terminate s3')

s3_list = env.get('s3', list())
target_s3_name = None
check_exists = False

if len(args) > 1:
    target_s3_name = args[1]

for s3_env in s3_list:
    if target_s3_name and s3_env['NAME'] != target_s3_name:
        continue

    if target_s3_name:
        check_exists = True

    if s3_env['TYPE'] == 'bucket':
        run_terminate_s3_bucket(s3_env['NAME'], s3_env)
    elif s3_env['TYPE'] == 'vue-app':
        run_terminate_s3_webapp(s3_env['NAME'], s3_env)
    else:
        print('"%s" is not supported' % s3_env['TYPE'])
        raise Exception()

if not check_exists and target_s3_name:
    print('"%s" is not exists in config.json' % target_s3_name)
