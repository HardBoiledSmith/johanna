#!/usr/bin/env python3
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_message


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-i', '--origin_bucket_account_id', type=str, required=True, help='origin bucket account id')
    parser.add_argument('-o', '--origin_bucket_name', type=str, required=True, help='origin bucket name')
    parser.add_argument('-r', '--replication_bucket_name', type=str, required=True, help='replication bucket name')
    parser.add_argument('-a', '--replication_aws_access_key', type=str, required=True,
                        help='Replication bucket AWS ACCESS KEY ID')
    parser.add_argument('-s', '--replication_aws_secret_key', type=str, required=True,
                        help='Replication bucket AWS SECRET ACCESS KEY')
    parser.add_argument('-p', '--srr_policy_name', type=str, required=True,
                        help='policy name applied to store replication')
    parser.add_argument('-n', '--srr_role_name', type=str, required=True, help='role name applied to store replication')

    args = parser.parse_args()

    _confirm_phase()

    return args


def run_terminate_s3_origin_srr(args):
    aws_cli = AWSCli()

    ################################################################################
    print_message('origin buket delete policy')

    origin_bucket_account_id = args.origin_bucket_account_id
    origin_bucket_name = args.origin_bucket_name
    replication_bucket_name = args.replication_bucket_name
    srr_policy_name = args.srr_policy_name
    srr_role_name = args.srr_role_name

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', srr_role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::%s:policy/%s' % (origin_bucket_account_id, srr_policy_name)]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-policy']
    cmd += ['--policy-arn', 'arn:aws:iam::%s:policy/%s' % (origin_bucket_account_id, srr_policy_name)]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', srr_role_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['s3api', 'delete-bucket-replication']
    cmd += ['--bucket', origin_bucket_name]
    aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'put-bucket-versioning']
    cmd += ['--bucket', origin_bucket_name]
    cmd += ['--versioning-configuration', 'Status=Suspended']
    aws_cli.run(cmd, ignore_error=False)

    aws_cli = AWSCli(aws_access_key=args.replication_aws_access_key,
                     aws_secret_access_key=args.replication_aws_secret_key)

    cmd = ['s3api', 'delete-bucket-policy']
    cmd += ['--bucket', replication_bucket_name]
    aws_cli.run(cmd, ignore_error=False)


if __name__ == "__main__":
    args = parse_args()

    run_terminate_s3_origin_srr(args)
