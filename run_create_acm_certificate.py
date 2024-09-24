#!/usr/bin/env python3.12

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


def run_create_acm_certificate(domain_name, additional_names, validation_method, region):
    print_session('create certificate')

    aws_cli = AWSCli(region)
    cmd = ['acm', 'request-certificate']
    cmd += ['--domain-name', domain_name]
    if additional_names:
        cmd += ['--subject-alternative-names', ' '.join(additional_names)]

    cmd += ['--validation-method', validation_method]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create acm')

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
    if find_certificates_arn(certificates_list, settings['DOMAIN_NAME']) is not None:
        continue

    is_target_exists = True

    run_create_acm_certificate(settings['DOMAIN_NAME'], settings['ADDITIONAL_NAMES'],
                               settings['VALIDATION_METHOD'], settings['AWS_REGION'])

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'acm: {mm} is not found in config.json')
