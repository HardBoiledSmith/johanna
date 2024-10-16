#!/usr/bin/env python3.12

from env import env
from run_common import print_session
from run_common import reset_template_dir
from run_create_codebuild_cron import run_create_cron_project
from run_create_codebuild_default import run_create_default_project
from run_create_codebuild_github import run_create_github_project
from run_create_codebuild_vpc import run_create_vpc_project

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create codebuild')

reset_template_dir(options)

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('codebuild', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'default':
        run_create_default_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'cron':
        run_create_cron_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'github':
        run_create_github_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'vpc':
        run_create_vpc_project(settings['NAME'], settings)
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
    print(f'codebuild: {mm} is not found in config.json')
