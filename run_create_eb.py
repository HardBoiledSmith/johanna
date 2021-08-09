#!/usr/bin/env python3

from env import env
from run_common import print_session
from run_create_eb_django import run_create_eb_django
from run_create_eb_windows import run_create_eb_windows

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create eb')

eb = env['elasticbeanstalk']
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in eb.get('ENVIRONMENTS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'django':
        run_create_eb_django(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'windows':
        run_create_eb_windows(settings['NAME'], settings, options)
    else:
        print(f'{settings["TYPE"]} is not supported')
        raise Exception()

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'eb environment: {mm} is not found in config.json')
