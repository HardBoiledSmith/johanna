#!/usr/bin/env python3
import os.path
import subprocess
from datetime import datetime

from env import env
from run_common import AWSCli
from run_common import download_template
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()

print_session('reset database')

engine = env['rds']['ENGINE']
if engine != 'mysql':
    print('not supported:', engine)
    raise Exception()

print_message('get database address')

db_host = aws_cli.get_rds_address()
db_user = env['rds']['USER_NAME']
db_password = env['rds']['USER_PASSWORD']
database = env['rds']['DATABASE']

print_message('reset database')

cmd_common = ['mysql']
cmd_common += ['-h' + db_host]
cmd_common += ['-u' + db_user]
cmd_common += ['-p' + db_password]

start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(' '.join(['Started at:', start_time]))

cmd = cmd_common + ['-e', 'DROP DATABASE IF EXISTS `%s`;' % database]
subprocess.Popen(cmd).communicate()

cmd = cmd_common + ['-e', 'CREATE DATABASE `%s` CHARACTER SET utf8;' % database]
subprocess.Popen(cmd).communicate()

cmd = cmd_common + ['--comments']

template_name = env['template']['NAME']
if not os.path.exists('template/%s' % template_name):
    download_template()

filename = 'template/%s/rds/mysql_schema.sql' % template_name
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

filename = 'template/%s/rds/mysql_data.sql' % template_name
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

finish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(' '.join(['Finished at:', finish_time]))
