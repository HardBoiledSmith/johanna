#!/usr/bin/env python3
from __future__ import print_function

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

################################################################################
#
# start
#
################################################################################
print_session('terminate s3')

################################################################################
print_message('terminate old environment (current timestamp: %d)' % timestamp)
