#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import json

AWS_REGIONS = ['us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southest-1', 'ap-southest-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'sa-east-1']

config_list = glob.glob('config-*.json')

# Check config file name is valid
for config in config_list:
    region = config[7 : len(config) - 5]
    if region not in AWS_REGIONS:
        import sys
        print('Invalid Region Name :', config)
        sys.exit(-1)

env_list = list()

# Load config json to env
for config in config_list:
    env_list.append(json.loads(open(config).read()))

# TODO: Enable to use env_list
env = env_list[0]
