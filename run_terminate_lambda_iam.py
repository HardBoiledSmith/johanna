from run_common import print_message
from run_common import AWSCli


def terminate_iam_for_lambda(function_name):
    aws_cli = AWSCli()

    replaced_function_name = function_name.replace('_', '-')

    print_message('delete iam role policy')

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', f'lambda-{replaced_function_name}-role']
    cmd += ['--policy-name', f'lambda-{replaced_function_name}-policy']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete iam role')

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', f'lambda-{replaced_function_name}-role']
    aws_cli.run(cmd, ignore_error=True)
