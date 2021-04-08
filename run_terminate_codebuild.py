#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def terminate_all_iam_role_and_policy(aws_cli, name, settings):
    aws_region = settings['AWS_DEFAULT_REGION']

    account_id = aws_cli.get_caller_account_id()

    pa_list = list()

    policy_name = f'CodeBuildBasePolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildManagedSecretPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildImageRepositoryPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildVpcPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'codebuild-{name}-cron-policy'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    for pa in pa_list:
        print_message(f'delete iam policy: {pa}')

        cmd = ['iam', 'delete-policy']
        cmd += ['--policy-arn', pa]
        aws_cli.run(cmd, ignore_error=True)

    rn_list = list()

    rn_list.append(f'codebuild-{name}-service-role')
    rn_list.append(f'codebuild-{name}-cron-role')

    for rn in rn_list:
        print_message(f'delete iam role: {rn}')

        cmd = ['iam', 'delete-role']
        cmd += ['--role-name', rn]
        aws_cli.run(cmd, ignore_error=True)


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


def run_terminate_vpc_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']

    print_message(f'delete vpc project: {name}')

    aws_cli = AWSCli(aws_default_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['ssm', 'get-parameters-by-path']
    cmd += ['--path', '/CodeBuild/%s' % name]
    result = aws_cli.run(cmd)

    for rr in result.get('Parameters', list()):
        cmd = ['ssm', 'delete-parameter']
        cmd += ['--name', rr['Name']]
        aws_cli.run(cmd, ignore_error=True)

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
