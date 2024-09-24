#!/usr/bin/env python3.12

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file


def run_create_route53_iam_for_resource_record_sets(user_name, allow_role_aws_account_id):
    aws_cli = AWSCli()

    base_name = f'{user_name}-route53-resource-record-sets'
    ################################################################################
    print_message(f'create role: {base_name}')

    lines = read_file('aws_iam/aws-route53-resource-record-sets-role.json')
    lines = re_sub_lines(lines, 'ACCOUNT_ID', allow_role_aws_account_id)
    pp = ' '.join(lines)

    cmd = ['iam', 'create-role']
    cmd += ['--role-name', f'{base_name}-role']
    cmd += ['--assume-role-policy-document', pp]
    aws_cli.run(cmd)

    iam_owner_aws_account_id = aws_cli.get_caller_account_id()
    lines = read_file('aws_iam/aws-route53-resource-record-sets-policy.json')
    lines = re_sub_lines(lines, 'ACCOUNT_ID', iam_owner_aws_account_id)
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


if __name__ == "__main__":
    from run_common import parse_args

    _, args = parse_args()

    ################################################################################
    #
    # start
    #
    ################################################################################
    print_session('create iam role for use route53 upsert')

    ################################################################################

    if len(args) != 3:
        print('usage:', args[0],
              '<Username to create role & policy> '
              '<aws account id to allow>')
        raise Exception()

    phase = env['common']['PHASE']
    if phase != 'op':
        raise Exception('It is a script dedicated to the op environment.')

    user_name = args[1]
    allow_role_aws_account_id = args[2]

    run_create_route53_iam_for_resource_record_sets(user_name, allow_role_aws_account_id)
