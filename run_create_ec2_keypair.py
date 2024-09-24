#!/usr/bin/env python3.12
import os
import subprocess
from multiprocessing import Process

env = dict(os.environ)


def read_file(file_path):
    f = open(file_path)
    lines = list()
    for ll in f.readlines():
        lines.append(ll)
    f.close()

    return lines


# noinspection PyShadowingNames
def run(cmd, file_path_name=None, cwd=None):
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

    pp = Process(target=_f)
    pp.start()
    pp.join()
    if pp.exitcode != 0:
        raise Exception()


def run_create_ec2_keypair(key_name):
    cmd = ['rm', '-f']
    cmd += [f'{key_name}.pem']
    cmd += [f'{key_name}.pub']
    run(cmd)

    cmd = ['openssl', 'genrsa']
    cmd += ['-out', f'{key_name}.pem']
    cmd += ['2048']
    run(cmd)

    print('Private key file:', f'{key_name}.pem', '\n')

    run(['chmod', '400', f'{key_name}.pem'])

    cmd = ['openssl', 'rsa']
    cmd += ['-in', f'{key_name}.pem']
    cmd += ['-pubout']
    run(cmd, file_path_name=f'{key_name}.pub')

    print('Public key file:', f'{key_name}.pub', '\n')

    print('AWS_KEY_PAIR_NAME:', key_name, '\n')

    pub_key = read_file(f'{key_name}.pub')
    pub_key = pub_key[1:-1]
    pp_list = list()
    for pk in pub_key:
        pk = pk.strip()
        pp_list.append(pk)
    pub_key = ''.join(pp_list)
    print('AWS_KEY_PAIR_MATERIAL:', pub_key, '\n')

    run(['chmod', '400', f'{key_name}.pub'])

    cmd = ['ssh-keygen', '-y']
    cmd += ['-f', f'{key_name}.pem']
    result, error = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE).communicate()
    # noinspection PyUnresolvedReferences
    result = result.decode('utf-8')
    print('OpenSSH public key:', result.strip(), '\n')

    cmd = ['openssl', 'pkey']
    cmd += ['-in', f'{key_name}.pem']
    cmd += ['-pubout']
    cmd += ['-outform', 'DER']
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
    cmd = ['openssl', 'md5', '-c']
    result, _ = subprocess.Popen(cmd, env=env, stdin=proc.stdout, stdout=subprocess.PIPE).communicate()
    # noinspection PyUnresolvedReferences
    result = result.decode('utf-8')
    print('OpenSSH finger print:', result)

    return pub_key


################################################################################
#
# start
#
################################################################################

if __name__ == "__main__":
    from run_common import parse_args

    _, args = parse_args()

    if len(args) != 2:
        print('usage:', args[0], '<key-name>')
        raise Exception()

    run_create_ec2_keypair(args[1])
