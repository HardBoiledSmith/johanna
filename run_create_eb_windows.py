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


def run_create_eb_windows(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_sqs_visual_test_result = settings['AWS_SQS_VISUAL_TEST_RESULT']
    scale_out_adjustment = settings['SCALE_OUT_ADJUSTMENT']
    scale_out_threshold = settings['SCALE_OUT_THRESHOLD']
    scale_in_adjustment = settings['SCALE_IN_ADJUSTMENT']
    scale_in_threshold = settings['SCALE_IN_THRESHOLD']
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    ssl_certificate_id = aws_cli.get_acm_certificate_id('hbsmith.io')
    cname = settings['CNAME']
    debug = env['common']['DEBUG']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    phase = env['common']['PHASE']
    subnet_type = settings['SUBNET_TYPE']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = f'{service_name}_' if service_name else ''
    url = settings['ARTIFACT_URL']
    dv_branch = settings.get('BRANCH', 'master')
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

    if phase == 'dv':
        print(f'dv branch: {dv_branch}')
        git_command = ['git', 'clone', '--depth=1', '-b', dv_branch, git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]

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
    lines = re_sub_lines(lines, 'AWS_SQS_VISUAL_TEST_RESULT', aws_sqs_visual_test_result)
    lines = re_sub_lines(lines, 'SCALE_OUT_ADJUSTMENT', scale_out_adjustment)
    lines = re_sub_lines(lines, 'SCALE_OUT_THRESHOLD', scale_out_threshold)
    lines = re_sub_lines(lines, 'SCALE_IN_ADJUSTMENT', scale_in_adjustment)
    lines = re_sub_lines(lines, 'SCALE_IN_THRESHOLD', scale_in_threshold)
    write_file(f'{template_path}/{name}/_provisioning/.ebextensions/{name}.config', lines)
    lines = read_file(
        f'{template_path}/{name}/_provisioning/configuration/Users/vagrant/Desktop/{name}_exe/settings_local_sample.py')
    lines = re_sub_lines(lines, '^(DEBUG).*', f'\\1 = {debug}')
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, f'^({oo[0]}) .*', f'\\1 = \'{oo[1]}\'')
    write_file(
        f'{template_path}/{name}/_provisioning/configuration/Users/vagrant/Desktop/{name}_exe/settings_local.py', lines)

    lines = read_file(f'{template_path}/{name}/_provisioning/configuration/'
                      f'Users/vagrant/Desktop/{name}_exe/{name}.exe_sample.config')
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        if oo[0] == 'SENTRY_DSN':
            lines = re_sub_lines(lines, '^.+Dsn value=.+$', f'<Dsn value="{oo[1]}" />')
        else:
            lines = re_sub_lines(lines, f'^.+add key=\"({oo[0]})\" value=.+$', f'<add key="\\1" value="{oo[1]}" />')
    write_file(f'{template_path}/{name}/_provisioning/configuration/'
               f'Users/vagrant/Desktop/{name}_exe/{name}.exe.config', lines)

    ################################################################################
    print_message('download artifact')

    branch = dv_branch.lower() if phase == 'dv' else phase

    file_name = f"{branch}-gendo-{git_hash_app.decode('utf-8').strip()}.zip"
    artifact_url = url + f'/{file_name}'

    cmd = ['s3', 'cp', artifact_url, 'gendo-artifact.zip']
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message('check previous version')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['Environments']:
        if 'CNAME' not in r:
            continue

        if r['CNAME'] == f'{cname}.{aws_default_region}.elasticbeanstalk.com':
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
    cmd_list.append(['mkdir', 'temp-gendo-artifact'])
    cmd_list.append(['unzip', 'gendo-artifact.zip', '-d', 'temp-gendo-artifact/'])
    cmd_list.append(['rm', '-rf', 'gendo-artifact.zip'])
    for cmd in cmd_list:
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-r', 'watchdog-artifact.zip', '.']
    subprocess.Popen(cmd, cwd=f'{template_path}/temp-gendo-artifact/watchdog/site').communicate()
    cmd = ['mv', 'temp-gendo-artifact/watchdog/site/watchdog-artifact.zip', '.']
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-r', 'gendo-artifact.zip', 'gendo/']
    subprocess.Popen(cmd, cwd=f'{template_path}/temp-gendo-artifact').communicate()

    cmd_list = list()
    cmd_list.append(['mv', 'temp-gendo-artifact/gendo-artifact.zip', '.'])
    cmd_list.append(['rm', '-rf', 'temp-gendo-artifact'])
    for cmd in cmd_list:
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['cp', 'manifest/aws-windows-deployment-manifest.json', f'{template_path}']
    subprocess.Popen(cmd).communicate()

    cmd = ['zip', '-r', zip_filename, '.', '.ebextensions']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['s3', 'cp', zip_filename, s3_zip_filename]
    aws_cli.run(cmd, cwd=template_path)
    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', f'S3Bucket="{s3_bucket}",S3Key="{eb_application_name}/{zip_filename}"']
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message(f'create environment {name}')

    option_settings = list()

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'EC2KeyName'
    oo['Value'] = key_pair_name
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'InstanceType'
    oo['Value'] = 't3.medium'
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

    tag0 = f"Key=git_hash_johanna,Value={git_hash_johanna.decode('utf-8').strip()}"
    tag1 = f"Key=git_hash_{name},Value={git_hash_app.decode('utf-8').strip()}"

    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', '64bit Windows Server 2016 v2.6.3 running IIS 10.0']
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
    print_message('revoke security group ingress')

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters', 'Name=tag-key,Values=Name', f'Name=tag-value,Values={eb_environment_name}']
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

        print_message('update desired capacity of eb new and old auto scaling-groups')

        cmd = ['autoscaling', 'update-auto-scaling-group']
        cmd += ['--auto-scaling-group-name', eb_new_autoscaling_group_name]
        cmd += ['--desired-capacity', eb_old_autoscaling_group_desired_capacity]
        aws_cli.run(cmd)

        cmd = ['autoscaling', 'update-auto-scaling-group']
        cmd += ['--auto-scaling-group-name', eb_old_autoscaling_group_name]
        cmd += ['--desired-capacity', aws_asg_min_value]
        aws_cli.run(cmd)

        print_message('describe cloudwatch alrams')

        ll = list()
        cmd = ['cloudwatch', 'describe-alarms']
        rr = aws_cli.run(cmd)

        for alarm in rr['MetricAlarms']:
            if eb_environment_id_old in alarm['AlarmName']:
                ll.append(alarm['AlarmName'])

        if not ll:
            return

        print_message('delete eb old environment cloudwatch alarms')

        for alarm in ll:
            cmd = ['cloudwatch', 'delete-alarms']
            cmd += ['--alarm-names', alarm]
            aws_cli.run(cmd)
