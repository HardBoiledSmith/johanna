#!/usr/bin/env python3

from env import env
from run_common import print_session
from run_create_eb_django import run_create_eb_django
from run_create_eb_windows import run_create_eb_windows

options, args = {}, []

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create eb')

################################################################################

eb = env['elasticbeanstalk']
target_eb_name = None
region = options.get('region')
check_exists = False

if len(args) > 1:
    target_eb_name = args[1]

for eb_env in eb['ENVIRONMENTS']:
    if target_eb_name and eb_env['NAME'] != target_eb_name:
        continue

    if region and eb_env.get('AWS_DEFAULT_REGION') != region:
        continue

    if target_eb_name:
        check_exists = True

    if eb_env['TYPE'] == 'django':
        run_create_eb_django(eb_env['NAME'], eb_env, options)
    elif eb_env['TYPE'] == 'windows':
        run_create_eb_windows(eb_env['NAME'], eb_env, options)
    else:
        print(f"\"{eb_env['TYPE']}\" is not supported")
        raise Exception()

if not check_exists and target_eb_name and not region:
    print(f'{target_eb_name} is not exists in config.json')

if not check_exists and target_eb_name and region:
    print(f'"{target_eb_name}, {region}" is not exists in config.json')
