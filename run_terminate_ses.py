#!/usr/bin/env python3
from env import env
from run_common import check_template_availability
from run_common import print_session
from run_common import AWSCli

aws_cli = AWSCli('us-east-1')
ses = env['ses']


def terminate_config_set():
    cmd = ['ses', 'list-configuration-sets']
    exist_config_sets = aws_cli.run(cmd)['ConfigurationSets']

    exist_config_names = [exist_config_set['Name'] for exist_config_set in exist_config_sets]
    for config_set in ses['CONFIGURATION_SETS']:
        if config_set['NAME'] in exist_config_names:
            cmd = ['ses', 'delete-configuration-set',
                   '--configuration-set-name', config_set['NAME']]
            aws_cli.run(cmd)


def terminate_email_identity():
    cmd = ['ses', 'list-identities']
    identities_results = dict(aws_cli.run(cmd))

    for email in ses['EMAILS']:
        if email in identities_results['Identities']:
            cmd = ['ses', 'delete-identity',
                   '--identity', email]
            aws_cli.run(cmd)


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
check_template_availability()

terminate_config_set()
terminate_email_identity()
