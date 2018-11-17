#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli('us-east-1')
ses = env['ses']


def create_email_identity():
    cmd = ['ses', 'list-identities']
    identities_results = dict(aws_cli.run(cmd))

    for identity in ses['IDENTITIES']:
        if identity['EMAIL'] not in identities_results['Identities']:
            cmd = ['ses', 'verify-email-identity',
                   '--email-address', identity['EMAIL']]
            aws_cli.run(cmd)

            sns_topic_name = identity['SNS_TOPICS_NAME']
            print_message('check topic exists: %s' % sns_topic_name)
            region, topic_name = sns_topic_name.split('/')
            topic_arn = AWSCli(region).get_topic_arn(topic_name)
            if not topic_arn:
                print('sns topic: "%s" is not exists in %s' % (sns_topic_name, region))
                raise Exception()

            cmd = ['ses', 'set-identity-notification-topic',
                   '--identity', identity['EMAIL'],
                   '--notification-type', 'Bounce',
                   '--sns-topic', topic_arn
                   ]
            aws_cli.run(cmd)

            cmd = ['ses', 'set-identity-headers-in-notifications-enabled',
                   '--identity', identity['EMAIL'],
                   '--notification-type', 'Bounce',
                   '--enabled'
                   ]
            aws_cli.run(cmd)

            cmd = ['ses', 'set-identity-notification-topic',
                   '--identity', identity['EMAIL'],
                   '--notification-type', 'Complaint',
                   '--sns-topic', topic_arn
                   ]
            aws_cli.run(cmd)

            cmd = ['ses', 'set-identity-headers-in-notifications-enabled',
                   '--identity', identity['EMAIL'],
                   '--notification-type', 'Complaint',
                   '--enabled'
                   ]
            aws_cli.run(cmd)


def create_config_set():
    cmd = ['ses', 'list-configuration-sets']
    exist_config_sets = aws_cli.run(cmd)['ConfigurationSets']

    exist_config_names = [exist_config_set['Name'] for exist_config_set in exist_config_sets]
    for config_set in ses['CONFIGURATION_SETS']:
        config = {
            "NAME": config_set['NAME'],
            "EVENT_DESTINATIONS": [{
                "Name": config_set['EVENT_DESTINATIONS_NAME'],
                "Enabled": config_set['EVENT_DESTINATIONS_Enabled'],
                "MatchingEventTypes": config_set['MATCHING_TYPE'],
                "CloudWatchDestination": {
                    "DimensionConfigurations": [
                        {
                            "DimensionName": config_set['DIMENSION_CONFIG_NAME'],
                            "DimensionValueSource": config_set['DIMENSION_CONFIG_VALUE_SOURCE'],
                            "DefaultDimensionValue": config_set['DIMENSION_CONFIG_VALUE']
                        }
                    ]
                }
            }]
        }

        if config_set['NAME'] not in exist_config_names:
            cmd = ['ses', 'create-configuration-set',
                   '--configuration-set', 'Name=%s' % config['NAME']]
            aws_cli.run(cmd)
            for event_destination in config['EVENT_DESTINATIONS']:
                cmd = ['ses', 'create-configuration-set-event-destination',
                       '--configuration-set-name', config_set['NAME'],
                       '--event-destination', json.dumps(event_destination)
                       ]
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
print_session('create ses')

################################################################################
check_template_availability()

create_email_identity()
create_config_set()
