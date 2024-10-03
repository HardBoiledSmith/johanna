#!/usr/bin/env python3

import json
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_session


################################################################################
#
# start
#
################################################################################
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='pass confirm')
    parser.add_argument('-ah', '--alias_hosted_zone_id', type=str, required=False, help='hosted zone id of alias')
    parser.add_argument('-at', '--alias_type', type=str, required=False, choices=['cloudfront', 's3'],
                        help='type of alias')
    parser.add_argument('-d', '--domain_name', type=str, required=True,
                        help='domain name(s3 -> end point, cloudfront -> domain name)')
    parser.add_argument('-hn', '--hosted_zone_name', type=str, required=True, help='name of hosted zone')
    parser.add_argument('-n', '--name', type=str, required=True, help='acm arn')
    parser.add_argument('-r', '--record_set_type', type=str, required=True, help='type of record_set')

    args = parser.parse_args()

    if not args.force:
        _confirm_phase()

    return args


def is_exist_record_set(host_zone_name, name):
    print_session('is_exist_record_set')
    aws_cli = AWSCli()
    cmd = ['route53', 'list-hosted-zones-by-name']
    cmd += ['--dns-name', host_zone_name]
    rr = aws_cli.run(cmd)

    if not (len(rr['HostedZones']) == 1):
        raise Exception('wrong host zone')

    hosted_zone_id = rr['HostedZones'][0]['Id']

    cmd = ['route53', 'list-resource-record-sets']
    cmd += ['--hosted-zone-id', hosted_zone_id]
    rr = aws_cli.run(cmd)

    for vv in rr['ResourceRecordSets']:
        if vv['Name'] == name:
            print_session('exist record set(%s)' % name)
            return True

    return False


def find_host_zone_id(host_zone_name):
    print_session('find_host_zone_id')
    aws_cli = AWSCli()
    cmd = ['route53', 'list-hosted-zones-by-name']
    cmd += ['--dns-name', host_zone_name]
    rr = aws_cli.run(cmd)

    if not (len(rr['HostedZones']) == 1):
        raise Exception('wrong host zone')

    return rr['HostedZones'][0]['Id']


def find_cloudfront(domain_name):
    aws_cli = AWSCli()
    cmd = ['cloudfront', 'list-distributions']
    rr = aws_cli.run(cmd)

    for vv in rr['DistributionList']['Items']:
        if 'Items' in vv['Aliases'] and domain_name in vv['Aliases']['Items']:
            return vv


def create_route53(name, host_zone_name, type, domain_name, alias=None):
    rrs = dict()
    if alias:
        if alias['TYPE'] == 'cloudfront':
            rr = find_cloudfront(domain_name)
            domain_name = rr['DomainName']

        rrs = {
            "Name": name,
            "Type": type,
            "AliasTarget": {
                "HostedZoneId": alias['HOSTED_ZONE_ID'],
                "DNSName": domain_name,
                "EvaluateTargetHealth": False
            }
        }
    else:
        rrs = {
            "Name": name,
            "Type": type,
            "ResourceRecord": [
                {
                    "Value": domain_name
                }
            ]
        }

    dd = dict()
    dd['Changes'] = [
        {
            "Action": "CREATE",
            "ResourceRecordSet": rrs
        }
    ]

    aws_cli = AWSCli()
    cmd = ['route53', 'change-resource-record-sets']
    id = find_host_zone_id(host_zone_name)
    cmd += ['--hosted-zone-id', id]
    cmd += ['--change-batch', json.dumps(dd)]
    rr = aws_cli.run(cmd)
    return rr


if __name__ == '__main__':
    args = parse_args()
    hosted_zone_name = args.hosted_zone_name
    name = args.name
    record_set_type = args.record_set_type
    domain_name = args.domain_name
    alias_hosted_zone_id = args.alias_hosted_zone_id
    alias_type = args.alias_type

    alias = None
    if alias_type:
        alias = dict()
        alias['TYPE'] = alias_type
        alias['HOSTED_ZONE_ID'] = alias_hosted_zone_id

    if is_exist_record_set(hosted_zone_name, name):
        exit(1)

    create_route53(name, hosted_zone_name, record_set_type, domain_name, alias)
