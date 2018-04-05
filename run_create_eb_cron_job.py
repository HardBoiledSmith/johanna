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


def run_create_eb_cron_job(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    phase = env['common']['PHASE']
    subnet_type = settings['SUBNET_TYPE']
    template_name = env['template']['NAME']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''
    if hasattr(settings, 'PRIVATE_IP'):
        private_ip = settings['PRIVATE_IP']
    else:
        private_ip = None

    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    zip_filename = '%s-%s.zip' % (name, str_timestamp)

    eb_environment_name = '%s-%s' % (name, str_timestamp)
    eb_environment_name_old = None

    template_path = 'template/%s' % template_name
    environment_path = '%s/elasticbeanstalk/%s' % (template_path, name)
    etc_config_path = '%s/configuration/etc' % environment_path

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

    ################################################################################
    print_session('create %s' % name)

    ################################################################################
    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

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
            print('ERROR!!! Unknown subnet type:', subnet_type)
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
            if r['GroupName'] == '%seb_public' % name_prefix:
                security_group_id = r['GroupId']
                break
        elif 'private' == subnet_type:
            if r['GroupName'] == '%seb_private' % name_prefix:
                security_group_id = r['GroupId']
                break
        else:
            print('ERROR!!! Unknown subnet type:', subnet_type)
            raise Exception()

    ################################################################################
    print_message('configuration %s' % name)

    with open('%s/configuration/phase' % environment_path, 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file('%s/.ebextensions/%s.config.sample' % (environment_path, name))
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    write_file('%s/.ebextensions/%s.config' % (environment_path, name), lines)

    lines = read_file('%s/collectd_sample.conf' % etc_config_path)
    write_file('%s/collectd.conf' % etc_config_path, lines)

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd=environment_path).communicate()
    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd=environment_path).communicate()
    if not os.path.exists('%s/%s' % (environment_path, name)):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd='%s/%s' % (environment_path, name)).communicate()[0]

    subprocess.Popen(['rm', '-rf', './%s/.git' % name], cwd=environment_path).communicate()
    subprocess.Popen(['rm', '-rf', './%s/.gitignore' % name], cwd=environment_path).communicate()

    ################################################################################

    for ss in settings['SETTINGS_LOCAL_PATH']:
        lines = read_file('%s/%s/settings_local_sample.py' % (environment_path, ss))
        lines = re_sub_lines(lines, '^(DEBUG).*', '\\1 = %s' % debug)
        option_list = list()
        option_list.append(['PHASE', phase])
        for key in settings:
            value = settings[key]
            option_list.append([key, value])
        for oo in option_list:
            lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
        write_file('%s/%s/settings_local.py' % (environment_path, ss), lines)

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

    cmd = ['zip', '-r', zip_filename, '.', '.ebextensions']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=environment_path).communicate()

    cmd = ['s3', 'cp', zip_filename, s3_zip_filename]
    aws_cli.run(cmd, cwd=environment_path)

    cmd = ['rm', '-rf', zip_filename]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=environment_path).communicate()

    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', 'S3Bucket="%s",S3Key="%s/%s"' % (s3_bucket, eb_application_name, zip_filename)]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=environment_path)

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
    oo['Value'] = 't2.nano'
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
    if 'private' == subnet_type:
        oo['Value'] = 'false'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBScheme'
    oo['Value'] = '...'
    if 'private' == subnet_type:
        oo['Value'] = 'internal'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBSubnets'
    oo['Value'] = ','.join([subnet_id_1, subnet_id_2])
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
    oo['Value'] = 'LoadBalanced'
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

    option_settings = json.dumps(option_settings)

    tag0 = 'Key=git_hash_johanna,Value=%s' % git_hash_johanna.decode('utf-8').strip()
    tag1 = 'Key=git_hash_%s,Value=%s' % (template_name, git_hash_template.decode('utf-8').strip())
    tag2 = 'Key=git_hash_%s,Value=%s' % (name, git_hash_app.decode('utf-8').strip())

    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', '64bit Amazon Linux 2017.09 v2.6.6 running Python 3.6']
    cmd += ['--tags', tag0, tag1, tag2]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=environment_path)

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

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd=environment_path).communicate()

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
