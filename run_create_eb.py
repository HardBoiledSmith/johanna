#!/usr/bin/env python3
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

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def run_create_template():
    git_url = env['template']['GIT_URL']
    name = env['template']['NAME']
    phase = env['common']['PHASE']

    print_session('create ' + name)

    subprocess.Popen(['mkdir', '-p', './template']).communicate()
    subprocess.Popen(['rm', '-rf', './' + name], cwd='template').communicate()
    if phase == 'dv':
        template_git_command = ['git', 'clone', git_url]
    else:
        template_git_command = ['git', 'clone', '-b', phase, git_url]
    subprocess.Popen(template_git_command, cwd='template').communicate()

    if not os.path.exists('template/' + name):
        raise Exception()


def run_create_eb_environment(name, settings):
    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_default_region = env['aws']['AWS_DEFAULT_REGION']
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    phase = env['common']['PHASE']
    subnet_type = settings['SUBNET_TYPE']
    template_name = env['template']['NAME']
    if hasattr(settings, 'PRIVATE_IP'):
        private_ip = settings['PRIVATE_IP']
    else:
        private_ip = None

    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    eb_environment_name = name + '-' + str_timestamp
    eb_environment_name_old = None

    template_path = 'template/%s' % template_name
    environment_path = '%s/elasticbeanstalk/%s' % (template_path, name)

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    ################################################################################
    print_session('create ' + name)

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
        if 'public' == subnet_type:
            if r['CidrBlock'] == cidr_subnet['eb']['public_1']:
                subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['public_2']:
                subnet_id_2 = r['SubnetId']
        elif 'private' == subnet_type:
            if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
                subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
                subnet_id_2 = r['SubnetId']
        else:
            print('ERROR!!! Unknown subnet type: %s' % subnet_type)
            raise Exception()

    ################################################################################
    print_message('get security group id')

    security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    result = aws_cli.run(cmd)
    for r in result['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if 'public' == subnet_type:
            if r['GroupName'] == 'eb_public':
                security_group_id = r['GroupId']
                break
        elif 'private' == subnet_type:
            if r['GroupName'] == 'eb_private':
                security_group_id = r['GroupId']
                break
        else:
            print('ERROR!!! Unknown subnet type: %s' % subnet_type)
            raise Exception()

    ################################################################################
    print_message('configuration ' + name)

    with open('%s/configuration/phase' % environment_path, 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file(environment_path + '/.elasticbeanstalk/config.yml.sample')
    lines = re_sub_lines(lines, '^(  application_name).*', '\\1: %s' % eb_application_name)
    lines = re_sub_lines(lines, '^(  default_ec2_keyname).*', '\\1: %s' % key_pair_name)
    write_file(environment_path + '/.elasticbeanstalk/config.yml', lines)

    lines = read_file(environment_path + '/.ebextensions/' + name + '.config.sample')
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    write_file(environment_path + '/.ebextensions/' + name + '.config', lines)

    lines = read_file(environment_path + '/configuration/etc/' + name + '/settings_local.py.sample')
    lines = re_sub_lines(lines, '^(DEBUG).*', '\\1 = %s' % debug)
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(' + oo[0] + ') .*', '\\1 = \'%s\'' % oo[1])
    write_file(environment_path + '/configuration/etc/' + name + '/settings_local.py', lines)

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', './' + name], cwd=environment_path).communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', git_url]
    else:
        git_command = ['git', 'clone', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd=environment_path).communicate()
    if not os.path.exists(environment_path + '/' + name):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd=environment_path + '/' + name).communicate()[0]

    subprocess.Popen(['rm', '-rf', './' + name + '/.git'], cwd=environment_path).communicate()
    subprocess.Popen(['rm', '-rf', './' + name + '/.gitignore'], cwd=environment_path).communicate()

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
    print_message('create ' + name)

    tags = list()
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_johanna=%s' % git_hash_johanna.decode('utf-8'))
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_%s=%s' % (template_name, git_hash_template.decode('utf-8')))
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_' + name + '=%s' % git_hash_app.decode('utf-8'))

    cmd = ['create', eb_environment_name]
    cmd += ['--cname', cname]
    cmd += ['--instance_type', 't2.nano']
    cmd += ['--region', aws_default_region]
    cmd += ['--tags', ','.join(tags)]
    cmd += ['--vpc.id', eb_vpc_id]
    cmd += ['--vpc.securitygroups', security_group_id]
    cmd += ['--quiet']
    if 'public' == subnet_type:
        cmd += ['--vpc.ec2subnets', subnet_id_1 + ',' + subnet_id_2]
        cmd += ['--vpc.elbsubnets', subnet_id_1 + ',' + subnet_id_2]
        cmd += ['--vpc.elbpublic']
        cmd += ['--vpc.publicip']
    elif 'private' == subnet_type:
        # to attach network interface located at 'ap-northeast-2a' (subnet_id_1),
        # DO NOT include 'ap-northeast-2c' (subnet_id_2)
        cmd += ['--vpc.ec2subnets', subnet_id_1]
        cmd += ['--vpc.elbsubnets', subnet_id_1]
    aws_cli.run_eb(cmd, cwd=environment_path)

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

    subprocess.Popen(['rm', '-rf', './' + name], cwd=environment_path).communicate()

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
    if private_ip is not None:
        print_message('attach network interface')

        elapsed_time = 0
        while True:
            cmd = ['ec2', 'describe-network-interfaces']
            cmd += ['--filters', 'Name=private-ip-address,Values=%s' % private_ip]
            result = aws_cli.run(cmd)

            network_interface_id = result['NetworkInterfaces'][0]['NetworkInterfaceId']

            if 'Attachment' not in result['NetworkInterfaces'][0]:
                cmd = ['ec2', 'describe-instances']
                cmd += ['--filters', 'Name=tag-key,Values=Name,Name=tag-value,Values=%s' % eb_environment_name]
                result = aws_cli.run(cmd)

                instance_id = result['Reservations'][0]['Instances'][0]['InstanceId']

                cmd = ['ec2', 'attach-network-interface']
                cmd += ['--network-interface-id', network_interface_id]
                cmd += ['--instance-id', instance_id]
                cmd += ['--device-index', '1']
                aws_cli.run(cmd)

                break

            attachment_id = result['NetworkInterfaces'][0]['Attachment']['AttachmentId']

            cmd = ['ec2', 'detach-network-interface']
            cmd += ['--attachment-id', attachment_id]
            aws_cli.run(cmd, ignore_error=True)

            print('detaching network interface... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    ################################################################################
    print_message('swap CNAME if the previous version exists')

    if eb_environment_name_old:
        cmd = ['elasticbeanstalk', 'swap-environment-cnames']
        cmd += ['--source-environment-name', eb_environment_name_old]
        cmd += ['--destination-environment-name', eb_environment_name]
        aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create template')

run_create_template()

################################################################################
print_session('create eb')

eb = env['elasticbeanstalk']
if len(args) == 2:
    target_eb_name = args[1]
    for eb_env in eb['ENVIRONMENTS']:
        if eb_env['NAME'] == target_eb_name:
            run_create_eb_environment(eb_env['NAME'], eb_env)
            break
    print('"%s" is not exists in config.json' % target_eb_name)
else:
    for eb_env in eb['ENVIRONMENTS']:
        run_create_eb_environment(eb_env['NAME'], eb_env)
