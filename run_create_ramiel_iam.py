#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()

print_session('set ramiel log groups retention days')

ll = [
    '/on-premise/ramiel/PnPDaemon',
    '/on-premise/ramiel/WebDriverAgent',
    '/on-premise/ramiel/ws-scrcpy-error',
    '/on-premise/ramiel/ws-scrcpy-info',
    '/on-premise/ramiel/ws-scrcpy-ios-error',
    '/on-premise/ramiel/ws-scrcpy-ios-info',
]

for log_group_name in ll:
    cc = ['logs', 'describe-log-groups']
    cc += ['--log-group-name-prefix', log_group_name]
    rr = aws_cli.run(cc)

    rr = [ee['logGroupName'] for ee in rr['logGroups']]
    if not rr:
        cc = ['logs', 'create-log-group']
        cc += ['--log-group-name', log_group_name]
        aws_cli.run(cc)

    cc = ['logs', 'put-retention-policy']
    cc += ['--log-group-name', log_group_name]
    cc += ['--retention-in-days', '7']
    aws_cli.run(cc)

print_session('create iAM resources for Ramiel cloudwatch dashboard')

user_name = 'ramiel-cloudwatch-user'

cc = ['iam', 'create-user']
cc += ['--user-name', user_name]
aws_cli.run(cc)

cc = ['iam', 'attach-user-policy']
cc += ['--user-name', user_name]
cc += ['--policy-arn', 'arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy']
aws_cli.run(cc)

cc = ['iam', 'create-access-key']
cc += ['--user-name', user_name]
rr = aws_cli.run(cc)

pp = f'/tmp/{user_name}.txt'
access_key = rr['AccessKey']['AccessKeyId']
secret_key = rr['AccessKey']['SecretAccessKey']
with open(pp, 'w', encoding='utf-8') as ff:
    ff.write(f'AccessKeyId={access_key}\n')
    ff.write(f'SecretAccessKeyId={secret_key}\n')

print_message('Use this generated access key and secret key to deploy Ramiel Monitoring Service')
print(f'''
- AccessKeyId: {access_key}')
- SecretAccessKey: {secret_key}

Also archived here: {pp}
''')
