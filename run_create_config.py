#!/usr/bin/env python3
import json
import subprocess
import sys
from os import listdir
from os import mkdir
from os import path
from shutil import copyfile
from shutil import rmtree
from string import Template

from run_common import AWSCli


def _print_how_to():
    print('please input path')
    print('(sample)')
    print('\t./run_create_config.py path/of/variable.json path/of/templete_config.json')


def generate_config(config_file_name, variable_file_name):
    config_format = open(config_file_name).read()
    tt = Template(config_format)
    dd = open(variable_file_name).read()
    variable = json.loads(dd)
    nn = dict()
    for kk in variable:
        nn[kk] = repr(variable[kk])[1:-1]
    config = tt.safe_substitute(**nn)
    config_file = 'config.json'
    open(config_file, "w+").write(config)


if __name__ == "__main__":
    aws_cli = AWSCli()
    tmp_dir = 'config'

    if len(sys.argv) != 3:
        if not path.exists(sys.argv[1]) or not path.exists(sys.argv[2]):
            _print_how_to()
            exit(1)

    zip_path = sys.argv[1]
    config_file_name = sys.argv[2]

    if not path.exists(tmp_dir):
        mkdir(tmp_dir)

    config_file = path.basename(config_file_name)
    pp = path.join(tmp_dir, config_file)
    copyfile(config_file_name, pp)

    password = input('write password of zip file:\n')
    cmd = ['unzip', '-P', password, '-d', 'config', zip_path]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    variable_file = ''

    for ff in listdir('config'):
        if ff == config_file:
            continue

        if 'variable.json' in ff:
            variable_file = ff
            break

    cc = '%s/%s' % (tmp_dir, config_file)
    vv = '%s/%s' % (tmp_dir, variable_file)
    generate_config(cc, vv)

    rmtree('config')
