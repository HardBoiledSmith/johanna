#!/usr/bin/env python3.11

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file

_, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    _, args = parse_args()


# It is a script dedicated to the op environment.
def run_create_cloudfront_iam_for_invaildation(user_name, allow_role_aws_account_id, app_distribution_id,
                                               test_distribution_id):
    aws_cli = AWSCli()

    base_name = f'{user_name}-cloudfront-invalidations'
    ################################################################################
    print_message(f'create role: {base_name}')

    lines = read_file('aws_iam/aws-cloudfront-invalidations-role.json')
    lines = re_sub_lines(lines, 'ACCOUNT_ID', allow_role_aws_account_id)
    pp = ' '.join(lines)

    cmd = ['iam', 'create-role']
    cmd += ['--role-name', f'{base_name}-role']
    cmd += ['--assume-role-policy-document', pp]
    aws_cli.run(cmd)

    iam_owner_aws_account_id = aws_cli.get_caller_account_id()
    lines = read_file('aws_iam/aws-cloudfront-invalidations-policy.json')
    lines = re_sub_lines(lines, 'ACCOUNT_ID', iam_owner_aws_account_id)
    lines = re_sub_lines(lines, 'APP_DISTRIBUTION_ID', app_distribution_id)
    lines = re_sub_lines(lines, 'TEST_DISTRIBUTION_ID', test_distribution_id)
    pp = ' '.join(lines)

    cmd = ['iam', 'create-policy']
    cmd += ['--policy-name', f'{base_name}-policy']
    cmd += ['--policy-document', pp]
    rr = aws_cli.run(cmd)

    policy_arn = rr['Policy']['Arn']
    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', f'{base_name}-role']
    cmd += ['--policy-arn', policy_arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create iam user for use cloudfront invalidations')

################################################################################

if len(args) != 5:
    print('usage:', args[0],
          '<Username to create role & policy> '
          '<aws account id to allow> '
          '<app page cloudfront distribution id to allow> '
          '<test page cloudfront distribution id to allow>')
    raise Exception()

phase = env['common']['PHASE']
if phase != 'op':
    raise Exception('It is a script dedicated to the op environment.')

user_name = args[1]
allow_role_aws_account_id = args[2]
app_distribution_id = args[3]
test_distribution_id = args[4]

run_create_cloudfront_iam_for_invaildation(user_name, allow_role_aws_account_id, app_distribution_id,
                                           test_distribution_id)
