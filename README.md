[![Build Status](https://travis-ci.org/HardBoiledSmith/johanna.svg?branch=master)](https://travis-ci.org/HardBoiledSmith/johanna)
# Introduction

Johanna is a collection of boilerplate Python scripts that can do provisioning/deprovisioning of a simple backend system using AWS.

The backend includes below:
- VPC with two public subnets, two private subnets, routing tables, an internet gateway, a nat gateway and an EIP.
- IAM roles for Elastic Beanstalk
- EC2 key pair (SSH key)
- An Elastic Beanstalk application and an environment for Python Django API server

You can do provisioning/deprovisioning/reprovisioning of the whole system or partial at once. Especially, the reprovisioning of Django API server means a '[continuous deployement](https://en.wikipedia.org/wiki/Continuous_delivery#Relationship_to_continuous_deployment)'.

# How To Play

Using [Lili](https://github.com/addnull/lili)(Vagrant provisioning script) is the simplest way to get a playground.

1. follow Lili [README manual](https://github.com/addnull/lili/blob/master/README.md)
1. on Vagrant VM(Ubuntu 16.04)
	1. `sudo su`
	1. `cd /opt/johanna`
	1. execute 'conf.py' to configure your aws environment.

		```
		./conf.py --accesskey YOUR_AWS_ACCESSKEY --secretkey YOUR_AWS_SECRETKEY --region AWS_REGION_NAME --az1 AVAILABILITY_ZONE_1 --az2 AVAILABILITY_ZONE_2 --cname CNAME --db DB_ENGINE --user DB_USER --pw DB_PASSWORD
		```
		
		*[Example]*
		```
		./conf.py --accesskey ... --secretkey ... --region ap-northeast-2 --az1 ap-northeast-2a --az2 ap-northeast-2c --cname dv-nova --db mysql --user db-user --pw db-password
		```

	1. `./run.py`

-

You can use this on web GUI

* [raynor](https://github.com/addnull/raynor) is web based GUI for johanna

# Notes

* If you use AWS IAM user credential instead of master account, it must have IAMFullAccess, AWSElasticBeanstalkFullAccess and PowerUserAccess permissions.
![alt text](https://github.com/addnull/johanna/raw/master/docs/images/iam_user_permissions.png "IAM user permissions")

# Links

* [PyCon APAC 2016](https://www.pycon.kr/2016apac/program/15)
* [Slideshare](http://www.slideshare.net/addnull/daily-continuous-deployment-custom-cli-aws-elastic-beanstalk-64946800)
