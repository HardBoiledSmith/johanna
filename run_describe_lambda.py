#!/usr/bin/env python3
from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_default_lambda(func_info):
    for el in env['lambda']:
        if func_info['FunctionName'] == el['NAME'] and el['TYPE'] == 'cron':
            return True

    return False


def describe_cron_lambda(func_info):
    for el in env['lambda']:
        if func_info['FunctionName'] == el['NAME'] and el['TYPE'] == 'default':
            return True

    return False


results = list()

cmd = ['lambda', 'list-functions']
result = aws_cli.run(cmd)

default_lambda_count = 0
cron_lambda_count = 0

for func in result['Functions']:
    if describe_default_lambda(func):
        default_lambda_count += 1
    if describe_cron_lambda(func):
        cron_lambda_count += 1

if default_lambda_count > 0:
    results.append('Lambda (default) -------------- O')
else:
    results.append('Lambda (default) -------------- X')

if cron_lambda_count > 0:
    results.append('Lambda (cron) -------------- O')
else:
    results.append('Lambda (cron) -------------- X')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
