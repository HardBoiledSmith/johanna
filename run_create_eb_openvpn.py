#!/usr/bin/env python3
import json
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file


def run_create_eb_openvpn(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    cname = settings['CNAME']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    host_maya = settings['HOST_MAYA']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    openvpn_ca_crt = settings['CA_CRT']
    openvpn_dh2048_pem = settings['DH2048_PEM']
    openvpn_server_crt = settings['SERVER_CRT']
    openvpn_server_key = settings['SERVER_KEY']
    openvpn_subnet_ip = settings['SUBNET_IP']
    phase = env['common']['PHASE']
    template_name = env['template']['NAME']

    cidr_vpc = aws_cli.cidr_vpc
    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    eb_environment_name = '%s-%s' % (name, str_timestamp)
    eb_environment_name_old = None

    template_path = 'template/%s' % template_name
    environment_path = '%s/elasticbeanstalk/%s' % (template_path, name)
    opt_config_path = '%s/configuration/opt' % environment_path
    etc_config_path = '%s/configuration/etc' % environment_path

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    ################################################################################
    #
    # start
    #
    ################################################################################
    print_session('create %s' % name)

    ################################################################################
    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    if not rds_vpc_id or not eb_vpc_id:
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
    print_message('configuration openvpn')

    path = '%s/configuration/etc/openvpn' % environment_path

    with open('%s/ca.crt' % path, 'w') as f:
        f.write(openvpn_ca_crt)
        f.close()

    with open('%s/dh2048.pem' % path, 'w') as f:
        f.write(openvpn_dh2048_pem)
        f.close()

    with open('%s/server.crt' % path, 'w') as f:
        f.write(openvpn_server_crt)
        f.close()

    with open('%s/server.key' % path, 'w') as f:
        f.write(openvpn_server_key)
        f.close()

    ################################################################################
    print_message('configuration %s' % name)

    with open('%s/configuration/phase' % environment_path, 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file('%s/.elasticbeanstalk/config_sample.yml' % environment_path)
    lines = re_sub_lines(lines, '^(  application_name).*', '\\1: %s' % eb_application_name)
    lines = re_sub_lines(lines, '^(  default_ec2_keyname).*', '\\1: %s' % key_pair_name)
    write_file('%s/.elasticbeanstalk/config.yml' % environment_path, lines)

    lines = read_file('%s/.ebextensions/%s.config.sample' % (environment_path, name))
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    write_file('%s/.ebextensions/%s.config' % (environment_path, name), lines)

    lines = read_file('%s/collectd_sample.conf' % etc_config_path)
    lines = re_sub_lines(lines, 'HOST_MAYA', host_maya)
    write_file('%s/collectd.conf' % etc_config_path, lines)

    lines = read_file('%s/ntpdate_sample.sh' % opt_config_path)
    lines = re_sub_lines(lines, '^(SERVER).*', '\\1=\'%s\'' % host_maya)
    write_file('%s/ntpdate.sh' % opt_config_path, lines)

    lines = read_file('%s/openvpn/server_sample.conf' % etc_config_path)
    lines = re_sub_lines(lines, 'OPENVPN_SUBNET_IP', openvpn_subnet_ip)
    write_file('%s/openvpn/server.conf' % etc_config_path, lines)

    lines = read_file('%s/sysconfig/iptables_sample' % etc_config_path)
    lines = re_sub_lines(lines, 'AWS_VPC_EB', cidr_vpc['eb'])
    lines = re_sub_lines(lines, 'OPENVPN_SUBNET_IP', openvpn_subnet_ip)
    write_file('%s/sysconfig/iptables' % etc_config_path, lines)

    ################################################################################
    print_message('check previous version')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['Environments']:
        if 'CNAME' not in r:
            continue

        if r['CNAME'] == '%s.%s.elasticbeanstalk.com' % (cname, aws_default_region):
            if r['Status'] == 'Terminated':
                continue
            elif r['Status'] != 'Ready':
                print('previous version is not ready.')
                raise Exception()

            eb_environment_name_old = r['EnvironmentName']
            cname += '-%s' % str_timestamp
            break

    ################################################################################
    print_message('create %s' % name)

    tags = list()
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_johanna=%s' % git_hash_johanna.decode('utf-8').strip())
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_%s=%s' % (template_name, git_hash_template.decode('utf-8').strip()))

    cmd = ['create', eb_environment_name]
    cmd += ['--cname', cname]
    cmd += ['--instance_type', 't2.nano']
    cmd += ['--region', aws_default_region]
    cmd += ['--single']
    cmd += ['--tags', ','.join(tags)]
    cmd += ['--vpc.ec2subnets', ','.join([subnet_id_1, subnet_id_2])]
    cmd += ['--vpc.elbpublic']
    cmd += ['--vpc.elbsubnets', ','.join([subnet_id_1, subnet_id_2])]
    cmd += ['--vpc.id', eb_vpc_id]
    cmd += ['--vpc.publicip']
    cmd += ['--vpc.securitygroups', security_group_id]
    cmd += ['--quiet']
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
    print_message('disable source/destination checking')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--environment-name', eb_environment_name]
    result = aws_cli.run(cmd)

    ip_address = result['Environments'][0]['EndpointURL']

    cmd = ['ec2', 'describe-instances']
    cmd += ['--filter=Name=ip-address,Values=%s' % ip_address]
    result = aws_cli.run(cmd)

    instance_id = result['Reservations'][0]['Instances'][0]['InstanceId']

    cmd = ['ec2', 'modify-instance-attribute']
    cmd += ['--instance-id', instance_id]
    cmd += ['--no-source-dest-check']
    aws_cli.run(cmd)

    ################################################################################
    print_message('swap CNAME if the previous version exists')

    if eb_environment_name_old:
        cmd = ['elasticbeanstalk', 'swap-environment-cnames']
        cmd += ['--source-environment-name', eb_environment_name_old]
        cmd += ['--destination-environment-name', eb_environment_name]
        aws_cli.run(cmd)
