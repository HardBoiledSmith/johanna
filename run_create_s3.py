#!/usr/bin/env python3

from env import env
from run_common import print_session
from run_create_s3_vue import run_create_s3_vue
from run_create_s3_bucket import run_create_s3_bucket

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create s3')

################################################################################

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
        run_create_s3_bucket(s3_env['NAME'], s3_env)
    elif s3_env['TYPE'] == 'vue-app':
        run_create_s3_vue(s3_env['NAME'], s3_env)
    else:
        print('"%s" is not supported' % s3_env['TYPE'])
        raise Exception()

if not check_exists and target_s3_name:
    print('"%s" is not exists in config.json' % target_s3_name)
