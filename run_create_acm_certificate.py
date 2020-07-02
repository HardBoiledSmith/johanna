#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_session
from env import env


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
    print_session('create acm certificate')

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
if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()
    acm_envs = env['acm']

    target_name = None
    check_exists = False

    if len(args) > 1:
        target_name = args[1]

    for acm_env in acm_envs:
        if target_name and acm_env['NAME'] != target_name:
            continue

        certificates_list = get_acm_certificates_list(acm_env['AWS_DEFAULT_REGION'])
        if find_certificates_arn(certificates_list, acm_env['DOMAIN_NAME']) is not None:
            continue

        if target_name:
            check_exists = True

        run_create_acm_certificate(acm_env['DOMAIN_NAME'], acm_env['ADDITIONAL_NAMES'],
                                   acm_env['VALIDATION_METHOD'], acm_env['AWS_DEFAULT_REGION'])

    if not check_exists and target_name:
        print(f'{target_name} is not exists in config.json')
