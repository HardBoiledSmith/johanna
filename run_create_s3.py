#!/usr/bin/env python3.12

from env import env
from run_common import print_session
from run_create_s3_bucket import run_create_s3_bucket
from run_create_s3_vue import run_create_s3_vue

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create s3')

################################################################################

target_name = None
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('s3', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'bucket':
        run_create_s3_bucket(settings['NAME'], settings)
    elif settings['TYPE'] == 'vue-app':
        run_create_s3_vue(settings['NAME'], settings, options)
    else:
        print(f'{settings["TYPE"]} is not supported')
        raise Exception()

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    mm = ' in '.join(mm)
    print(f's3: {mm} is not found in config.json')
