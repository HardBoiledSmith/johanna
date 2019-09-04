#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import reset_template_dir
from run_common import print_message
from run_common import print_session
from run_create_codebuild_cron import run_create_codebuild_cron
from run_create_codebuild_default import run_create_codebuild_default
from run_create_codebuild_github import run_create_codebuild_github

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def create_iam_for_codebuild(codebuild_type):
    sleep_required = False

    role_name = 'aws-codebuild-%s-role' % codebuild_type
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role: %s' % role_name)

        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', 'file://aws_iam/%s.json' % role_name]
        aws_cli.run(cmd)
        sleep_required = True

    policy_name = 'aws-codebuild-%s-policy' % codebuild_type
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message('create iam role policy: %s' % policy_name)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', 'file://aws_iam/%s.json' % policy_name]
        aws_cli.run(cmd)
        sleep_required = True

    return sleep_required


def create_iam_for_events():
    sleep_required = False

    role_name = 'aws-events-rule-codebuild-role'
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role: %s' % role_name)

        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', 'file://aws_iam/%s.json' % role_name]
        aws_cli.run(cmd)
        sleep_required = True

    policy_name = 'aws-events-rule-codebuild-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message('create iam role policy: %s' % policy_name)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', 'file://aws_iam/%s.json' % policy_name]
        aws_cli.run(cmd)
        sleep_required = True

    return sleep_required


################################################################################
#
# start
#
################################################################################
print_session('create codebuild')

################################################################################
reset_template_dir()

default_role_created = create_iam_for_codebuild('default')
cron_role_created = create_iam_for_codebuild('cron')
secure_parameter_role_created = create_iam_for_codebuild('secure-parameter')
events_role_created = create_iam_for_events()
if default_role_created or (cron_role_created or events_role_created or secure_parameter_role_created):
    print_message('wait two minutes to let iam role and policy propagated to all regions...')
    time.sleep(120)

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
        print('"%s" is not supported' % codebuild_env['TYPE'])
        raise Exception()
