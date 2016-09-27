#!/usr/bin/env python
from __future__ import print_function

import json
import os
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

aws_asg_max_value = env['nova']['AWS_ASG_MAX_VALUE']
aws_asg_min_value = env['nova']['AWS_ASG_MIN_VALUE']
aws_default_region = env['aws']['AWS_DEFAULT_REGION']
cname = env['nova']['CNAME']
debug = env['common']['DEBUG']
eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
host_nova = env['common']['HOST_NOVA']
key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
phase = env['common']['PHASE']
url_nova = env['common']['URL_NOVA']

cidr_subnet = aws_cli.cidr_subnet

str_timestamp = str(int(time.time()))

eb_environment_name = 'nova-' + str_timestamp
eb_environment_name_old = None

git_rev = ['git', 'rev-parse', 'HEAD']
git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

################################################################################
#
# start
#
################################################################################
print_session('create nova')

################################################################################
print_message('get vpc id')

eb_vpc_id = aws_cli.get_vpc_id()

if not eb_vpc_id:
    print('ERROR!!! No VPC found')
    raise Exception()

################################################################################
print_message('get subnet id')

subnet_id_1 = None
subnet_id_2 = None
cmd = ['ec2', 'describe-subnets']
result = aws_cli.run(cmd)
for r in result['Subnets']:
    if r['VpcId'] != eb_vpc_id:
        continue
    if r['CidrBlock'] == cidr_subnet['eb']['public_1']:
        subnet_id_1 = r['SubnetId']
    if r['CidrBlock'] == cidr_subnet['eb']['public_2']:
        subnet_id_2 = r['SubnetId']

################################################################################
print_message('get security group id')

security_group_id = None
cmd = ['ec2', 'describe-security-groups']
result = aws_cli.run(cmd)
for r in result['SecurityGroups']:
    if r['VpcId'] != eb_vpc_id:
        continue
    if r['GroupName'] == 'eb_public':
        security_group_id = r['GroupId']
        break

################################################################################
print_message('configuration nova')

with open('nova/configuration/phase', 'w') as f:
    f.write(phase)
    f.close()

lines = read_file('nova/.elasticbeanstalk/config.yml.sample')
lines = re_sub_lines(lines, '^(  application_name).*', '\\1: %s' % eb_application_name)
lines = re_sub_lines(lines, '^(  default_ec2_keyname).*', '\\1: %s' % key_pair_name)
write_file('nova/.elasticbeanstalk/config.yml', lines)

lines = read_file('nova/.ebextensions/nova.config.sample')
lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE_NOVA', aws_asg_min_value)
lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE_NOVA', aws_asg_max_value)
write_file('nova/.ebextensions/nova.config', lines)

lines = read_file('nova/configuration/etc/nova/settings_local.py.sample')
lines = re_sub_lines(lines, '^(DEBUG).*', '\\1 = %s' % debug)
option_list = list()
option_list.append(['HOST', host_nova])
option_list.append(['PHASE', phase])
option_list.append(['URL', url_nova])
for oo in option_list:
    lines = re_sub_lines(lines, '^(' + oo[0] + ') .*', '\\1 = \'%s\'' % oo[1])
write_file('nova/configuration/etc/nova/settings_local.py', lines)

################################################################################
print_message('git clone')

subprocess.Popen(['rm', '-rf', './nova'], cwd='nova').communicate()
if phase == 'dv':
    git_command = ['git', 'clone', 'git@github.com:addnull/nova.git']
else:
    git_command = ['git', 'clone', '-b', phase, 'git@github.com:addnull/nova.git']
subprocess.Popen(git_command, cwd='nova').communicate()
if not os.path.exists('nova/nova'):
    raise Exception()

git_hash_nova = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd='nova/nova').communicate()[0]

subprocess.Popen(['rm', '-rf', './nova/.git'], cwd='nova').communicate()
subprocess.Popen(['rm', '-rf', './nova/.gitignore'], cwd='nova').communicate()

################################################################################
print_message('check previous version')

cmd = ['elasticbeanstalk', 'describe-environments']
cmd += ['--application-name', eb_application_name]
result = aws_cli.run(cmd)

for r in result['Environments']:
    if 'CNAME' not in r:
        continue

    if r['CNAME'] == cname + '.ap-northeast-2.elasticbeanstalk.com':
        if r['Status'] == 'Terminated':
            continue
        elif r['Status'] != 'Ready':
            print('previous version is not ready.')
            raise Exception()

        eb_environment_name_old = r['EnvironmentName']
        cname += '-' + str_timestamp
        break

################################################################################
print_message('create nova')

tags = list()
tags.append('git_hash_johanna=%s' % git_hash_johanna.decode('utf-8'))
tags.append('git_hash_nova=%s' % git_hash_nova.decode('utf-8'))

cmd = ['create', eb_environment_name]
cmd += ['--cname', cname]
cmd += ['--instance_type', 't2.nano']
cmd += ['--region', aws_default_region]
cmd += ['--tags', ','.join(tags)]
cmd += ['--vpc.ec2subnets', subnet_id_1 + ',' + subnet_id_2]
cmd += ['--vpc.elbpublic']
cmd += ['--vpc.elbsubnets', subnet_id_1 + ',' + subnet_id_2]
cmd += ['--vpc.id', eb_vpc_id]
cmd += ['--vpc.publicip']
cmd += ['--vpc.securitygroups', security_group_id]
cmd += ['--quiet']
aws_cli.run_eb(cmd, cwd='nova')

elapsed_time = 0
while True:
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--environment-name', eb_environment_name]
    result = aws_cli.run(cmd)

    ee = result['Environments'][0]
    print(json.dumps(ee, sort_keys=True, indent=4))
    if ee.get('Health', '') == 'Green' \
            and ee.get('HealthStatus', '') == 'Ok' \
            and ee.get('Status', '') == 'Ready':
        break

    print('creating... (elapsed time: \'%d\' seconds)' % elapsed_time)
    time.sleep(5)
    elapsed_time += 5

    if elapsed_time > 60 * 30:
        raise Exception()

subprocess.Popen(['rm', '-rf', './nova'], cwd='nova').communicate()

################################################################################
print_message('revoke security group ingress')

cmd = ['ec2', 'describe-security-groups']
cmd += ['--filters', 'Name=tag-key,Values=Name,Name=tag-value,Values=%s' % eb_environment_name]
result = aws_cli.run(cmd)

for ss in result['SecurityGroups']:
    cmd = ['ec2', 'revoke-security-group-ingress']
    cmd += ['--group-id', ss['GroupId']]
    cmd += ['--protocol', 'tcp']
    cmd += ['--port', '22']
    cmd += ['--cidr', '0.0.0.0/0']
    aws_cli.run(cmd, ignore_error=True)

################################################################################
print_message('swap CNAME if the previous version exists')

if eb_environment_name_old:
    cmd = ['elasticbeanstalk', 'swap-environment-cnames']
    cmd += ['--source-environment-name', eb_environment_name_old]
    cmd += ['--destination-environment-name', eb_environment_name]
    aws_cli.run(cmd)
