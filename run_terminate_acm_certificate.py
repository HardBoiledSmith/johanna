#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def get_acm_certificates_list(region):
    aws_cli = AWSCli(region)
    cmd = ['acm', 'list-certificates']
    result = aws_cli.run(cmd)

    return result['CertificateSummaryList']


def find_certificates_arn(list, domain_name):
    for ll in list:
        if ll['DomainName'] == domain_name:
            return ll['CertificateArn']

    return None


def run_terminate_acm_certificate(region, arn):
    print_session('terminate acm certificate')

    aws_cli = AWSCli(region)
    cmd = ['acm', 'delete-certificate']
    cmd += ['--certificate-arn', arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
acm_envs = env['acm']

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('acm', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    certificates_list = get_acm_certificates_list(settings['AWS_REGION'])
    if len(certificates_list) < 1:
        continue

    arn = find_certificates_arn(certificates_list, settings['DOMAIN_NAME'])
    if not arn:
        continue

    run_terminate_acm_certificate(settings['AWS_REGION'], arn)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'acm: {mm} is not found in config.json')
