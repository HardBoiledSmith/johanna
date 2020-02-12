#!/usr/bin/env python3

import json
import re
from argparse import ArgumentParser

from run_common import AWSCli
from run_common import _confirm_phase
from run_common import print_session


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='pass confirm')
    parser.add_argument('-hn', '--hosted_zone_name', type=str, required=True, help='name of hosted zone')
    parser.add_argument('-n', '--name', type=str, required=True, help='acm arn')

    args = parser.parse_args()

    if not args.force:
        _confirm_phase()

    return args


def find_host_zone_id(host_zone_name):
    print_session('find_host_zone_id')
    aws_cli = AWSCli()
    cmd = ['route53', 'list-hosted-zones-by-name']
    cmd += ['--dns-name', host_zone_name]
    rr = aws_cli.run(cmd)

    if not (len(rr['HostedZones']) == 1):
        raise Exception('wrong host zone')

    return rr['HostedZones'][0]['Id']


def delete_route53(name, host_zone_name):
    id = find_host_zone_id(host_zone_name)

    aws_cli = AWSCli()
    cmd = ['route53', 'list-resource-record-sets']
    cmd += ['--hosted-zone-id', id]
    rr = aws_cli.run(cmd)

    for rrs in rr['ResourceRecordSets']:
        if rrs['Name'] == name + '.':
            dd = dict()
            dd['Changes'] = [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": rrs
                }
            ]

            aws_cli = AWSCli()
            cmd = ['route53', 'change-resource-record-sets']
            id = find_host_zone_id(host_zone_name)
            cmd += ['--hosted-zone-id', id]
            cmd += ['--change-batch', json.dumps(dd)]
            rr = aws_cli.run(cmd)
            print(rr)


################################################################################
#
# start
#
################################################################################


if __name__ == "__main__":
    args = parse_args()

    hosted_zone_name = args.hosted_zone_name
    name = args.name

    cc = re.split('-|\.', name)
    if not 'dv' in cc:
        print('only can delete dv')
        exit(1)

    delete_route53(name, hosted_zone_name)
