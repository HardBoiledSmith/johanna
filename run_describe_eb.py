#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()


def describe_key_pairs():
    cmd = ['ec2', 'describe-key-pairs']
    result = aws_cli.run(cmd)

    for r in result['KeyPairs']:
        if r['KeyName'] == env['common']['AWS_KEY_PAIR_NAME']:
            return True
            
    return False


def describe_list_roles():
    cmd = ['iam', 'list-roles']
    result = aws_cli.run(cmd)
    count = 0

    for r in result['Roles']:
        if r['RoleName'] == 'aws-elasticbeanstalk-ec2-role':
            count+=1
        if r['RoleName'] == 'aws-elasticbeanstalk-ec2-worker-role':
            count+=1
        if r['RoleName'] == 'aws-elasticbeanstalk-service-role':
            count+=1

    if count == 3:
        return True
    else:
        return False


def describe_role_policy():
    cmd = ['iam', 'list-role-policies']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-worker-role']
    cmd_2 = ['iam', 'list-role-policies']
    cmd_2 += ['--role-name', 'aws-elasticbeanstalk-service-role']

    try:
       aws_cli.run(cmd)
       aws_cli.run(cmd_2)
    except:
       return False

    return True


def describe_application():
    cmd = ['elasticbeanstalk', 'describe-applications']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]
    result = aws_cli.run(cmd, ignore_error=True)

    if result['Applications'] == []:
       return False
    else:
       return True


if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

results = list()

if describe_key_pairs() == False:
   results.append('EC2 Key Pairs -------------- X')
else:
   results.append('EC2 Key Pairs -------------- O')

if describe_list_roles() == False:
   results.append('IAM Roles -------------- X')
else:
   results.append('IAM Roles -------------- O')

if describe_role_policy() == False:
   results.append('IAM Role Policy -------------- X')
else:
   results.append('IAM Role Policy -------------- O')

if describe_application() == False:
   results.append('EB Application -------------- X')
else:
   results.append('EB Application -------------- O')

print('#' * 80)

for r in results:
   print(r)

print('#' * 80)
