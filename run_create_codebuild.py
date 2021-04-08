#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_session
from run_common import reset_template_dir
from run_create_codebuild_cron import run_create_codebuild_cron
from run_create_codebuild_default import run_create_codebuild_default
from run_create_codebuild_github import run_create_codebuild_github
from run_create_codebuild_vpc import run_create_codebuild_vpc

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()

################################################################################
#
# start
#
################################################################################
print_session('create codebuild')

################################################################################
reset_template_dir()

codebuild_list = env['codebuild']
if len(args) == 2:
    target_codebuild_name = args[1]
    target_codebuild_name_exists = False
    for codebuild_env in codebuild_list:
        if codebuild_env['NAME'] == target_codebuild_name:
            target_codebuild_name_exists = True
            if codebuild_env['TYPE'] == 'default':
                run_create_codebuild_default(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'cron':
                run_create_codebuild_cron(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'github':
                run_create_codebuild_github(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'vpc':
                run_create_codebuild_vpc(codebuild_env['NAME'], codebuild_env)
                break
            print('"%s" is not supported' % codebuild_env['TYPE'])
            raise Exception()
    if not target_codebuild_name_exists:
        print('"%s" is not exists in config.json' % target_codebuild_name)
else:
    for codebuild_env in codebuild_list:
        if codebuild_env['TYPE'] == 'default':
            run_create_codebuild_default(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'cron':
            run_create_codebuild_cron(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'github':
            run_create_codebuild_github(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'vpc':
            run_create_codebuild_vpc(codebuild_env['NAME'], codebuild_env)
            continue
        print('"%s" is not supported' % codebuild_env['TYPE'])
        raise Exception()
