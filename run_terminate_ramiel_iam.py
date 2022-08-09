#!/usr/bin/env python3

from run_common import AWSCli

aws_cli = AWSCli()

user_name = 'ramiel-cloudwatch-user'

cc = ['iam', 'detach-user-policy']
cc += ['--user-name', user_name]
cc += ['--policy-arn', 'arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy']
aws_cli.run(cc, ignore_error=True)

cc = ['iam', 'list-access-keys']
cc += ['--user-name', user_name]
rr = aws_cli.run(cc, ignore_error=True)
if rr:
    ll = [ee['AccessKeyId'] for ee in rr['AccessKeyMetadata']]
    for kk in ll:
        cc = ['iam', 'delete-access-key']
        cc += ['--user-name', user_name]
        cc += ['--access-key-id', kk]
        aws_cli.run(cc, ignore_error=True)

cc = ['iam', 'delete-user']
cc += ['--user-name', user_name]
aws_cli.run(cc)
