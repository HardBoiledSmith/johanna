#!/usr/bin/env python3
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


def run_create_eb_openvpn(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    accounts = settings['ACCOUNTS']
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    openvpn_ca_crt = settings['CA_CRT']
    openvpn_ca_key = settings['CA_KEY']
    openvpn_dh2048_pem = settings['DH2048_PEM']
    openvpn_server_crt = settings['SERVER_CRT']
    openvpn_server_key = settings['SERVER_KEY']
    openvpn_subnet_ip = settings['OPENVPN_SUBNET_IP']
    phase = env['common']['PHASE']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    cidr_vpc = aws_cli.cidr_vpc
    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    zip_filename = '%s-%s.zip' % (name, str_timestamp)

    eb_environment_name = '%s-%s' % (name, str_timestamp)
    eb_environment_name_old = None

    template_path = 'template/%s' % name
    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

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
        if r['GroupName'] == '%seb_public' % name_prefix:
            security_group_id = r['GroupId']
            break

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd=template_path).communicate()
    if not os.path.exists('%s/%s' % (template_path, name)):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd='%s/%s' % (template_path, name)).communicate()[0]

    subprocess.Popen(['rm', '-rf', './%s/.git' % name], cwd=template_path).communicate()
    subprocess.Popen(['rm', '-rf', './%s/.gitignore' % name], cwd=template_path).communicate()

    ################################################################################
    print_message('configuration openvpn')

    path = '%s/%s/_provisioning/configuration/etc/openvpn' % (template_path, name)

    with open('%s/ca.crt' % path, 'w') as f:
        f.write(openvpn_ca_crt)
        f.close()

    with open('%s/ca.key' % path, 'w') as f:
        f.write(openvpn_ca_key)
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

    with open('%s/%s/_provisioning/configuration/accounts' % (template_path, name), 'w') as f:
        for aa in accounts:
            f.write(aa + '\n')
        f.close()

    with open('%s/%s/_provisioning/configuration/phase' % (template_path, name), 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file('%s/%s/_provisioning/.ebextensions/%s.config.sample' % (template_path, name, name))
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    write_file('%s/%s/_provisioning/.ebextensions/%s.config' % (template_path, name, name), lines)

    lines = read_file('%s/%s/_provisioning/configuration/etc/openvpn/server_sample.conf' % (template_path, name))
    lines = re_sub_lines(lines, 'OPENVPN_SUBNET_IP', openvpn_subnet_ip)
    write_file('%s/%s/_provisioning/configuration/etc/openvpn/server.conf' % (template_path, name), lines)

    lines = read_file('%s/%s/_provisioning/configuration/etc/sysconfig/iptables_sample' % (template_path, name))
    lines = re_sub_lines(lines, 'AWS_VPC_EB', cidr_vpc['eb'])
    lines = re_sub_lines(lines, 'OPENVPN_SUBNET_IP', openvpn_subnet_ip)
    write_file('%s/%s/_provisioning/configuration/etc/sysconfig/iptables' % (template_path, name), lines)

    lines = read_file(('%s/%s/_provisioning/configuration/etc/%s/settings_local_sample.py'
                       % (template_path, name, name)))
    lines = re_sub_lines(lines, '^(DEBUG).*', '\\1 = %s' % debug)
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
    write_file(('%s/%s/_provisioning/configuration/etc/%s/settings_local.py' % (template_path, name, name)), lines)

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
    print_message('create storage location')

    cmd = ['elasticbeanstalk', 'create-storage-location']
    result = aws_cli.run(cmd)

    s3_bucket = result['S3Bucket']
    s3_zip_filename = '/'.join(['s3://' + s3_bucket, eb_application_name, zip_filename])

    ################################################################################
    print_message('create application version')

    file_list = list()
    file_list.append('.ebextensions')
    file_list.append('configuration')
    file_list.append('provisioning.py')
    file_list.append('requirements.txt')

    for ff in file_list:
        cmd = ['mv', '%s/_provisioning/%s' % (name, ff), '.']
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['rm', '-rf', '%s/_provisioning' % name]
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-r', zip_filename, '.', '.ebextensions']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['s3', 'cp', zip_filename, s3_zip_filename]
    aws_cli.run(cmd, cwd=template_path)

    cmd = ['rm', '-rf', zip_filename]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', 'S3Bucket="%s",S3Key="%s/%s"' % (s3_bucket, eb_application_name, zip_filename)]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message('create environment %s' % name)

    option_settings = list()

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'EC2KeyName'
    oo['Value'] = key_pair_name
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'InstanceType'
    oo['Value'] = 't3.nano'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'IamInstanceProfile'
    oo['Value'] = 'aws-elasticbeanstalk-ec2-role'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'SecurityGroups'
    oo['Value'] = security_group_id
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'AssociatePublicIpAddress'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBScheme'
    oo['Value'] = '...'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBSubnets'
    oo['Value'] = '...'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'Subnets'
    oo['Value'] = ','.join([subnet_id_1, subnet_id_2])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'VPCId'
    oo['Value'] = eb_vpc_id
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:environment'
    oo['OptionName'] = 'EnvironmentType'
    oo['Value'] = 'SingleInstance'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:environment'
    oo['OptionName'] = 'ServiceRole'
    oo['Value'] = 'aws-elasticbeanstalk-service-role'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:healthreporting:system'
    oo['OptionName'] = 'SystemType'
    oo['Value'] = 'enhanced'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:healthreporting:system'
    oo['OptionName'] = 'ConfigDocument'
    cw_instance = dict()
    cw_instance['RootFilesystemUtil'] = 60
    cw_instance['InstanceHealth'] = 60
    cw_instance['CPUIdle'] = 60
    cw = dict()
    cw['Instance'] = cw_instance
    cfg_doc = dict()
    cfg_doc['CloudWatchMetrics'] = cw
    cfg_doc['Version'] = 1
    oo['Value'] = json.dumps(cfg_doc)
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'StreamLogs'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'DeleteOnTerminate'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'RetentionInDays'
    oo['Value'] = '3'
    option_settings.append(oo)

    option_settings = json.dumps(option_settings)

    tag0 = 'Key=git_hash_johanna,Value=%s' % git_hash_johanna.decode('utf-8').strip()
    tag1 = 'Key=git_hash_%s,Value=%s' % (name, git_hash_app.decode('utf-8').strip())

    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', '64bit Amazon Linux 2018.03 v2.9.2 running Python 3.6']
    cmd += ['--tags', tag0, tag1]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    elapsed_time = 0
    while True:
        cmd = ['elasticbeanstalk', 'describe-environments']
        cmd += ['--application-name', eb_application_name]
        cmd += ['--environment-name', eb_environment_name]
        result = aws_cli.run(cmd)

        ee = result['Environments'][0]
        print(json.dumps(ee, sort_keys=True, indent=4))
        if ee.get('Health', '') == 'Green' and ee.get('Status', '') == 'Ready':
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
