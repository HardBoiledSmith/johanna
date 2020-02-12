#!/usr/bin/env python3

import json
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_message


################################################################################
#
# start
#
################################################################################
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='pass confirm')
    parser.add_argument('-b', '--backet', type=str, required=True, help='static web bucket name')
    parser.add_argument('-e', '--endpoint', type=str, required=True, help='s3 bucket end point')
    parser.add_argument('-a', '--acm-arn', dest='acm_arn', type=str, required=True, help='acm arn')
    parser.add_argument('-c', '--cname', type=str, required=True, nargs='+', help='cname')

    args = parser.parse_args()

    if not args.force:
        _confirm_phase()

    return args


def is_exist_cname(cname_list):
    aws_cli = AWSCli()
    cmd = ['cloudfront', 'list-distributions']
    rr = aws_cli.run(cmd)

    for vv in rr['DistributionList']['Items']:
        for cc in cname_list:
            if 'Items' in vv['Aliases'] and cc in vv['Aliases']['Items']:
                print_message('exist cname(%s)' % cc)
                return True

    return False


def create_cloudfront(bucket_name, origin_url, certificate_arn, cname_list):
    origin_id = 'S3-Website-%s' % bucket_name

    dd = dict()
    dd['PriceClass'] = 'PriceClass_200'
    dd['CallerReference'] = bucket_name
    dd['Comment'] = ''
    dd['Enabled'] = True

    dd['Aliases'] = {
        'Quantity': len(cname_list),
        'Items': cname_list
    }

    dd['Origins'] = {
        'Quantity': 1,
        'Items': [
            {
                'Id': origin_id,
                'DomainName': origin_url,
                'CustomOriginConfig': {
                    'HTTPPort': 80,
                    'HTTPSPort': 443,
                    'OriginProtocolPolicy': 'http-only',
                    'OriginSslProtocols': {
                        'Items': [
                            'TLSv1',
                            'TLSv1.1',
                            'TLSv1.2'
                        ],
                        'Quantity': 3
                    }
                }
            }
        ]
    }

    dd['DefaultCacheBehavior'] = {
        'TargetOriginId': origin_id,
        'ViewerProtocolPolicy': 'redirect-to-https',
        'AllowedMethods': {
            'CachedMethods': {
                'Items': ['HEAD', 'GET'],
                'Quantity': 2
            },
            'Items': ['HEAD', 'GET'],
            'Quantity': 2
        },
        'Compress': False,
        'ForwardedValues': {
            'QueryString': False,
            'Cookies': {
                'Forward': 'none'
            },
            'Headers': {
                'Quantity': 0
            },
            'QueryStringCacheKeys': {
                'Quantity': 0
            }
        },
        'TrustedSigners': {
            'Enabled': False,
            'Quantity': 0
        },
        "MinTTL": 0,
        "DefaultTTL": 86400,
        "MaxTTL": 31536000
    }

    dd['ViewerCertificate'] = {
        'ACMCertificateArn': certificate_arn,
        'Certificate': certificate_arn,
        'CertificateSource': 'acm',
        'MinimumProtocolVersion': 'TLSv1.1_2016',
        'SSLSupportMethod': 'sni-only'
    }

    aws_cli = AWSCli()
    cmd = ['cloudfront', 'create-distribution']
    cmd += ['--distribution-config', json.dumps(dd)]
    rr = aws_cli.run(cmd)
    return rr


def create_route53(name, type, dns_name, alias_hostzon_id):
    rrs = dict()
    if alias_hostzon_id:
        rrs = {
            "Name": name,
            "Type": type,
            "AliasTarget": {
                "HostedZoneId": alias_hostzon_id,
                "DNSName": dns_name,
                "EvaluateTargetHealth": False
            }
        }
    else:
        rrs = {
            "Name": name,
            "Type": type,
            "ResourceRecord": [
                {
                    "Value": dns_name
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
    cmd += ['--change-batch', json.dumps(dd)]
    rr = aws_cli.run(cmd)
    return rr


if __name__ == '__main__':
    args = parse_args()
    bucket_name = args.backet
    origin_domain_name = args.endpoint
    certificate_arn = args.acm_arn
    cname_list = args.cname

    if is_exist_cname(cname_list):
        exit(1)

    create_cloudfront(bucket_name, origin_domain_name, certificate_arn, cname_list)
