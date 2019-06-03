#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_session

aws_cli = AWSCli('us-east-1')
ses = env['ses']


def terminate_config_set():
    for cs in ses['CONFIGURATION_SETS']:
        name = cs['NAME']
        cmd = ['ses', 'delete-configuration-set',
               '--configuration-set-name', name]
        aws_cli.run(cmd, ignore_error=True)


def terminate_email_identity():
    for ii in ses['IDENTITIES']:
        email = ii['EMAIL']
        cmd = ['ses', 'delete-identity',
               '--identity', email]
        aws_cli.run(cmd, ignore_error=True)


def terminate_domain_identity():
    for ii in ses['DOMAIN_IDENTITIES']:
        cmd = ['ses', 'delete-identity',
               '--identity', ii['DOMAIN']]
        aws_cli.run(cmd, ignore_error=True)


def terminate_receipt_rule_set():
    cmd = ['ses', 'set-active-receipt-rule-set']
    aws_cli.run(cmd)

    for ii in ses['DOMAIN_IDENTITIES']:
        cmd = ['ses', 'delete-receipt-rule-set',
               '--rule-set-name', ii['RULE_SET_NAME']]
        aws_cli.run(cmd, ignore_error=True)
        for rr in ii['RULES']:
            cmd = ['s3', 'rm', 's3://%s/%s' % (rr['BUCKET_NAME'], env['common']['PHASE']), '--recursive']
        aws_cli.run(cmd, ignore_error=True)


args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('terminate ses')

################################################################################
terminate_config_set()
terminate_email_identity()
terminate_domain_identity()
terminate_receipt_rule_set()
