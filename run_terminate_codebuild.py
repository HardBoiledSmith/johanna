#!/usr/bin/env python3.12
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_codebuild_common import run_terminate_vpc_project
from run_terminate_codebuild_common import terminate_all_iam_role_and_policy
from run_terminate_codebuild_common import terminate_all_notification_rule

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


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
    aws_region = settings['AWS_REGION']

    print_message(f'delete default project: {name}')

    aws_cli = AWSCli(aws_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)

    terminate_all_notification_rule(aws_cli, name, settings)


def run_terminate_github_project(name, settings):
    aws_region = settings['AWS_REGION']

    print_message(f'delete github project: {name}')

    aws_cli = AWSCli(aws_region)

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
    aws_region = settings['AWS_REGION']
    git_branch = settings['BRANCH']

    print_message(f'delete cron project: {name}')

    aws_cli = AWSCli(aws_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    rule_name = f'{name}CronRuleSourceBy{git_branch.title()}'
    terminate_cron_event(aws_cli, rule_name)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)

    terminate_all_notification_rule(aws_cli, name, settings)


################################################################################
#
# start
#
################################################################################
print_session('terminate codebuild')

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
        run_terminate_default_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'cron':
        run_terminate_cron_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'github':
        run_terminate_github_project(settings['NAME'], settings)
    elif settings['TYPE'] == 'vpc':
        run_terminate_vpc_project(settings['NAME'], settings)
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
