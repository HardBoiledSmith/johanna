#!/usr/bin/env python3
import json
import argparse
import sys

parser = argparse.ArgumentParser(description='Johanna configuration script')
parser.add_argument('--accesskey', help='AWS Access Key ID')
parser.add_argument('--secretkey', help='AWS Secret Access Key')
parser.add_argument('--region', help='Choose AWS Region')
parser.add_argument('--az1', help='AWS Availability Zone 1')
parser.add_argument('--az2', help='AWS Availablitiy Zone 2')
parser.add_argument('--cname', help='Your Application CNAME')


if __name__ == '__main__':
    args = parser.parse_args()
    
    if not (args.accesskey and args.secretkey and args.region and args.az1 and args.az2 and args.cname):
        parser.print_help()
        sys.exit(0)
    
    config = json.loads(open('config.json').read())

    # AWS ACCESS KEY ID
    config['aws']['AWS_ACCESS_KEY_ID'] = args.accesskey
    
    # AWS SECRET ACCESS KEY
    config['aws']['AWS_SECRET_ACCESS_KEY'] = args.secretkey
    
    # AWS REGION
    AWS_REGIONS = ['us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southest-1', 'ap-southest-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'sa-east-1']
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
    
    # CNAME
    config['nova']['CNAME'] = args.cname
    config['common']['HOST_NOVA'] = args.cname + '.' + args.region + '.elasticbeanstalk.com'
    config['common']['URL_NOVA'] = 'http://' + args.cname + '.' + args.region + '.elasticbeanstalk.com'
    
    config_file = open('config.json', 'w+')
    config_file.write(json.dumps(config, sort_keys=True, indent=4))
    config_file.close()
