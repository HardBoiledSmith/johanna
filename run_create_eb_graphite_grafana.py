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


def _get_s3_bucket_name(settings):
    aws_cli = AWSCli()

    result = aws_cli.run(['s3', 'ls'])

    bucket_name = None
    # noinspection PyTypeChecker
    for rr in result.split('\n'):
        print(rr)
        # noinspection PyTypeChecker
        bucket_name = rr.split(' ')[2]
        # noinspection PyTypeChecker,PyUnresolvedReferences
        if bucket_name.startswith('elasticbeanstalk-%s-' % settings['AWS_DEFAULT_REGION']):
            break
        bucket_name = None

    if not bucket_name:
        raise Exception('cannot find any elasticbeanstalk bucket in AWS Seoul region.')

    # noinspection PyTypeChecker
    bucket_name = 's3://' + bucket_name
    print(bucket_name)

    return bucket_name


def run_create_eb_graphite_grafana(name, settings):
    aws_cli = AWSCli()

    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_eb_notification_email = settings['AWS_EB_NOTIFICATION_EMAIL']
    cname = settings['CNAME']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    host_maya = settings['HOST_MAYA']
    key_pair_name = env['common']['AWS_KEY_PAIR_NAME']
    phase = env['common']['PHASE']
    private_ip = settings['PRIVATE_IP']
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
    app_config_path = '%s/%s' % (etc_config_path, name)

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]
    git_hash_template = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=template_path).communicate()[0]

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
    cmd = ['ec2', 'describe-subnets']
    result = aws_cli.run(cmd)
    for r in result['Subnets']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
            subnet_id_1 = r['SubnetId']

    ################################################################################
    print_message('get security group id')

    security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    result = aws_cli.run(cmd)
    for r in result['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == 'eb_private':
            security_group_id = r['GroupId']
            break

    ################################################################################

    print_message('get database address')
    db_address = aws_cli.get_rds_address()

    settings['DB_HOST'] = db_address
    settings['DB_PASSWORD'] = env['rds']['USER_PASSWORD']
    settings['DB_USER'] = env['rds']['USER_NAME']

    ################################################################################

    print_message('download influxdb backup if available')

    subprocess.Popen(['rm', '-rf',
                      '%s/configuration/influxd/' % environment_path]).communicate()

    try:
        bucket_name = _get_s3_bucket_name(settings)
        s3_folder = '/'.join([bucket_name, 'influxdb_backup'])
        result = aws_cli.run(['s3', 'ls', s3_folder, '--recursive', '--page-size', '1'])
        rr = result.strip()
        if not rr:
            raise Exception('backup is not found')
        rr = rr.split('\n')
        if len(rr) < 1:
            raise Exception('backup is not found')
        rr = sorted(rr, reverse=True)[0]
        print(rr)
        s3_path = rr.split()[3]
        file_name = s3_path.split('/')[1]
        source_file = '/'.join([bucket_name, s3_path])
        target_folder = '%s/configuration/influxd/' % environment_path
        result = aws_cli.run(['s3', 'cp', source_file, target_folder])
        print(result)
        subprocess.Popen(['unzip', '-P', settings['DB_PASSWORD'], file_name],
                         cwd=target_folder).communicate()
        subprocess.Popen(['rm', file_name], cwd=target_folder).communicate()
    except Exception as e:
        print(e)

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
    lines = re_sub_lines(lines, 'AWS_VPC_EB', cidr_vpc['eb'])
    lines = re_sub_lines(lines, 'AWS_EB_NOTIFICATION_EMAIL', aws_eb_notification_email)
    write_file('%s/.ebextensions/%s.config' % (environment_path, name), lines)

    lines = read_file('%s/collectd_sample.conf' % etc_config_path)
    lines = re_sub_lines(lines, 'HOST_MAYA', host_maya)
    write_file('%s/collectd.conf' % etc_config_path, lines)

    lines = read_file('%s/ntpdate_sample.sh' % opt_config_path)
    lines = re_sub_lines(lines, '^(SERVER).*', '\\1=\'%s\'' % host_maya)
    write_file('%s/ntpdate.sh' % opt_config_path, lines)

    lines = read_file('%s/settings_local_sample.py' % app_config_path)
    option_list = list()
    option_list.append(['PHASE', phase])
    for key in settings:
        value = settings[key]
        option_list.append([key, value])
    for oo in option_list:
        lines = re_sub_lines(lines, '^(%s) .*' % oo[0], '\\1 = \'%s\'' % oo[1])
    write_file('%s/settings_local.py' % app_config_path, lines)

    lines = read_file('%s/configuration/grafana-alert-notifications_sample.json' % environment_path)
    lines = re_sub_lines(lines, 'SLACK_WEBHOOK_URL', settings['SLACK_WEBHOOK_URL'])
    write_file('%s/configuration/grafana-alert-notifications.json' % environment_path, lines)

    file_list = list()
    file_list.append('grafana-dashboards-database.json')
    file_list.append('grafana-dashboards-global.json')
    file_list.append('grafana-dashboards-maya.json')
    file_list.append('grafana-dashboards-penpen.json')
    file_list.append('grafana-dashboards-sachiel.json')
    for ff in file_list:
        lines = read_file('%s/configuration/%s' % (environment_path, ff))
        lines = re_sub_lines(lines, 'ALERT_TITLE_PREFIX', settings['ALERT_TITLE_PREFIX'])
        write_file('%s/configuration/%s' % (environment_path, ff), lines)

    lines = read_file('%s/grafana/grafana.ini' % etc_config_path)
    lines = re_sub_lines(lines, 'HOST_MAYA', host_maya)
    write_file('%s/grafana/grafana.ini' % etc_config_path, lines)

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
    # noinspection PyUnresolvedReferences
    tags.append('git_hash_%s=%s' % (name, git_hash_app.decode('utf-8').strip()))

    cmd = ['create', eb_environment_name]
    cmd += ['--cname', cname]
    cmd += ['--instance_type', 't2.micro']
    cmd += ['--region', aws_default_region]
    cmd += ['--single']
    cmd += ['--tags', ','.join(tags)]
    # to attach network interface located at 'ap-northeast-2a' (subnet_id_1),
    # DO NOT include 'ap-northeast-2c' (subnet_id_2)
    cmd += ['--vpc.ec2subnets', subnet_id_1]
    cmd += ['--vpc.elbsubnets', subnet_id_1]
    cmd += ['--vpc.id', eb_vpc_id]
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
