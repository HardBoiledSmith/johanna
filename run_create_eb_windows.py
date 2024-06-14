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
from run_create_eb_iam import create_iam_profile_for_ec2_instances


def run_create_eb_windows(name, settings, options):
    aws_cli = AWSCli(settings['AWS_REGION'])

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_fifo_sqs_visual_test_result = settings['AWS_FIFO_SQS_VISUAL_TEST_RESULT']
    scale_out_adjustment = settings['SCALE_OUT_ADJUSTMENT']
    scale_out_threshold = settings['SCALE_OUT_THRESHOLD']
    scale_in_adjustment = settings['SCALE_IN_ADJUSTMENT']
    scale_in_threshold = settings['SCALE_IN_THRESHOLD']
    aws_region = settings['AWS_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    ssl_certificate_id = aws_cli.get_acm_certificate_id('hbsmith.io')
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    instance_type = settings.get('INSTANCE_TYPE', 'r7i.large')
    phase = env['common']['PHASE']
    subnet_type = settings['SUBNET_TYPE']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = f'{service_name}_' if service_name else ''
    url = settings['ARTIFACT_URL']
    time_base_scale_desired_capacity_weekday1 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKDAY1']
    time_base_scale_desired_capacity_weekday2 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKDAY2']
    time_base_scale_desired_capacity_weekday3 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKDAY3']
    time_base_scale_desired_capacity_weekday4 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKDAY4']
    time_base_scale_desired_capacity_weekend1 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKEND1']
    time_base_scale_desired_capacity_weekend2 = settings['TIME_BASE_SCALE_DESIRED_CAPACITY_WEEKEND2']
    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    zip_filename = f'{name}-{str_timestamp}.zip'

    eb_environment_name = f'{name}-{str_timestamp}'
    eb_environment_name_old = None
    eb_environment_id_old = None

    template_path = f'template/{name}'

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

    ################################################################################
    print_session(f'create {name}')

    ################################################################################
    print_message('get gendo golden img arn')

    cmd = ['ec2', 'describe-images']
    cmd += ['--filters',
            'Name=name,Values=Gendo_*',
            'Name=state,Values=available']
    cmd += ['--query', 'reverse(sort_by(Images, &CreationDate))[:1].ImageId']
    cmd += ['--output', 'text']
    cmd += ['--region', 'ap-northeast-2']
    latest_eb_platform_ami = aws_cli.run(cmd)
    if not latest_eb_platform_ami:
        Exception('not exist gendo ami')
    print_message(f'selected latest eb platform ami : {latest_eb_platform_ami}')

    ################################################################################
    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    if not eb_vpc_id:
        print('ERROR!!! No VPC found')
        raise Exception()

    print_message('get Availability Zones offering required instance type')
    cmd = ['ec2', 'describe-instance-type-offerings']
    cmd += ['--location-type', 'availability-zone']
    cmd += ['--filters', f'Name=instance-type,Values={instance_type}']
    cmd += ['--region', aws_region]
    result = aws_cli.run(cmd)
    azs = [az['Location'] for az in result['InstanceTypeOfferings']]

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
        if r['AvailabilityZone'] not in azs:
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
            if r['GroupName'] == f'{name_prefix}eb_private':
                security_group_id = r['GroupId']
                break
        elif 'private' == subnet_type:
            if r['GroupName'] == f'{name_prefix}eb_private':
                security_group_id = r['GroupId']
                break
        else:
            print('ERROR!!! Unknown subnet type:', subnet_type)
            raise Exception()

    #################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()

    branch = options.get('branch', 'master' if phase == 'dv' else phase)
    print(f'branch: {branch}')
    git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
    subprocess.Popen(git_command, cwd=template_path).communicate()
    print(f'{template_path}/{name}')
    if not os.path.exists(f'{template_path}/{name}'):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd=f'{template_path}/{name}').communicate()[0]

    subprocess.Popen(['rm', '-rf', f'./{name}/.git'], cwd=template_path).communicate()
    subprocess.Popen(['rm', '-rf', f'./{name}/.gitignore'], cwd=template_path).communicate()

    lines = read_file(f'{template_path}/{name}/_provisioning/.ebextensions/{name}.config.sample')
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    lines = re_sub_lines(lines, 'SSL_CERTIFICATE_ID', ssl_certificate_id)
    lines = re_sub_lines(lines, 'AWS_FIFO_SQS_VISUAL_TEST_RESULT', aws_fifo_sqs_visual_test_result)
    lines = re_sub_lines(lines, 'SCALE_OUT_ADJUSTMENT', scale_out_adjustment)
    lines = re_sub_lines(lines, 'SCALE_OUT_THRESHOLD', scale_out_threshold)
    lines = re_sub_lines(lines, 'SCALE_IN_ADJUSTMENT', scale_in_adjustment)
    lines = re_sub_lines(lines, 'SCALE_IN_THRESHOLD', scale_in_threshold)
    write_file(f'{template_path}/{name}/_provisioning/.ebextensions/{name}.config', lines)
    lines = read_file(
        f'{template_path}/{name}/_provisioning/configuration/hbsmith/{name}_exe/settings_local_sample.py')
    lines = re_sub_lines(lines, '^(DEBUG).*', f'\\1 = {debug}')
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, f'^({oo[0]}) .*', f'\\1 = \'{oo[1]}\'')
    write_file(
        f'{template_path}/{name}/_provisioning/configuration/hbsmith/{name}_exe/settings_local.py', lines)

    ################################################################################
    print_message('download artifact')

    branch = branch.lower() if phase == 'dv' else phase

    file_name = f"{branch}-gendo-{git_hash_app.decode('utf-8').strip()}.zip"
    artifact_url = url + f'/{file_name}'

    cmd = ['s3', 'cp', artifact_url, 'gendo-artifact.zip']
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message('create iam')

    instance_profile_name, role_arn = create_iam_profile_for_ec2_instances(template_path, name)
    print_message('wait 10 seconds to let iam role and policy propagated to all regions...')
    time.sleep(10)

    ################################################################################
    print_message('check previous version')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['Environments']:
        if 'CNAME' not in r:
            continue

        if r['CNAME'] == f'{cname}.{aws_region}.elasticbeanstalk.com':
            if r['Status'] == 'Terminated':
                continue
            elif r['Status'] != 'Ready':
                print('previous version is not ready.')
                raise Exception()

            eb_environment_name_old = r['EnvironmentName']
            eb_environment_id_old = r['EnvironmentId']
            cname += f'-{str_timestamp}'
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

    for ff in file_list:
        cmd = ['mv', f'{name}/_provisioning/{ff}', '.']
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd_list = list()
    cmd_list.append(['mkdir', 'temp_gendo'])
    cmd_list.append(['rm', '-rf', f'{name}/_provisioning/pretrained_model'])
    cmd_list.append(['mv', f'{name}/_provisioning', 'temp_gendo'])
    cmd_list.append(['mv', f'{name}/requirements.txt', 'temp_gendo/requirements.txt'])
    cmd_list.append(['rm', '-rf', f'{name}'])
    cmd_list.append(['mv', 'temp_gendo', f'{name}'])
    for cmd in cmd_list:
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd_list = list()
    cmd_list.append(['mkdir', 'gendo-artifact'])
    cmd_list.append(['unzip', 'gendo-artifact.zip', '-d', 'gendo-artifact/'])
    cmd_list.append(['rm', '-f', 'gendo-artifact.zip'])
    for cmd in cmd_list:
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-m', '-r', 'watchdog-bundle.zip', '.']
    subprocess.Popen(cmd, cwd=f'{template_path}/gendo-artifact/watchdog').communicate()
    cmd = ['mv', 'gendo-artifact/watchdog/watchdog-bundle.zip', '.']
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-m', '-r', 'gendo-bundle.zip', '.']
    subprocess.Popen(cmd, cwd=f'{template_path}/gendo-artifact/gendo').communicate()
    cmd = ['mv', 'gendo-artifact/gendo/gendo-bundle.zip', '.']
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['rm', '-rf', 'gendo-artifact']
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['cp', 'manifest/aws-windows-deployment-manifest.json', f'{template_path}']
    subprocess.Popen(cmd).communicate()

    cmd = ['zip', '-m', '-r', zip_filename, '.', '.ebextensions']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['s3', 'cp', zip_filename, s3_zip_filename]
    aws_cli.run(cmd, cwd=template_path)

    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', f'S3Bucket="{s3_bucket}",S3Key="{eb_application_name}/{zip_filename}"']
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message('update s3 policy of storage location')

    cmd = ['s3api', 'get-bucket-policy']
    cmd += ['--bucket', s3_bucket]
    rr = aws_cli.run(cmd)
    rr = rr['Policy']

    account_id = aws_cli.get_caller_account_id()
    ppp = fr'arn:aws:iam::{account_id}:role/aws-elasticbeanstalk-(?:[a-z]+-ec2|ec2)-role'
    role_list = re.findall(ppp, rr)

    role_list = set(role_list)
    role_list.add(role_arn)
    role_list = list(role_list)

    lines = read_file('aws_iam/aws-elasticbeanstalk-storage-policy.json')
    lines = re_sub_lines(lines, 'BUCKET_NAME', s3_bucket)
    lines = re_sub_lines(lines, 'AWS_ACCOUNT_ID', account_id)
    elb_account_id = aws_cli.get_elb_account_id(aws_region)
    lines = re_sub_lines(lines, 'ELB_ACCOUNT_ID', elb_account_id)
    lines = re_sub_lines(lines, 'EC2_ROLE_LIST', json.dumps(role_list))
    pp = ' '.join(lines)
    pp = json.loads(pp)

    cmd = ['s3api', 'put-bucket-policy']
    cmd += ['--bucket', s3_bucket]
    cmd += ['--policy', json.dumps(pp)]
    aws_cli.run(cmd)

    ################################################################################
    print_message(f'create environment {name}')

    option_settings = list()

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'ImageId'
    oo['Value'] = latest_eb_platform_ami
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'InstanceType'
    oo['Value'] = instance_type
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'IamInstanceProfile'
    oo['Value'] = instance_profile_name
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'SecurityGroups'
    oo['Value'] = security_group_id
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'RootVolumeType'
    oo['Value'] = 'gp3'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'RootVolumeSize'
    oo['Value'] = '40'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekday1
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 4 * * 1-5'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay2'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay2'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay2'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekday2
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay2'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 7 * * 1-5'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay3'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay3'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay3'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekday3
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay3'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 9 * * 1-5'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay4'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay4'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay4'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekday4
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay4'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 18 * * 1-5'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd1'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd1'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd1'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekend1
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd1'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 7 * * 0,6'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd2'
    oo['OptionName'] = 'MinSize'
    oo['Value'] = aws_asg_min_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd2'
    oo['OptionName'] = 'MaxSize'
    oo['Value'] = aws_asg_max_value
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd2'
    oo['OptionName'] = 'DesiredCapacity'
    oo['Value'] = time_base_scale_desired_capacity_weekend2
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekEnd2'
    oo['OptionName'] = 'Recurrence'
    oo['Value'] = '0 18 * * 0,6'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:scheduledaction'
    oo['ResourceName'] = 'ScheduledScaleSpecificTimeWeekDay1'
    oo['OptionName'] = 'TimeZone'
    oo['Value'] = 'Asia/Seoul'
    option_settings.append(oo)

    ################################################################################

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
    oo['Value'] = ','.join([ss for ss in [elb_subnet_id_1, elb_subnet_id_2, elb_subnet_id_3, elb_subnet_id_4] if ss])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'Subnets'
    oo['Value'] = ','.join([ss for ss in [ec2_subnet_id_1, ec2_subnet_id_2, ec2_subnet_id_3, ec2_subnet_id_4] if ss])
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

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:application:environment'
    oo['OptionName'] = 'EB_ENVIRONMENT_NAME'
    oo['Value'] = eb_environment_name
    option_settings.append(oo)

    option_settings = json.dumps(option_settings)

    tag0 = f"Key=git_hash_johanna,Value={git_hash_johanna.decode('utf-8').strip()}"
    tag1 = f"Key=git_hash_{name},Value={git_hash_app.decode('utf-8').strip()}"

    solution_stack_name = aws_cli.get_eb_gendo_windows_platform(target_service='elastic_beanstalk')
    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', solution_stack_name]
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
        eb_environment_id = result['Environments'][0]['EnvironmentId']
        print(json.dumps(ee, sort_keys=True, indent=4))
        if ee.get('Health', '') == 'Green' and ee.get('Status', '') == 'Ready':
            break

        print('creating... (elapsed time: \'%d\' seconds)' % elapsed_time)
        time.sleep(5)
        elapsed_time += 5

        if elapsed_time > 60 * 60:
            raise Exception()

    subprocess.Popen(['rm', '-rf', f'./{name}'], cwd=template_path).communicate()

    ################################################################################
    print_message('swap CNAME if the previous version exists')

    if eb_environment_name_old:
        cmd = ['elasticbeanstalk', 'swap-environment-cnames']
        cmd += ['--source-environment-name', eb_environment_name_old]
        cmd += ['--destination-environment-name', eb_environment_name]
        aws_cli.run(cmd)

        print_message('describe elastic beanstalk environment resources')

        cmd = ['elasticbeanstalk', 'describe-environment-resources']
        cmd += ['--environment-name', eb_environment_name_old]
        cmd += ['--environment-id', eb_environment_id_old]
        rr = aws_cli.run(cmd)
        eb_old_autoscaling_group_name = rr['EnvironmentResources']['AutoScalingGroups'][0]['Name']

        cmd = ['elasticbeanstalk', 'describe-environment-resources']
        cmd += ['--environment-name', eb_environment_name]
        cmd += ['--environment-id', eb_environment_id]
        rr = aws_cli.run(cmd)
        eb_new_autoscaling_group_name = rr['EnvironmentResources']['AutoScalingGroups'][0]['Name']

        print_message('describe auto scaling-groups for get eb old desired capacity')

        cmd = ['autoscaling', 'describe-auto-scaling-groups']
        cmd += ['--auto-scaling-group-names', eb_old_autoscaling_group_name]
        rr = aws_cli.run(cmd)

        eb_old_autoscaling_group_desired_capacity = str(rr['AutoScalingGroups'][0]['DesiredCapacity'])

        print_message('update desired capacity of eb new auto scaling-groups')

        cmd = ['autoscaling', 'update-auto-scaling-group']
        cmd += ['--auto-scaling-group-name', eb_new_autoscaling_group_name]
        cmd += ['--desired-capacity', eb_old_autoscaling_group_desired_capacity]
        aws_cli.run(cmd)

        elapsed_time = 0
        while True:
            print(f'20 minutes while waiting for new gendo generation... (elapsed time: {elapsed_time} seconds)')

            if elapsed_time > 60 * 20:
                break

            time.sleep(30)
            elapsed_time += 30

        print_message('update desired capacity of eb old auto scaling-groups')

        cmd = ['autoscaling', 'update-auto-scaling-group']
        cmd += ['--auto-scaling-group-name', eb_old_autoscaling_group_name]
        cmd += ['--desired-capacity', aws_asg_min_value]
        aws_cli.run(cmd)

        print_message('describe cloudwatch alarms')

        ll = list()
        cmd = ['cloudwatch', 'describe-alarms']
        rr = aws_cli.run(cmd)

        for alarm in rr['MetricAlarms']:
            if eb_environment_id_old in alarm['AlarmName']:
                ll.append(alarm['AlarmName'])

        if ll:
            print_message('delete eb old environment cloudwatch alarms')

            for alarm in ll:
                cmd = ['cloudwatch', 'delete-alarms']
                cmd += ['--alarm-names', alarm]
                aws_cli.run(cmd)
