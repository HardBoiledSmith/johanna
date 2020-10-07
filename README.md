[![Build Status](https://codebuild.ap-northeast-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiQWJKb1lUc0tkNnlEVWZPMldDa3FoQncrOEdKS2M1emM2eG9pNmR4UW9aWVJmZXl3c0xUVU4wR2tmVDcySHpSRm1hTHBNSTE0V0RUU1lYV29YdmpVMS9nPSIsIml2UGFyYW1ldGVyU3BlYyI6IjI3TU5qY0hZRGFTL29EbEMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)](https://ap-northeast-2.console.aws.amazon.com/codesuite/codebuild/projects/build_test_johanna/history)

# Introduction

Johanna is a collection of boilerplate Python scripts that can do provisioning/deprovisioning of a simple backend system using AWS.

The backend includes below:
- VPC with two public subnets, two private subnets, routing tables, an internet gateway, a nat gateway and an EIP.
- IAM roles for Elastic Beanstalk
- EC2 key pair (SSH key)
- An Elastic Beanstalk application and an environment for Python Django API server
- An aurora RDS cluster with instances
- An sample SQS
- An sample apply SRR(Same Region Replication) to S3  

You can do provisioning/deprovisioning/reprovisioning of the whole system or partial at once. Especially, the reprovisioning of Django API server means a '[continuous deployement](https://en.wikipedia.org/wiki/Continuous_delivery#Relationship_to_continuous_deployment)'.

# How To Play

Using [Lili](https://github.com/HardBoiledSmith/lili)(Vagrant provisioning script) is the simplest way to get a playground.

- Follow Lili [README manual](https://github.com/addnull/lili/blob/master/README.md)
- On Vagrant VM (Ubuntu 16.04)
  1. `sudo su`

  2. `cd /opt/johanna`

  3. Execute `conf.py` to configure your aws environment.

     ```bash
     ./conf.py --email YOUR_EMAIL --keypairname YOUR_AWS_KEYPAIR_NAME --accesskey YOUR_AWS_ACCESSKEY --secretkey YOUR_AWS_SECRETKEY --region AWS_REGION_NAME --az1 AVAILABILITY_ZONE_1 --az2 AVAILABILITY_ZONE_2 --template TEMPLATE_GIT_URL --user DB_USER --pw DB_PASSWORD
     ```

     *[Example]*

     ```bash
     ./conf.py --email ... --keypairname ... --accesskey ... --secretkey ... --region ap-northeast-2 --az1 ap-northeast-2a --az2 ap-northeast-2c --template git@github.com:HardBoiledSmith/kerrigan.git --user db-user --pw db-password
     ```

  4. `./run.py`

You can use this on web GUI

* [raynor](https://github.com/HardBoiledSmith/raynor) is web based GUI for johanna

# Script to create cloudfront and route 53
- Execute `run_create_cloudfront.py` to create cloud front
```bash
./run_create_cloudfront.py -b <s3 bucket name> -e <s3 bucket end point> -a <acm-arn> -c <cname> -f
```
- Execute `run_create_cloudfront.py` to create route53
- reference HOSTED_ZONE_ID : https://docs.aws.amazon.com/Route53/latest/APIReference/API_AliasTarget.html#Route53-Type-AliasTarget-HostedZoneIdx
```bash
./run_create_route53.py -ah Z2FDTNDATAQYW2 -at cloudfront -d <cloudfront domain name> -hn hbsmith.io -n <domain> -r A -f
```

# Notes

* If you use AWS IAM user credential instead of master account, it must have IAMFullAccess, AWSElasticBeanstalkFullAccess and PowerUserAccess permissions.

	![alt text](https://github.com/HardBoiledSmith/johanna/raw/master/docs/images/iam_user_permissions.png "IAM user permissions")

# Vagrant

- set config.json below root of johanna
- move to provisioning folder using `johanna $ cd _provisioning`
- create or run vagrant using `johanna/_provisioning $ vagrant up`
- connect to vagrant using `$ ssh root@dv-johanna.hbsmith.io` or `$ ssh root@192.168.124.5` 
- move to johanna folder using  `$ cd /opt/johanna`
- run provisioning script using `/opt/johanna $ ./run.py`

# How to run Lint check (PEP8)

1. Provisioning vagrant
1. Connect `http://dv-johanna.hbsmith.io/`
1. Go to `cd /opt/johanna`
1. Run `flake8 --config=flake8 .`

# Command Completion

You can use [AWS CLI Command Completion](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-completion.html)

# AWS Codebuild

Before create codebuild projects, you must create these resources manually using AWS Web console:

- Environment Variables (Secure String) at Systems Manager > Parameter Store

  https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-securestring.html

- OAuth Connection to GitHub by follow instructions

  > For source code in a GitHub repository, the HTTPS clone URL to the repository that contains the source and the buildspec file. You must connect your AWS account to your GitHub account. Use the AWS CodeBuild console to start creating a build project. When you use the console to connect (or reconnect) with GitHub, on the GitHub Authorize application page, for Organization access , choose Request access next to each repository you want to allow AWS CodeBuild to have access to, and then choose Authorize application . (After you have connected to your GitHub account, you do not need to finish creating the build project. You can leave the AWS CodeBuild console.)    
  > https://docs.aws.amazon.com/cli/latest/reference/codebuild/create-project.html#options

# AWS Client VPN

You can create client configuration (.ovpn) for AWS Client VPN

1. Provision VPC, AWS SES into your account
1. Provision Client VPN Endpoint into the VPC
1. SSH into vagrant johanna
1. Go to `cd /opt/johanna`
1. Run `./run_export_client_vpn_ovpn.py <client vpn name> <region> <email to> <zip password>`
1. Check email inbox of `<email to>`

# S3 SRR(Same Region Replication)

This script applies replication to different AWS accounts.

At least two buckets are required to apply this policy. 
1. You need a source bucket and replication bucket.
2. Create two buckets and activate the versioning function on each bucket.
3. Please run the following a scripts.
    - run_create_s3_srr.py \
    ```./run_terminate_s3_srr.py -oa <origin bucket account id> -o <origin bucket name> -ra <replication bucket account id> -r <replication bucket name> -a `<replication bucket owner access key>` -s `<replication bucket owner secret access key> -p <write down the policy name you want> -n <write down the role name you want> ```

        sample code \
        ./run_create_s3_srr.py -oa `123456789000` -o `dv-srr-test` -ra `009883222211` -r `qa-srr-test` -a `XXXXXXXXXXXXXX` -s `11XXX12XXXXXXXX` -p `srr-policy` -n `srr-role`

4. If this feature is applied, uploading the file to the original bucket will also indicate that the file will be uploaded to the replication bucket.


Run the script below if you want to remove the replication function below.

   - run_terminate_s3_srr.py \
    ```./run_terminate_s3_srr.py -oa <origin bucket account id> -o <origin bucket name> -r <replication bucket name> -a <replication bucket owner access key> -s <replication bucket owner secret access key> -p <policy name applied to store replication> -n <role name applied to store replication>```

   - sample code \
    ./run_terminate_s3_srr.py -oa `123456789000` -o `dv-srr-test` -r `qa-srr-test` -a `XXXXXXXXXXXXXX` -s `11XXX12XXXXXXXX` -p `srr-policy` -n `srr-role`

# Links

* [PyCon APAC 2016](https://www.pycon.kr/2016apac/program/15)
* [Slideshare](http://www.slideshare.net/addnull/daily-continuous-deployment-custom-cli-aws-elastic-beanstalk-64946800)
