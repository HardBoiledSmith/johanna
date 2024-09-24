#!/usr/bin/env python3.12

import json
import re
from argparse import ArgumentParser
from time import sleep

from run_common import AWSCli
from run_common import _confirm_phase


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='pass confirm')
    parser.add_argument('-c', '--cname', type=str, required=True, help='cname')

    args = parser.parse_args()

    if not args.force:
        _confirm_phase()

    return args


def find_cloudfront(domain_name):
    aws_cli = AWSCli()
    cmd = ['cloudfront', 'list-distributions']
    rr = aws_cli.run(cmd)

    for vv in rr['DistributionList']['Items']:
        if 'Items' in vv['Aliases'] and domain_name in vv['Aliases']['Items']:
            return vv


def delete_cloudfront(id):
    aws_cli = AWSCli()
    cmd = ['cloudfront', 'get-distribution']
    cmd += ['--id', id]
    rr = aws_cli.run(cmd)
    e_tag = rr['ETag']

    cmd = ['cloudfront', 'delete-distribution']
    cmd += ['--id', id]
    cmd += ['--if-match', e_tag]
    rr = aws_cli.run(cmd)


def disable_cloudfront(id):
    aws_cli = AWSCli()
    cmd = ['cloudfront', 'get-distribution']
    cmd += ['--id', id]
    rr = aws_cli.run(cmd)
    e_tag = rr['ETag']

    if not rr['Distribution']['DistributionConfig']['Enabled']:
        return

    aws_cli = AWSCli()
    cmd = ['cloudfront', 'update-distribution']
    cmd += ['--id', id]
    cmd += ['--if-match', e_tag]
    dd = dict()
    dd['PriceClass'] = 'PriceClass_200'
    dd['CallerReference'] = domain_name
    dd['Origins'] = rr['Distribution']['DistributionConfig']['Origins']
    dd['DefaultCacheBehavior'] = rr['Distribution']['DistributionConfig']['DefaultCacheBehavior']
    dd['DefaultRootObject'] = rr['Distribution']['DistributionConfig']['DefaultRootObject']
    dd['Comment'] = rr['Distribution']['DistributionConfig']['Comment']
    dd['Aliases'] = rr['Distribution']['DistributionConfig']['Aliases']
    dd['Enabled'] = False
    rr['Distribution']['DistributionConfig']['Enabled'] = False
    cmd += ['--distribution-config', json.dumps(rr['Distribution']['DistributionConfig'])]
    aws_cli.run(cmd)


def wait_cloudfront_status(id, status):
    aws_cli = AWSCli()
    elapsed_time = 0
    is_not_terminate = True

    while is_not_terminate:
        cmd = ['cloudfront', 'get-distribution']
        cmd += ['--id', id]
        rr = aws_cli.run(cmd)

        ss = rr['Distribution']['Status']
        if status == ss:
            is_not_terminate = False

        if elapsed_time > 1200:
            raise Exception('timeout: stop cloudfront(%s)' % id)

        sleep(5)
        print('wait cloudfront status(%s), but now %s (elapsed time: \'%d\' seconds)' % (status, ss, elapsed_time))
        elapsed_time += 5


################################################################################
#
# start
#
################################################################################


if __name__ == "__main__":
    args = parse_args()
    domain_name = args.cname

    cc = re.split('[-.]', domain_name)
    if 'dv' not in cc:
        print('only can delete dv')
        exit(1)

    cc = find_cloudfront(domain_name)
    id = cc['Id']

    disable_cloudfront(id)
    wait_cloudfront_status(id, 'Deployed')
    delete_cloudfront(id)
