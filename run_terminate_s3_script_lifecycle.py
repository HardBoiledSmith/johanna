#!/usr/bin/env python3
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_message
from run_common import print_session


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument('-b', '--bucket_name', type=str, required=True, help='bucket name')

    args = parser.parse_args()

    _confirm_phase()

    return args


def run_terminate_s3_script_bucket_lifecycle(name):
    aws_cli = AWSCli()

    bucket_name = args.bucket_name

    ################################################################################
    print_session('terminate %s' % name)

    ################################################################################
    print_message('delete life cycle')

    cmd = ['s3api', 'delete-bucket-lifecycle', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)


if __name__ == "__main__":
    args = _parse_args()

    run_terminate_s3_script_bucket_lifecycle(args)
