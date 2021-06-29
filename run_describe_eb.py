#!/usr/bin/env python3
from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_list_roles(name):
    cmd = ['iam', 'list-roles']
    result = aws_cli.run(cmd)
    count = 0

    for role in result['Roles']:
        if role['RoleName'] == f'aws-elasticbeanstalk-{name}-ec2-role':
            count += 1
        if role['RoleName'] == f'aws-elasticbeanstalk-{name}-service-role':
            count += 1

    if count == 3:
        return True
    else:
        return False


def describe_role_policy():
    cmd = ['iam', 'list-role-policies']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']

    # noinspection PyBroadException
    try:
        aws_cli.run(cmd)
    except Exception:
        return False

    return True


def describe_application():
    cmd = ['elasticbeanstalk', 'describe-applications']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]
    result = aws_cli.run(cmd, ignore_error=True)

    if not result['Applications']:
        return False
    else:
        return True


def describe_environments():
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]

    # noinspection PyBroadException
    try:
        result = aws_cli.run(cmd)
    except Exception:
        return False

    return result['Environments']


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()

for environment in env['elasticbeanstalk']['ENVIRONMENTS']:
    if not describe_list_roles(environment['NAME']):
        results.append(f'IAM {environment["NAME"]} Roles -------------- X')
    else:
        results.append(f'IAM {environment["NAME"]} Roles -------------- O')

if not describe_role_policy():
    results.append('IAM Role Policy -------------- X')
else:
    results.append('IAM Role Policy -------------- O')

if not describe_application():
    results.append('EB Application -------------- X')
else:
    results.append('EB Application -------------- O')

if not describe_environments():
    results.append('EB Environments -------------- X')
else:
    results.append('EB Environments -------------- O')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
