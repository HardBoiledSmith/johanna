#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_message

aws_cli = AWSCli()


def create_iam_for_lambda(git_folder_name, folder_name, function_name):
    sleep_required = False
    replaced_function_name = function_name.replace('_', '-')
    role_name = f'lambda-{replaced_function_name}-role'
    result = aws_cli.get_iam_role(role_name)
    print_message(f'role_name result: {result}')
    if not result:
        print_message('create iam role')

        role_file_path = f'file://template/{git_folder_name}/lambda/{folder_name}/iam/role.json'
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', role_file_path]
        aws_cli.run(cmd)
        sleep_required = True

    policy_name = f'lambda-{replaced_function_name}-policy'
    result = aws_cli.get_iam_role_policy(role_name, policy_name)
    print_message(f'policy_name result: {result}')
    if not result:
        print_message('put iam role policy')

        policy_file_path = f'file://template/{git_folder_name}/lambda/{folder_name}/iam/policy.json'
        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', policy_file_path]
        aws_cli.run(cmd)
        sleep_required = True

    return sleep_required
