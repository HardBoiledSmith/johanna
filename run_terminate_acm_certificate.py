#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_session
from env import env
import sys


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
if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()
    acm_envs = env['acm']

    target_name = None
    check_exists = False

    if len(args) > 1:
        target_name = args[1]

    list_region = {}
    for ee in acm_envs:
        rr = ee['AWS_DEFAULT_REGION']
        list_region.add(rr)

    certificates_list = []
    for rr in list_region:
        certificates_list += get_acm_certificates_list(rr)

        if len(certificates_list) < 1:
            continue

        for acm_env in acm_envs:
            if target_name and acm_env['NAME'] != target_name:
                continue

            if target_name:
                check_exists = True

            arn = find_certificates_arn(certificates_list, acm_env['DOMAIN_NAME'])
            if arn:
                run_terminate_acm_certificate(rr, arn)

    if not check_exists and target_name:
        print(f'{target_name} is not exists in config.json')
