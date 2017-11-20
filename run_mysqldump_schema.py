#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from datetime import datetime
from subprocess import PIPE
from time import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def _auto_hourly_backup(path_config):
    config_dict = dict()
    with open(path_config + '/my.cnf', 'r') as ff:
        ll_iter = ff.readlines()
        for ll in ll_iter:
            ll_part = ll.split('=')
            if len(ll_part) != 2:
                continue
            config_dict[ll_part[0].strip()] = ll_part[1].strip()

    host = config_dict['host']
    user = config_dict['user']
    password = config_dict['password']
    database = config_dict['database']

    time_now = int(time())
    time_now_yyyymmdd_hhmmss = datetime.fromtimestamp(time_now).strftime('%Y%m%d_%H%M00')
    cwd = '/tmp'
    filename = 'mysql_schema_%s.sql' % time_now_yyyymmdd_hhmmss
    filename_zip = filename + '.zip'
    cwd_filename = '/'.join([cwd, filename])

    _mysql_dump(host, user, password, database, cwd_filename)

    cmd = ['zip']
    cmd += ['-e', filename_zip]
    cmd += ['-P', password]
    cmd += [filename]

    print('\n>>> ' + ' '.join(cmd) + '\n')

    subprocess.Popen(cmd, cwd=cwd, stdout=PIPE).communicate()

    _s3_upload(path_config, cwd, time_now_yyyymmdd_hhmmss[:8], filename_zip)

    cmd = ['rm', filename, filename_zip]

    subprocess.Popen(cmd, cwd=cwd, stdout=PIPE).communicate()


def _manual_backup():
    aws_cli = AWSCli()

    ################################################################################
    print_session('dump mysql schema')

    engine = env['rds']['ENGINE']
    if engine not in ('mysql', 'aurora'):
        print('not supported:', engine)
        raise Exception()

    ################################################################################
    print_message('get database address')

    host = 'dv-database.hbsmith.io'
    answer = 'no'
    if env['common']['PHASE'] == 'dv':
        answer = input('Do you use a database of Vagrant VM? (yes/no): ')
    if answer != 'yes':
        host = aws_cli.get_rds_address(read_replica=True)

    database = env['rds']['DATABASE']
    password = env['rds']['USER_PASSWORD']
    user = env['rds']['USER_NAME']

    template_name = env['template']['NAME']
    filename_path = 'template/%s/rds/mysql_schema.sql' % template_name

    _mysql_dump(host, user, password, database, filename_path)


def _mysql_dump(host, user, password, database, filename_path):
    ################################################################################
    print_message('dump schema')

    cmd = ['mysqldump']
    cmd += ['-h' + host]
    cmd += ['-u' + user]
    cmd += ['-p' + password]
    cmd += ['--comments']
    cmd += ['--databases', database]
    cmd += ['--ignore-table=%s.django_migrations' % database]
    cmd += ['--no-data']

    print('\n>>> ' + ' '.join(cmd) + '\n')

    data = subprocess.Popen(cmd, stdout=PIPE).communicate()[0].decode()
    line = data.split('\n')
    with open(filename_path, 'w') as f:
        for ll in line:
            ll = re.sub('^-- MySQL dump.*$', '', ll)
            ll = re.sub('^-- Host.*$', '', ll)
            ll = re.sub('^-- Server version.*$', '', ll)
            ll = re.sub(' AUTO_INCREMENT=[0-9]*', '', ll)
            ll = re.sub('^-- Dump completed on.*$', '', ll)
            f.write(ll + '\n')


def _s3_upload(path_config, cwd, yyyymmdd, filename):
    sys.path.append(path_config)
    # noinspection PyPep8,PyUnresolvedReferences
    from settings_local import AWS_DEFAULT_REGION, \
        AWS_S3_BACKUP_BUCKET, \
        BILLING_AWS_ACCESS_KEY_ID, \
        BILLING_AWS_SECRET_ACCESS_KEY, \
        PHASE

    ee = dict(os.environ)
    ee['AWS_ACCESS_KEY_ID'] = BILLING_AWS_ACCESS_KEY_ID
    ee['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    ee['AWS_SECRET_ACCESS_KEY'] = BILLING_AWS_SECRET_ACCESS_KEY

    s3_filename = '/'.join(['s3://' + AWS_S3_BACKUP_BUCKET, PHASE + '-' + yyyymmdd, filename])

    cmd = ['aws', 's3', 'cp', filename, s3_filename]

    subprocess.Popen(cmd, cwd=cwd, env=ee, stdout=PIPE).communicate()


################################################################################
#
# start
#
################################################################################
print_session('mysqldump data')

################################################################################
if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    if len(args) != 2 \
            or not os.path.exists(args[1] + '/my.cnf') \
            or not os.path.exists(args[1] + '/settings_local.py'):
        print('input the path of \'my.conf\' and \'settings_local.py\'')
        sys.exit()

    _auto_hourly_backup(args[1])
else:
    _manual_backup()
