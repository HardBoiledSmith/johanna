#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

# It is a script dedicated to the op environment.
if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_cloudfront_iam_for_invaildations(name):
    print_session('terminate iam')

    aws_cli = AWSCli()

    iam_owner_aws_account_id = env['cloudfront']['IAM_OWNER_AWS_ACCOUNT_ID']

    ################################################################################
    base_name = f'{name}-cloudfront-invalidations'
    print_message(f'terminate iam: {base_name}-role')

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
print_session('create iam user for use cloudfront invalidations')

################################################################################

check_exists = False

if len(args) != 3:
    print('usage:', args[0], '<delete role or policy user name>')
    raise Exception()

phase = env['common']['PHASE']
if phase != 'op':
    print('# It is a script dedicated to the op environment.')
    raise Exception()

user_name = args[1]

run_terminate_cloudfront_iam_for_invaildations(user_name)
