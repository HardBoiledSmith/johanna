# Johanna

[![Build Status](https://codebuild.ap-northeast-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZ1BqQzAxWTF6ZEV3TmJyWWtVQ1lpOEpYTkFxMEh5amNRd3U3bnp2anpiQXhtQm8wSTJLZFYxRndSYVhJc0VCRFdKNG1mMWtaUFpqWlB1d1JEdHlUU1hvPSIsIml2UGFyYW1ldGVyU3BlYyI6InArbTJQTHh6Y08yalMwZmMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)](https://ap-northeast-2.console.aws.amazon.com/codesuite/codebuild/projects/build_test_johanna/history)

Johanna is a collection of boilerplate Python scripts that can do provisioning/deprovisioning of a simple backend system
using AWS.

The backend includes below:

- VPC with two public subnets, two private subnets, routing tables, an internet gateway, a nat gateway and an EIP.
- IAM roles for Elastic Beanstalk
- EC2 key pair (SSH key)
- An Elastic Beanstalk application and an environment for Python Django API server
- An aurora RDS cluster with instances
- An sample SQS
- and more...

You can do provisioning/deprovisioning/reprovisioning of the whole system or partial at once. Especially, the
reprovisioning of Django API server means
a '[continuous deployement](https://en.wikipedia.org/wiki/Continuous_delivery#Relationship_to_continuous_deployment)'.

## Requirements

```
- Vagrant 2.2.13+

[For using hbsmith/awslinux2 box] 
- Parallels Desktop 16+ for Mac 
- vagrant-parallels plugin 2.0.1+
```

# How To Play

Using [Lili](https://github.com/HardBoiledSmith/lili)(Vagrant provisioning script) is the simplest way to get a
playground.

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

# CLI Options

```
./run_create_eb.py [OPTIONS] <eb-environment-name>		(ex: './run_create_eb.py sachiel')
./run_terminate_eb.py [OPTIONS] <eb-environment-name>	        (ex: './run_terminate_eb.py sachiel')
./run_create_lambda.py [OPTIONS] <lambda-function-name>		(ex: './run_create_eb.py sachiel_send_email')
./run_terminate_lambda.py [OPTIONS] <lambda-function-name>	(ex: './run_terminate_lambda.py sachiel_send_email')
./run_create_s3.py [OPTIONS] <s3-bucket-name>		        (ex: './run_create_eb.py dv-hbsmith-web')
./run_terminate_s3.py [OPTIONS] <s3-bucket-name>		(ex: './run_terminate_s3.py dv-hbsmith-web')
./run.py [OPTIONS] -- [AWS CLI COMMAND]		                (ex: './run.py -- aws ec2 describe-instances')
```

- `--force` or `-f`
	Attempt to execute the commend without prompting for phase confirmation.
- `--branch` or `-b`
	Attempt to execute the command with specific git branch.
- `--region` or `-r`
	Attempt to execute the command on specific region.

# Script to create cloudfront and route 53

- Execute `run_create_cloudfront.py` to create cloud front

```bash
./run_create_cloudfront.py -b <s3 bucket name> -e <s3 bucket end point> -a <acm-arn> -c <cname> -f
```

- Execute `run_create_cloudfront.py` to create route53
- reference
  HOSTED_ZONE_ID : https://docs.aws.amazon.com/Route53/latest/APIReference/API_AliasTarget.html#Route53-Type-AliasTarget-HostedZoneIdx

```bash
./run_create_route53.py -ah Z2FDTNDATAQYW2 -at cloudfront -d <cloudfront domain name> -hn hbsmith.io -n <domain> -r A -f
```

# Notes

* If you use AWS IAM user credential instead of master account, it must have IAMFullAccess,
  AWSElasticBeanstalkFullAccess and PowerUserAccess permissions.

  ![alt text](https://github.com/HardBoiledSmith/johanna/raw/master/docs/images/iam_user_permissions.png "IAM user permissions")

# Vagrant

- set config.json below root of johanna
- move to provisioning folder using `johanna $ cd _provisioning`
- copy `id_rsa` : `cp ~/.ssh/id_rsa ./_provisioning/configuration/root/.ssh/`
- (optional) To use release feature for sentry, must set environment value: `SENTRY_AUTH_TOKEN` and `SENTRY_ORG`
    - https://docs.sentry.io/product/releases/suspect-commits/#using-the-cli
- create or run vagrant using `johanna/_provisioning $ vagrant up`
- (optional) Run `BRANCH=<branch name> vagrant up` for provisioning with specific git branch.
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

## Troubleshooting - ACM quotas

> "You have reached the maximum number of certificates. Delete certificates that are not in use, or contact AWS Support to request an increase."

By default, you can import up to 1000 certificates into ACM, but new AWS accounts might start with a lower limit. If you
exceed this limit, request an ACM quota increase with these. You can solve this issue
by [opening support case](https://docs.aws.amazon.com/acm/latest/userguide/acm-limits.html).

- AWS Certificate Manager (ACM) > Imported certificates in last 365 days
- AWS Certificate Manager (ACM) > ACM certificates created in last 365 days

## How to set up fake email test environment

1. Provision AWS VPC, RDS, Client VPN, Elastic Beanstalk, SQS, AWS SES, SNS, S3 into your account
1. Create vagrant gendo, johanna.
1. SSH into vagrant johanna
1. Go to `cd /opt/johanna`
1. run that command `./run.py create_vpc`
1. run that command `./run.py create_rds`
1. run that command `./run_create_ec2_client_vpn.py` connect to the self_service address shown in the last line to download the ovpn file.
1. Reset the database data in the created aws rds
1. run that command `./run_create_eb.py sachiel`
1. run that command `./run.py create_sqs`
1. run that command `./run_create_s3.py <your dev env name>-dv-hbsmith-email-receive`
1. run that command `./run_create_s3.py test`
1. run that command `./run.py create_sns`
1. run that command `./run.py create_ses`
1. Go to the company email and click the link to agree to the verify email received from AWS SNS and SES.
1. run that command `./run_create_lambda.py sachiel_fake_email_save`
1. run that command `./run_create_lambda.py sachiel_fake_email_delete`
1. run that command `./run_create_lambda.py gendo_test_fake_mail`
1. Connect to AWS console and run lambda service gendo_test_fake_mail (Seoul Region)
1. Go to the naoko project and set the http://dv-sachiel.hbsmith.io value in the code at https://github.com/HardBoiledSmith/naoko/blob/4e1c7aedbb8856bf804910a9ddae573310681097/naoko/Utility/SettingsManager.cs#L43 to https:// Change to {your dev env name}-dv-sachiel.hbsmith.io"; and build.
1. run the naoko program. set the URL to <your dev env name>-dv-test.hbsmith.io and start recording.
1. test page through the received email tab.
1. Enter test_gendo@hbsmith-email.io in the Email field.
1. Follow the contents of the test page to the address `test_gendo@hbsmith-email.io`

# Links

* [PyCon APAC 2016](https://www.pycon.kr/2016apac/program/15)
* [Slideshare](http://www.slideshare.net/addnull/daily-continuous-deployment-custom-cli-aws-elastic-beanstalk-64946800)
