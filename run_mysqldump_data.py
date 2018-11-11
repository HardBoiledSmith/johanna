#!/usr/bin/env python3
import subprocess
from subprocess import PIPE

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def _manual_backup():
    aws_cli = AWSCli()

    ################################################################################
    print_session('dump mysql data')

    engine = env['rds']['ENGINE']
    if engine not in ('aurora', 'aurora-mysql', 'aurora-postgresql'):
        print('not supported:', engine)
        raise Exception()

    ################################################################################
    print_message('get database address')

    if env['common']['PHASE'] != 'dv':
        host = aws_cli.get_rds_address(read_replica=True)
    else:
        while True:
            answer = input('Do you use a database of Vagrant VM? (yes/no): ')
            if answer.lower() == 'no':
                host = aws_cli.get_rds_address(read_replica=True)
                break
            if answer.lower() == 'yes':
                host = 'dv-database.hbsmith.io'
                break

    database = env['rds']['DATABASE']
    password = env['rds']['USER_PASSWORD']
    user = env['rds']['USER_NAME']

    template_name = env['template']['NAME']
    filename_path = 'template/%s/rds/mysql_data.sql' % template_name

    _mysql_dump(host, user, password, database, filename_path)


def _mysql_dump(host, user, password, database, filename_path):
    ################################################################################
    print_message('dump data')

    cmd = ['mysqldump']
    cmd += ['-h' + host]
    cmd += ['-u' + user]
    cmd += ['-p' + password]
    cmd += ['--column-statistics=0']
    cmd += ['--comments']
    cmd += ['--databases', database]
    cmd += ['--hex-blob']
    cmd += ['--ignore-table=%s.auth_permission' % database]
    cmd += ['--ignore-table=%s.django_content_type' % database]
    cmd += ['--ignore-table=%s.django_migrations' % database]
    cmd += ['--ignore-table=%s.django_session' % database]
    cmd += ['--no-create-info']
    cmd += ['--single-transaction']
    cmd += ['--skip-extended-insert']

    print('\n>>> ' + ' '.join(cmd) + '\n')

    filename_path_raw = filename_path + '.raw'

    with open(filename_path_raw, 'w') as ff:
        subprocess.Popen(cmd, stdout=ff).communicate()

    with open(filename_path_raw, 'r') as ff_raw, open(filename_path, 'w') as ff:
        case_alarm_insert_count = 0
        scenario_alarm_insert_count = 0
        while True:
            line = ff_raw.readline()
            if not line:
                break

            if line.startswith('-- MySQL dump') or \
                    line.startswith('-- Host') or \
                    line.startswith('-- Server version') or \
                    line.startswith('-- Dump completed on'):
                ff.write('\n')
                continue

            if 'INSERT INTO `auth_user` VALUES (' in line:
                ss = line.split(',')
                if ss[0].endswith('(1') or ss[0].endswith('(2'):
                    ss[1] = "'pbkdf2_sha256$36000$1eLKAkz2Ki55$jrvEzikMhfTLm/tYzfdTcWndnMddR9fMucTpvcVYqSc='"
                else:
                    ss[7] = "'bounced@hbsmith.io'"
                if ss[0].endswith('(2'):
                    ss[4] = "'dev0000@hbsmith.io'"
                    ss[7] = "'hello@hbsmith.io'"
                line = ','.join(ss)
            elif 'INSERT INTO `hbsmith_team` VALUES (' in line:
                ss = line.split(',')
                ss[3:6] = ["''", "''", "''"]
                line = ','.join(ss)
            elif 'INSERT INTO `hbsmith_case` VALUES (' in line:
                ss = line.split(',')
                ss[-4] = 'NULL'
                line = ','.join(ss)
            elif 'INSERT INTO `hbsmith_scenario` VALUES (' in line:
                ss = line.split(',')
                ss[-6:-4] = ["''", 'NULL']
                line = ','.join(ss)
            elif 'INSERT INTO `hbsmith_case_alarm` VALUES (' in line:
                case_alarm_insert_count += 1
                if case_alarm_insert_count >= 1000:
                    continue
            elif 'INSERT INTO `hbsmith_scenario_alarm` VALUES (' in line:
                scenario_alarm_insert_count += 1
                if scenario_alarm_insert_count >= 1000:
                    continue
            elif 'INSERT INTO `hbsmith_bounced_email` VALUES (' in line:
                ss = line.split(',')
                if ss[0].endswith('(1'):
                    ss[3] = "'bounced@hbsmith.io');\n"
                line = ','.join(ss)
            elif any([(lambda qq: qq in line)(qq) for qq in [
                'INSERT INTO `hbsmith_cache` VALUES (',
                'INSERT INTO `oauth2_provider_accesstoken` VALUES (',
                'INSERT INTO `oauth2_provider_refreshtoken` VALUES (',
                'INSERT INTO `hbsmith_case_result` VALUES (',
                'INSERT INTO `hbsmith_scenario_result` VALUES (',
                'INSERT INTO `hbsmith_case_lock` VALUES (',
                'INSERT INTO `hbsmith_scenario_lock` VALUES (',
                'INSERT INTO `hbsmith_report_lock` VALUES (',
                'INSERT INTO `hbsmith_revenue_lock` VALUES ('
            ]]):
                continue
            ff.write(line)

    cmd = ['rm', filename_path_raw]

    subprocess.Popen(cmd, stdout=PIPE).communicate()


################################################################################
#
# start
#
################################################################################
print_session('mysqldump data')

################################################################################
if __name__ != "__main__":
    _manual_backup()
