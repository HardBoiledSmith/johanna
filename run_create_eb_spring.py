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


def run_create_eb_spring(name, settings):
    aws_cli = AWSCli()

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_default_region = env['aws']['AWS_DEFAULT_REGION']
    cname = settings['CNAME']
    db_conn_str_suffix = settings.get('DB_CONNECTION_STR_SUFFIX', '')
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    instance_type = settings.get('INSTANCE_TYPE', 't2.medium')
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    phase = env['common']['PHASE']
    service_name = env['common'].get('SERVICE_NAME', '')
    subnet_type = settings['SUBNET_TYPE']
    name_prefix = '%s_' % service_name if service_name else ''

    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    war_filename = '%s-%s.war' % (name, str_timestamp)

    eb_environment_name = '%s-%s' % (name, str_timestamp)
    eb_environment_name_old = None

    template_folder = 'template/%s' % name
    target_folder = 'template/%s/target' % name
    ebextensions_folder = 'template/%s/_provisioning/.ebextensions' % name
    configuration_folder = 'template/%s/_provisioning/configuration' % name
    properties_file = 'template/%s/%s' % (name, settings['PROPERTIES_FILE'])

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
    ec2_subnet_id_1 = None
    ec2_subnet_id_2 = None
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
            if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
                ec2_subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
                ec2_subnet_id_2 = r['SubnetId']
        elif 'private' == subnet_type:
            if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
                elb_subnet_id_1 = ec2_subnet_id_1 = r['SubnetId']
            if r['CidrBlock'] == cidr_subnet['eb']['private_2']:
                elb_subnet_id_2 = ec2_subnet_id_2 = r['SubnetId']
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
    db_address = aws_cli.get_rds_address()

    ################################################################################
    print_message('get cache address')
    cache_address = aws_cli.get_elasticache_address()

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['mkdir', '-p', 'template']).communicate()

    subprocess.Popen(['rm', '-rf', '%s/' % name], cwd='template').communicate()

    branch = aws_cli.env.get('GIT_BRANCH_APP', phase)
    git_command = ['git', 'clone', '--depth=1']
    if branch != 'dv':
        git_command += ['-b', branch]
    git_command += [git_url]
    subprocess.Popen(git_command, cwd='template').communicate()
    if not os.path.exists('%s' % template_folder):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd=template_folder).communicate()[0]

    subprocess.Popen(['rm', '-rf', '.git'], cwd=template_folder).communicate()
    subprocess.Popen(['rm', '-rf', '.gitignore'], cwd=template_folder).communicate()

    ################################################################################
    print_message('configuration %s' % name)

    with open('%s/phase' % configuration_folder, 'w') as f:
        f.write(phase)
        f.close()

    lines = read_file('%s/etc/logstash/conf.d/logstash_sample.conf' % configuration_folder)
    write_file('%s/etc/logstash/conf.d/logstash.conf' % configuration_folder, lines)

    lines = read_file('%s/%s.config.sample' % (ebextensions_folder, name))
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    write_file('%s/%s.config' % (ebextensions_folder, name), lines)

    sample_file = properties_file.replace('.properties', '-sample.properties')
    lines = read_file(sample_file)
    option_list = list()
    option_list.append(['jdbc.url', 'jdbc:mysql://%s%s' % (db_address, db_conn_str_suffix)])
    option_list.append(['jdbc.username', env['rds']['USER_NAME']])
    option_list.append(['jdbc.password', env['rds']['USER_PASSWORD']])
    option_list.append(['redis.host', cache_address])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(%s)=.*' % oo[0], '\\1=%s' % oo[1])
    write_file(properties_file, lines)

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
    print_message('build artifact')

    build_command = ['mvn']
    if phase != 'dv':
        build_command += ['exec:exec']
    build_command += ['package']

    print_message('build %s: %s' % (name, ' '.join(build_command)))

    subprocess.Popen(build_command, cwd=template_folder).communicate()

    ################################################################################
    print_message('create storage location')

    cmd = ['elasticbeanstalk', 'create-storage-location']
    result = aws_cli.run(cmd)

    s3_bucket = result['S3Bucket']
    s3_war_filename = '/'.join(['s3://' + s3_bucket, eb_application_name, war_filename])

    ################################################################################
    print_message('create application version')

    cmd = ['mv', 'ROOT.war', war_filename]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target_folder).communicate()

    cmd = ['s3', 'cp', war_filename, s3_war_filename]
    aws_cli.run(cmd, cwd=target_folder)

    cmd = ['rm', '-rf', war_filename]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target_folder).communicate()

    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', 'S3Bucket="%s",S3Key="%s/%s"' % (s3_bucket, eb_application_name, war_filename)]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_folder)

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
    oo['Value'] = ','.join([elb_subnet_id_1, elb_subnet_id_2])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'Subnets'
    oo['Value'] = ','.join([ec2_subnet_id_1, ec2_subnet_id_2])
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

    option_settings = json.dumps(option_settings)

    tag0 = 'Key=git_hash_johanna,Value=%s' % git_hash_johanna.decode('utf-8').strip()
    tag2 = 'Key=git_hash_%s,Value=%s' % (name, git_hash_app.decode('utf-8').strip())

    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', '64bit Amazon Linux 2018.03 v3.0.1 running Tomcat 8.5 Java 8']
    cmd += ['--tags', tag0, tag2]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_folder)

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

    subprocess.Popen(['rm', '-rf', '%s/' % name], cwd='template').communicate()

    ################################################################################
    print_message('revoke security group ingress')

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters', 'Name=tag-key,Values=Name Name=tag-value,Values=%s' % eb_environment_name]
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
