#!/usr/bin/env python3
import os
import subprocess
import re
from datetime import datetime

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()

print_session('reset database')

phase = env['common']['PHASE']
if phase == 'op':
    print('\'OP\' phase does not allow this operation.')
    raise Exception()

check_template_availability()

engine = env['rds']['ENGINE']
if engine not in ('aurora', 'aurora-mysql', 'aurora-postgresql'):
    print('not supported:', engine)
    raise Exception()

print_message('get database address')

if phase != 'dv':
    db_host = aws_cli.get_rds_address()
else:
    while True:
        answer = input('Do you use a database of Vagrant VM? (yes/no): ')
        if answer.lower() == 'no':
            db_host = aws_cli.get_rds_address()
            break
        if answer.lower() == 'yes':
            db_host = 'dv-database.hbsmith.io'
            break

db_password = env['rds']['USER_PASSWORD']
db_user = env['rds']['USER_NAME']
database = env['rds']['DATABASE']
template_name = env['template']['NAME']

print_message('git clone')

git_url = env['rds']['GIT_URL']
mm = re.match(r'^.+/(.+)\.git$', git_url)
if not mm:
    raise Exception()

git_folder_name = mm.group(1)

template_path = 'template/%s' % git_folder_name

subprocess.Popen(['rm', '-rf', template_path]).communicate()
subprocess.Popen(['mkdir', '-p', template_path]).communicate()

if phase == 'dv':
    git_command = ['git', 'clone', '--depth=1', git_url]
else:
    git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]

subprocess.Popen(git_command, cwd='./template').communicate()
if not os.path.exists(template_path):
    raise Exception()

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

filename = '%s/mysql_schema.sql' % template_path
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

filename = '%s/mysql_data.sql' % template_path
with open(filename, 'r') as f:
    subprocess.Popen(cmd, stdin=f).communicate()

finish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(' '.join(['Finished at:', finish_time]))
