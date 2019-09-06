#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli('us-east-1')
ses = env['ses']


def create_email_identity():
    cmd = ['ses', 'list-identities']
    identities_results = dict(aws_cli.run(cmd))

    for identity in ses['IDENTITIES']:
        if identity['EMAIL'] in identities_results['Identities']:
            continue

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
               '--sns-topic', topic_arn]
        aws_cli.run(cmd)

        cmd = ['ses', 'set-identity-headers-in-notifications-enabled',
               '--identity', identity['EMAIL'],
               '--notification-type', 'Bounce',
               '--enabled']
        aws_cli.run(cmd)

        cmd = ['ses', 'set-identity-notification-topic',
               '--identity', identity['EMAIL'],
               '--notification-type', 'Complaint',
               '--sns-topic', topic_arn]
        aws_cli.run(cmd)

        cmd = ['ses', 'set-identity-headers-in-notifications-enabled',
               '--identity', identity['EMAIL'],
               '--notification-type', 'Complaint',
               '--enabled']
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


def verify_ses_domain():
    for ii in ses['DOMAIN_IDENTITIES']:
        cmd = ['ses', 'get-identity-mail-from-domain-attributes',
               '--identities', ii['DOMAIN']]
        rr = dict(aws_cli.run(cmd))
        if rr['MailFromDomainAttributes']:
            continue

        cmd = ['ses', 'verify-domain-identity',
               '--domain', ii['DOMAIN']]
        aws_cli.run(cmd)


def create_rule_set():
    for ii in ses['DOMAIN_IDENTITIES']:
        cmd = ['ses', 'describe-receipt-rule-set',
               '--rule-set-name', ii['RULE_SET_NAME']]
        rr = aws_cli.run(cmd, ignore_error=True)
        if rr:
            continue

        cmd = ['ses', 'create-receipt-rule-set',
               '--rule-set-name', ii['RULE_SET_NAME']]
        aws_cli.run(cmd)

        cmd = ['ses', 'set-active-receipt-rule-set',
               '--rule-set-name', ii['RULE_SET_NAME']]
        aws_cli.run(cmd)

        for rule in ii['RULES']:
            cmd = ['sns', 'list-topics']
            rr = dict(aws_cli.run(cmd))
            sns_topic = __find_sns_topic(rr, rule)
            bucket_name = __find_s3_bucket(rule)

            rule_action = {
                'Name': rule['NAME'],
                'Enabled': True,
                'Actions': [{
                    'S3Action': {
                        'BucketName': bucket_name,
                        'ObjectKeyPrefix': env['common']['PHASE'],
                        'TopicArn': sns_topic
                    }
                }]
            }

            cmd = ['ses', 'create-receipt-rule',
                   '--rule-set-name', ii['RULE_SET_NAME'],
                   '--rule', json.dumps(rule_action)]
            aws_cli.run(cmd)


def __find_s3_bucket(rule):
    bucket_name = None
    cmd = ['s3api', 'list-buckets']
    rr = dict(aws_cli.run(cmd))
    for bb in rr['Buckets']:
        if rule['BUCKET_NAME'] == bb['Name']:
            bucket_name = rule['BUCKET_NAME']
            break
    if not bucket_name:
        cmd = ['s3api', 'create-bucket',
               '--bucket', rule['BUCKET_NAME']]
        bucket_name = rule['BUCKET_NAME']
        aws_cli.run(cmd)

        s3_policy = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ses.amazonaws.com"
                    },
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::%s/*" % bucket_name
                }
            ]
        }
        cmd = ['s3api', 'put-bucket-policy',
               '--bucket', bucket_name,
               '--policy', json.dumps(s3_policy)]
        aws_cli.run(cmd)

        s3_lifecycle_rule = {
            "Rules": [
                {
                    "ID": "%s-lifecycle" % bucket_name,
                    "Prefix": env['common']['PHASE'],
                    "Status": "Enabled",
                    "Expiration": {
                        "Days": rule['BUCKET_LIFECYCLE_EXPIRATION']
                    }
                }
            ]
        }
        cmd = ['s3api', 'put-bucket-lifecycle-configuration',
               '--bucket', bucket_name,
               '--lifecycle-configuration', json.dumps(s3_lifecycle_rule)]
        aws_cli.run(cmd)

    return bucket_name


def __find_sns_topic(rr, rule):
    sns_topic = None
    for tt in rr['Topics']:
        if rule['SNS_NAME'] in tt['TopicArn']:
            sns_topic = tt['TopicArn']
            break
    return sns_topic


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

create_email_identity()
create_config_set()
verify_ses_domain()
create_rule_set()
