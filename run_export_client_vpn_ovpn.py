#!/usr/bin/env python3
import os
import re
import json
import subprocess
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from multiprocessing import Process
from time import time
import base64

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import write_file

_env = dict(os.environ)

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def send_email(settings, subject, email_to, text, zip_filename):
    aws_cli = AWSCli('us-east-1')

    phase = env['common']['PHASE']
    timestamp_now = str(datetime.now())[:19]
    msg = MIMEMultipart()
    msg['Subject'] = f'[{phase}] {subject} ({timestamp_now})'
    msg['From'] = settings['EMAIL_FROM']
    msg['To'] = email_to
    msg['Bcc'] = settings['EMAIL_BCC']

    msg.preamble = 'Multipart message.\n'

    part = MIMEText(text)
    msg.attach(part)

    part = MIMEApplication(open(zip_filename, 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename=zip_filename.split('/')[-1])
    msg.attach(part)

    content = dict()
    content['Data'] = msg.as_string()
    content = json.dumps(content)
    with open(f'{zip_filename}.json', 'w') as ff:
        ff.write(content)

    cmd = ['ses', 'send-raw-email']
    cmd += ['--raw-message', f'file://{zip_filename}.json']
    aws_cli.run(cmd)


def run(cmd, file_path_name=None, yes=None, cwd=None):
    def _f():
        stdin = None
        if type(yes) is str:
            stdin = subprocess.Popen(['yes', yes], stdout=subprocess.PIPE).stdout

        if not file_path_name:
            _p = subprocess.Popen(cmd, stdin=stdin, cwd=cwd, env=_env)
            _p.communicate()
            if _p.returncode != 0:
                raise Exception()
        else:
            with open(file_path_name, 'a') as ff:
                _p = subprocess.Popen(cmd, stdin=stdin, stdout=ff, cwd=cwd, env=_env)
                if stdin:
                    _p.stdin.write(yes)
                _p.communicate()
                if _p.returncode != 0:
                    raise Exception()

    pp = Process(target=_f)
    pp.start()
    pp.join()
    if pp.exitcode != 0:
        raise Exception()


def run_export_new_client_ovpn(name, settings, email_to, password):
    vpc_region = settings['AWS_VPC_REGION']
    aws_cli = AWSCli(vpc_region)
    print_message(f'create new client config for {name}')

    phase = env['common']['PHASE']

    user = email_to.split('@')[0]
    str_time_now = str(int(time()))
    client_name = '%s-%s' % (user, str_time_now)

    ################################################################################
    print_message('generate new easyrsa pki')

    cwd = '/etc/openvpn/easy-rsa'

    cmd = ['./easyrsa', 'init-pki']
    run(cmd, yes='yes', cwd=cwd)

    cmd = ['./easyrsa', 'build-ca', 'nopass']
    run(cmd, yes='', cwd=cwd)

    write_file(f'{cwd}/pki/ca.crt', settings['CA_CRT'])
    write_file(f'{cwd}/pki/private/ca.key', settings['CA_KEY'])

    cmd = ['./easyrsa', 'build-client-full', client_name, 'nopass']
    run(cmd, cwd=cwd)

    with open(cwd + '/pki/issued/%s.crt' % client_name, 'r') as ff:
        openvpn_client_cert = ff.readlines()
        openvpn_client_cert = ''.join(openvpn_client_cert)
        openvpn_client_cert = openvpn_client_cert.strip()

    with open(cwd + '/pki/private/%s.key' % client_name, 'r') as ff:
        openvpn_client_key = ff.readlines()
        openvpn_client_key = ''.join(openvpn_client_key)
        openvpn_client_key = openvpn_client_key.strip()

    ################################################################################
    print_message('get endpoint id')

    cmd = ['ec2', 'describe-client-vpn-endpoints']
    result = aws_cli.run(cmd)

    vpn_endpoint_id = None
    for r in result['ClientVpnEndpoints']:
        if not r['Tags']:
            continue

        for t in r['Tags']:
            if t['Key'] == 'Name' and t['Value'] == settings['NAME']:
                vpn_endpoint_id = r['ClientVpnEndpointId']
                break

        if vpn_endpoint_id:
            break

    if not vpn_endpoint_id:
        print('ERROR!!! No client vpn endpoint found')
        raise Exception()

    ################################################################################
    print_message('generate new client ovpn file')

    prefix = f'{phase}-{name}-{client_name}'

    cmd = ['ec2', 'export-client-vpn-client-configuration']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--output', 'text']
    result = aws_cli.run(cmd)

    result = result.replace('remote cvpn-endpoint', f'remote {prefix}.cvpn-endpoint')

    dd = ['</ca>']
    dd += ['<cert>', f'{openvpn_client_cert}', '</cert>']
    dd += ['<key>', f'{openvpn_client_key}', '</key>']
    result = result.replace('</ca>\n', '\n'.join(dd))

    filename = f'/tmp/{prefix}.ovpn'
    write_file(filename, result)

    zip_filename = f'/tmp/{prefix}-ovpn.zip'
    cmd = ['zip', '-j', '-P', password, zip_filename, filename]
    run(cmd)

    ################################################################################
    print_message(f'send zipped ovpn to {email}')

    domain = f'{prefix}'

    ll = result.split('\n')
    for line in ll:
        mm = re.match(r'^remote (.+\.cvpn-endpoint.+) .+$', line)
        if mm:
            domain = mm[1]
            break

    subject = f'openvpn client (domain:{domain})'
    text = ''
    text += '\n!!! DO NOT SHARE THIS WITH OTHERS !!!'
    text += '\n'
    text += f'\nemail address: {email_to}'
    text += f'\nopenvpn client (domain:{domain})'

    send_email(settings, subject, email_to, text, zip_filename)


################################################################################
#
# start
#
################################################################################
print_session('export ovpn files for client vpn')

################################################################################

check_exists = False

if len(args) != 5:
    print('usage:', args[0], '<name> <region> <user-email> <password>')
    raise Exception()

target_name = args[1]
region = args[2]
email = args[3]
password = args[4]

for vpn_env in env['client_vpn']:
    if vpn_env['NAME'] != target_name:
        continue

    if vpn_env.get('AWS_VPC_REGION') != region:
        continue

    run_export_new_client_ovpn(vpn_env['NAME'], vpn_env, email, password)

if not check_exists and target_name:
    print(f'{target_name} is not exists in config.json')
