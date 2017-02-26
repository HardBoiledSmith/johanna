#!/usr/bin/env python3
import argparse
import json
import sys

parser = argparse.ArgumentParser(description='Johanna configuration script')
parser.add_argument('--accesskey', help='AWS Access Key ID')
parser.add_argument('--secretkey', help='AWS Secret Access Key')
parser.add_argument('--region', help='Choose AWS Region')
parser.add_argument('--az1', help='AWS Availability Zone 1')
parser.add_argument('--az2', help='AWS Availability Zone 2')
parser.add_argument('--template', help='git URL of provisioning template repository')
parser.add_argument('--db', help='AWS RDS Engine')
parser.add_argument('--user', help='RDS User Name')
parser.add_argument('--pw', help='RDS User Password')

if __name__ == '__main__':
    args = parser.parse_args()

    required_args = [
        args.accesskey,
        args.secretkey,
        args.region,
        args.az1,
        args.az2,
        args.db,
        args.user,
        args.pw
    ]

    for arg in required_args:
        if not arg:
            parser.print_help()
            sys.exit(0)

    config = json.loads(open('config.json.sample').read())

    # AWS ACCESS KEY ID
    config['aws']['AWS_ACCESS_KEY_ID'] = args.accesskey

    # AWS SECRET ACCESS KEY
    config['aws']['AWS_SECRET_ACCESS_KEY'] = args.secretkey

    # AWS REGION
    AWS_REGIONS = ['us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southest-1', 'ap-southest-2',
                   'ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'sa-east-1']
    if args.region not in AWS_REGIONS:
        print('Invalid Region Name')
        sys.exit(0)
    config['aws']['AWS_DEFAULT_REGION'] = args.region

    # AWS AVAILABILITY ZONE 1
    if args.region not in args.az1:
        print('Invalid AWS_AVAILABILITY_ZONE_1')
        sys.exit(0)
    config['aws']['AWS_AVAILABILITY_ZONE_1'] = args.az1

    # AWS AVAILABILITY ZONE 2
    if args.region not in args.az2:
        print('Invalid AWS_AVAILABILITY_ZONE_2')
        sys.exit(0)
    config['aws']['AWS_AVAILABILITY_ZONE_2'] = args.az2

    # AWS TEMPLATE
    if args.template:
        config['template']['GIT_URL'] = args.template
        config['elasticbeanstalk']['ENVIRONMENTS'] = []
    else:
        nova = config['elasticbeanstalk']['ENVIRONMENTS'][0]
        nova_cname = nova['CNAME']
        nova['HOST'] = '%s.%s.elasticbeanstalk.com' % (nova_cname, args.region)
        nova['URL'] = 'http://%s.%s.elasticbeanstalk.com' % (nova_cname, args.region)

    # RDS Engine
    AWS_RDS_ENGINES = ['mysql', 'mariadb', 'oracle-se1', 'oracle-se2', 'oracle-se', 'oracle-ee', 'sqlserver-ee',
                       'sqlserver-se', 'sqlserver-ex', 'sqlserver-web', 'postgres', 'aurora']
    if args.db not in AWS_RDS_ENGINES:
        print('Invalid AWS RDS ENGINE')
        sys.exit(0)
    config['rds']['ENGINE'] = args.db

    # RDS User Configuration
    config['rds']['USER_NAME'] = args.user
    config['rds']['USER_PASSWORD'] = args.pw

    config_file = open('config.json', 'w+')
    config_file.write(json.dumps(config, sort_keys=True, indent=4))
    config_file.close()
