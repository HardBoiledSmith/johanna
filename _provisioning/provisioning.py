#!/usr/bin/env python3
import fileinput
import inspect
import os
import re
import subprocess
import time
from datetime import datetime
from multiprocessing import Process
from subprocess import PIPE

env = dict(os.environ)


def _print_line_number(number_of_outer_frame=1):
    cf = inspect.currentframe()
    frame = cf
    for ii in range(number_of_outer_frame):
        frame = frame.f_back

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print('\n'.join(['#' * 40, '[%s] LINE NUMBER: %d' % (timestamp, frame.f_lineno), '#' * 40]))


def _run(cmd, file_path_name=None, cwd=None):
    def _f():
        if not file_path_name:
            _p = subprocess.Popen(cmd, cwd=cwd, env=env)
            _p.communicate()
            if _p.returncode != 0:
                raise Exception()
        else:
            with open(file_path_name, 'a') as f:
                _p = subprocess.Popen(cmd, stdout=f, cwd=cwd, env=env)
                _p.communicate()
                if _p.returncode != 0:
                    raise Exception()

    _print_line_number(2)
    cmd_string = ' '.join(cmd)
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print('\n'.join(['#' * 40, '[%s] COMMAND: %s' % (timestamp, cmd_string), '#' * 40]))

    pp = Process(target=_f)
    pp.start()
    pp.join()
    if pp.exitcode != 0:
        raise Exception()


def _file_line_replace(file_path_name, str_old, str_new, backup='.bak'):
    with fileinput.FileInput(file_path_name, inplace=True, backup=backup) as f:
        for line in f:
            new_line = re.sub(str_old, str_new, line)
            print(new_line, end='')


def _settings_file_line_replace(settings_file_path_name, key, value, backup='.bak'):
    with fileinput.FileInput(settings_file_path_name, inplace=True, backup=backup) as f:
        for line in f:
            new_line = re.sub('^(' + key + ') .*', '\\1 = \'%s\'' % value, line)
            print(new_line, end='')


def _read_settings_file(settings_file_path_name):
    sdd = {}
    with open(settings_file_path_name) as ff:
        for line in ff:
            key, value = line.partition("=")[::2]
            sdd[key.strip()] = value.strip().strip("'")

    return sdd


def _preprocess(hostname):
    _print_line_number()

    _file_line_replace('/etc/sysconfig/network', '^HOSTNAME=localhost.localdomain$', 'HOSTNAME=%s' % hostname)
    with open('/etc/hosts', 'a') as f:
        f.write('127.0.0.1 %s\n' % hostname)
    _run(['hostname', hostname])
    _run(['/etc/init.d/network', 'restart'])

    _print_line_number()

    with open('/etc/server_info', 'w') as f:
        f.write('AWS_EC2_INSTANCE_ID=i-01234567\n')
        f.write('AWS_EC2_AVAILABILITY_ZONE=my-local-1a\n')

    _print_line_number()

    _run(['fallocate', '-l', '2G', '/swapfile'])
    _run(['chmod', '600', '/swapfile'])
    _run(['mkswap', '/swapfile'])
    _run(['swapon', '/swapfile'])
    with open('/etc/fstab', 'a') as f:
        f.write('/swapfile	swap	swap	sw	0	0\n')

    _print_line_number()

    subprocess.Popen(['chpasswd'], stdin=PIPE).communicate(b'root:1234qwer')
    _file_line_replace('/etc/ssh/sshd_config', '^#PermitRootLogin yes$', 'PermitRootLogin yes')
    _file_line_replace('/etc/ssh/sshd_config', '^PasswordAuthentication no$', 'PasswordAuthentication yes')
    _run(['service', 'sshd', 'restart'])

    _print_line_number()

    _run(['yum', '-y', 'erase', 'ntp*'])
    _run(['yum', '-y', 'install', 'chrony'])
    _run(['service', 'chronyd', 'start'])
    _run(['chkconfig', 'chronyd', 'on'])

    _print_line_number()

    _run(['yum', '-y', 'update'])
    file_path_name = '/vagrant/requirements_rpm.txt'
    if os.path.exists(file_path_name):
        with open(file_path_name, 'r') as f:
            lines = f.readlines()
            for ll in lines:
                _run(['yum', '-y', 'install', ll.strip()])

    _print_line_number()

    _run(['ln', '-s', '/usr/bin/pip-3.6', '/usr/bin/pip3'])
    file_path_name = '/vagrant/requirements.txt'
    if os.path.exists(file_path_name):
        with open(file_path_name, 'r') as f:
            lines = f.readlines()
            for ll in lines:
                _run(['pip3', 'install', ll.strip()])

    node_version = 'v10.16.0'
    _run(['wget', 'https://raw.githubusercontent.com/creationix/nvm/v0.33.6/install.sh'], cwd='/root')
    _run(['chmod', '+x', 'install.sh'], cwd='/root')
    _run(['./install.sh'], cwd='/root')

    with open('/root/.npmrc', 'w') as f:
        f.write('unsafe-perm=true\n')
        f.write('user=root')

    with open('/root/install.sh', 'w') as f:
        f.write('#!/usr/bin/env bash\n')
        f.write('source /root/.nvm/nvm.sh\n')
        # remove this node mirror setting if there is any problems
        f.write('export NVM_NODEJS_ORG_MIRROR=https://npm.taobao.org/mirrors/node/\n')
        f.write('nvm install %s\n' % node_version)
        f.write('nvm alias default %s\n' % node_version)
        f.write('nvm use default %s\n' % node_version)
    _run(['chmod', '+x', 'install.sh'], cwd='/root')
    _run(['./install.sh'], cwd='/root')

    env['NVM_BIN'] = '/root/.nvm/versions/node/%s/bin' % node_version
    env['NVM_CD_FLAGS'] = ''
    env['NVM_DIR'] = '/root/.nvm'
    env['NVM_RC_VERSION'] = ''
    env['PATH'] = ('/root/.nvm/versions/node/%s/bin:' % node_version) + env['PATH']
    _run(['npm', 'install', '-g', 'npm@latest'])

    with open('/root/.bashrc', 'a') as f:
        f.write('export NODE_OPTIONS="--max-old-space-size=2048"')


def main():
    hostname = 'dv-johanna-my-local-1a-012345.localdomain'

    _preprocess(hostname)

    _print_line_number()

    _run(['mkdir', '-p', '/root/.ssh'])
    _run(['mkdir', '-p', '/var/log/johanna'])

    _print_line_number()

    cmd_common = ['cp', '--backup']
    file_list = list()
    file_list.append('/root/.ssh/id_rsa')
    for ff in file_list:
        cmd = cmd_common + ['/vagrant/configuration' + ff, ff]
        _run(cmd)

    _print_line_number()

    _run(['chmod', '600', '/root/.ssh/id_rsa'])
    is_success = False
    for ii in range(10):
        print('Git clone try count: %d' % (ii + 1))
        # noinspection PyBroadException
        try:
            # Non interactive git clone (ssh fingerprint prompt)
            _run(['ssh-keyscan', 'github.com'], '/root/.ssh/known_hosts')
            _run(['git', 'clone', '--depth=1', 'git@github.com:HardBoiledSmith/johanna.git'], cwd='/opt')
            if os.path.exists('/opt/johanna'):
                is_success = True
                break
        except Exception:
            time.sleep(3)

    if not is_success:
        raise Exception()

    _print_line_number()

    cmd_common = ['mv']
    file_list = list()
    file_list.append('/opt/johanna/config.json')

    local_config_path = '/vagrant/opt/johanna/config.json'
    for ff in file_list:
        cmd = cmd_common + [local_config_path, ff]
        _run(cmd)

    _print_line_number()

    _run(['reboot'])


if __name__ == "__main__":
    main()
