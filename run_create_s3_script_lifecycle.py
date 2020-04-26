#!/usr/bin/env python3
import json
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_message


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument('-b', '--bucket_name', type=str, required=True, help='bucket name')
    parser.add_argument('-f', '--expire_days', type=int, required=True, help='File expiration date in the _trash/')

    args = parser.parse_args()

    _confirm_phase()

    return args


def run_create_s3_script_file_lifecycle(args):
    aws_cli = AWSCli()

    bucket_name = args.bucket_name
    expire_days = int(args.expire_days)

    print_message('set life cycle rule')

    cc = {
        "Rules": [
            {
                "Expiration": {
                    "Days": expire_days
                },
                "ID": "script_file_manage_rule",
                "Filter": {
                    "Prefix": "_trash/"
                },
                "Status": "Enabled",
                "NoncurrentVersionExpiration": {
                    "NoncurrentDays": expire_days
                },
                "AbortIncompleteMultipartUpload": {
                    "DaysAfterInitiation": 7
                }
            }
        ]
    }

    cmd = ['s3api', 'put-bucket-lifecycle-configuration', '--bucket', bucket_name]
    cmd += ['--lifecycle-configuration', json.dumps(cc)]
    aws_cli.run(cmd)


if __name__ == "__main__":
    args = _parse_args()

    run_create_s3_script_file_lifecycle(args)
