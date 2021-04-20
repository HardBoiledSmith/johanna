#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_codebuild_common import run_terminate_vpc_project
from run_terminate_codebuild_common import terminate_all_iam_role_and_policy
from run_terminate_codebuild_common import terminate_all_notification_rule

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def terminate_cron_event(aws_cli, rule_name):
    print_message(f'delete events rule: {rule_name}')

    cmd = ['events', 'remove-targets']
    cmd += ['--rule', rule_name]
    cmd += ['--ids', '1']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['events', 'delete-rule']
    cmd += ['--name', rule_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_default_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']

    print_message(f'delete default project: {name}')

    aws_cli = AWSCli(aws_default_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)


def run_terminate_github_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']

    print_message(f'delete github project: {name}')

    aws_cli = AWSCli(aws_default_region)

    cmd = ['codebuild', 'delete-webhook']
    cmd += ['--project-name', name]
    aws_cli.run(cmd, ignore_error=True)

    for cc in settings.get('CRON', list()):
        git_branch = cc['SOURCE_VERSION']
        rule_name = f'{name}CronRuleSourceBy{git_branch.title()}'
        terminate_cron_event(aws_cli, rule_name)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)

    terminate_all_notification_rule(aws_cli, name, settings)


def run_terminate_cron_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']
    git_branch = settings['BRANCH']

    print_message(f'delete cron project: {name}')

    aws_cli = AWSCli(aws_default_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    rule_name = f'{name}CronRuleSourceBy{git_branch.title()}'
    terminate_cron_event(aws_cli, rule_name)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)


################################################################################
#
# start
#
################################################################################
print_session('terminate codebuild')

codebuild_list = env.get('codebuild', list())
if len(args) == 2:
    target_codebuild_name = args[1]
    target_codebuild_name_exists = False
    for codebuild_env in codebuild_list:
        if codebuild_env['NAME'] == target_codebuild_name:
            target_codebuild_name_exists = True
            if codebuild_env['TYPE'] == 'default':
                run_terminate_default_project(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'cron':
                run_terminate_cron_project(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'github':
                run_terminate_github_project(codebuild_env['NAME'], codebuild_env)
                break
            if codebuild_env['TYPE'] == 'vpc':
                run_terminate_vpc_project(codebuild_env['NAME'], codebuild_env)
                break
            print('"%s" is not supported' % codebuild_env['TYPE'])
            raise Exception()
    if not target_codebuild_name_exists:
        print('"%s" is not exists in config.json' % target_codebuild_name)
else:
    for codebuild_env in codebuild_list:
        if codebuild_env['TYPE'] == 'default':
            run_terminate_default_project(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'cron':
            run_terminate_cron_project(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'github':
            run_terminate_github_project(codebuild_env['NAME'], codebuild_env)
            continue
        if codebuild_env['TYPE'] == 'vpc':
            run_terminate_vpc_project(codebuild_env['NAME'], codebuild_env)
            continue
        print('"%s" is not supported' % codebuild_env['TYPE'])
        raise Exception()
