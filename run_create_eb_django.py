#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file


def run_create_eb_django(name, settings):
    aws_cli = AWSCli()

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_default_region = env['aws']['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    instance_type = settings.get('INSTANCE_TYPE', 't3.small')
    phase = env['common']['PHASE']
    rds_required = settings.get('RDS_REQUIRED', True)
    ssl_certificate_id = aws_cli.get_acm_certificate_id('hbsmith.io')
    subnet_type = settings['SUBNET_TYPE']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    zip_filename = '%s-%s.zip' % (name, str_timestamp)

    eb_environment_name = '%s-%s' % (name, str_timestamp)
    eb_environment_name_old = None

    template_path = 'template/%s' % name

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

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

    elb_subnet_id_1 = None
    elb_subnet_id_2 = None
    elb_subnet_id_3 = None
    elb_subnet_id_4 = None
    ec2_subnet_id_1 = None
    ec2_subnet_id_2 = None
    ec2_subnet_id_3 = None
    ec2_subnet_id_4 = None
    cmd = ['ec2', 'describe-subnets']
    result = aws_cli.run(cmd)
    for r in result['Subnets']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if 'public' == subnet_type:
            if r['CidrBlock'] == cidr_subnet['eb']['public_1']:
                elb_subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['public_2']:
                elb_subnet_id_2 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['public_3']:
                elb_subnet_id_3 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['public_4']:
                elb_subnet_id_4 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
                ec2_subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
                ec2_subnet_id_2 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_3']:
                ec2_subnet_id_3 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_4']:
                ec2_subnet_id_4 = r['SubnetId']
        elif 'private' == subnet_type:
            if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
                elb_subnet_id_1 = ec2_subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
                elb_subnet_id_2 = ec2_subnet_id_2 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_3']:
                elb_subnet_id_3 = ec2_subnet_id_3 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_4']:
                elb_subnet_id_4 = ec2_subnet_id_4 = r['SubnetId']
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
            if r['GroupName'] == '%seb_private' % name_prefix:
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
    print_message('get database address')

    db_address = ''
    db_address_read_replica = ''

    if rds_required:
        db_address = aws_cli.get_rds_address()
        db_address_read_replica = aws_cli.get_rds_address(read_replica=True)

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
    print_message('configuration %s' % name)

    with open('%s/%s/_provisioning/configuration/phase' % (template_path, name), 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file('%s/%s/_provisioning/configuration/etc/cron.d/%s' % (template_path, name, name))
    rr = '/opt/python/run/venv/bin/python3 /opt/python/current/app/%s/\\1.py' % name
    lines = re_sub_lines(lines, r'/opt/%s/(.+)\.py' % name, rr)
    write_file('%s/%s/_provisioning/configuration/etc/cron.d/%s' % (template_path, name, name), lines)

    lines = read_file('%s/%s/_provisioning/.ebextensions/%s.config.sample' % (template_path, name, name))
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    lines = re_sub_lines(lines, 'SSL_CERTIFICATE_ID', ssl_certificate_id)
    write_file('%s/%s/_provisioning/.ebextensions/%s.config' % (template_path, name, name), lines)

    if db_address:
        lines = read_file('%s/%s/_provisioning/configuration/etc/%s/my_primary.cnf' % (template_path, name, name))
        lines = re_sub_lines(lines, '^(host).*', '\\1 = %s' % db_address)
        lines = re_sub_lines(lines, '^(user).*', '\\1 = %s' % env['rds']['USER_NAME'])
        lines = re_sub_lines(lines, '^(password).*', '\\1 = %s' % env['rds']['USER_PASSWORD'])
        write_file('%s/%s/_provisioning/configuration/etc/%s/my_primary.cnf' % (template_path, name, name), lines)

    if db_address_read_replica:
        lines = read_file('%s/%s/_provisioning/configuration/etc/%s/my_replica.cnf' % (template_path, name, name))
        lines = re_sub_lines(lines, '^(host).*', '\\1 = %s' % db_address_read_replica)
        lines = re_sub_lines(lines, '^(user).*', '\\1 = %s' % env['rds']['USER_NAME'])
        lines = re_sub_lines(lines, '^(password).*', '\\1 = %s' % env['rds']['USER_PASSWORD'])
        write_file('%s/%s/_provisioning/configuration/etc/%s/my_replica.cnf' % (template_path, name, name), lines)

    lines = read_file('%s/%s/_provisioning/configuration/etc/%s/settings_local_sample.py' % (template_path, name, name))
    lines = re_sub_lines(lines, '^(DEBUG).*', '\\1 = %s' % debug)
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
    write_file('%s/%s/_provisioning/configuration/etc/%s/settings_local.py' % (template_path, name, name), lines)

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
    print_message('update s3 policy of storage location')

    lines = read_file('aws_iam/aws-elasticbeanstalk-storage-policy.json')
    lines = re_sub_lines(lines, 'BUCKET_NAME', s3_bucket)

    account_id = re.match(r'^.+-([0-9]+)$', s3_bucket).group(1)
    lines = re_sub_lines(lines, 'MY_ACCOUNT_ID', account_id)

    elb_account_id = aws_cli.get_elb_account_id(aws_default_region)
    lines = re_sub_lines(lines, 'ELB_ACCOUNT_ID', elb_account_id)
    pp = ' '.join(lines)
    pp = json.loads(pp)

    cmd = ['s3api', 'put-bucket-policy']
    cmd += ['--bucket', s3_bucket]
    cmd += ['--policy', json.dumps(pp)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create environment %s' % name)

    option_settings = list()

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'InstanceType'
    oo['Value'] = instance_type
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
    oo['Value'] = 'false'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBScheme'
    oo['Value'] = 'public'
    if 'private' == subnet_type:
        oo['Value'] = 'internal'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBSubnets'
    oo['Value'] = ','.join([elb_subnet_id_1, elb_subnet_id_2, elb_subnet_id_3, elb_subnet_id_4])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'Subnets'
    oo['Value'] = ','.join([ec2_subnet_id_1, ec2_subnet_id_2, ec2_subnet_id_3, ec2_subnet_id_4])
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
    oo['OptionName'] = 'LoadBalancerType'
    oo['Value'] = 'application'
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
    cw_env = dict()
    cw_env['ApplicationRequestsTotal'] = 60
    cw_env['ApplicationRequests2xx'] = 60
    cw_env['ApplicationRequests3xx'] = 60
    cw_env['ApplicationRequests4xx'] = 60
    cw_env['ApplicationRequests5xx'] = 60
    cw_instance = dict()
    cw_instance['RootFilesystemUtil'] = 60
    cw_instance['InstanceHealth'] = 60
    cw_instance['CPUIdle'] = 60
    cw = dict()
    cw['Environment'] = cw_env
    cw['Instance'] = cw_instance
    cfg_doc = dict()
    cfg_doc['CloudWatchMetrics'] = cw
    cfg_doc['Version'] = 1
    oo['Value'] = json.dumps(cfg_doc)
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:healthreporting:system'
    oo['OptionName'] = 'EnhancedHealthAuthEnabled'
    oo['Value'] = 'true'
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
    cmd += ['--solution-stack-name', '64bit Amazon Linux 2018.03 v2.9.19 running Python 3.6']
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

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd=template_path).communicate()

    ################################################################################
    print_message('swap CNAME if the previous version exists')

    if eb_environment_name_old:
        cmd = ['elasticbeanstalk', 'swap-environment-cnames']
        cmd += ['--source-environment-name', eb_environment_name_old]
        cmd += ['--destination-environment-name', eb_environment_name]
        aws_cli.run(cmd)
