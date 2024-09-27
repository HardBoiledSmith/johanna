#!/usr/bin/env python3.11
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

_, args = dict(), list()

# It is a script dedicated to the op environment.
if __name__ == "__main__":
    from run_common import parse_args

    _, args = parse_args()


def run_terminate_cloudfront_iam_for_invaildation(name):
    print_session('terminate iam')

    aws_cli = AWSCli()

    ################################################################################
    base_name = f'{name}-cloudfront-invalidations'
    print_message(f'terminate iam: {base_name}-role')

    iam_owner_aws_account_id = aws_cli.get_caller_account_id()
    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', f'{base_name}-role']
    cmd += ['--policy-arn', f'arn:aws:iam::{iam_owner_aws_account_id}:policy/{base_name}-policy']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', f'{base_name}-role']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-policy']
    cmd += ['--policy-arn', f'arn:aws:iam::{iam_owner_aws_account_id}:policy/{base_name}-policy']
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate iam user for use cloudfront invalidations')

################################################################################

if len(args) != 2:
    raise Exception('usage:', args[0], '<delete role or policy user name>')

phase = env['common']['PHASE']
if phase != 'op':
    raise Exception('It is a script dedicated to the op environment.')

user_name = args[1]

run_terminate_cloudfront_iam_for_invaildation(user_name)
