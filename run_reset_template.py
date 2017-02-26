#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import download_template
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()

template_name = env['template']['NAME']
print_session('reset template: %s' % template_name)

download_template()
