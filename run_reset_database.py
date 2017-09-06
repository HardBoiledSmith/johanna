#!/usr/bin/env python3
import subprocess
from datetime import datetime

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()

print_session('reset database')

check_template_availability()

engine = env['rds']['ENGINE']
if engine not in ('mysql', 'aurora'):
    print('not supported:', engine)
    raise Exception()

print_message('get database address')

db_host = 'dv-database.hbsmith.io'
answer = 'no'
if env['common']['PHASE'] == 'dv':
    answer = input('Do you use a database of Vagrant VM? (yes/no): ')
if answer != 'yes':
    db_host = aws_cli.get_rds_address(read_replica=True)

db_password = env['rds']['USER_PASSWORD']
db_user = env['rds']['USER_NAME']
database = env['rds']['DATABASE']
template_name = env['template']['NAME']

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

filename = 'template/%s/rds/mysql_schema.sql' % template_name
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

filename = 'template/%s/rds/mysql_data.sql' % template_name
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

finish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(' '.join(['Finished at:', finish_time]))
