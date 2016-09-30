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
	1. edit 'env.py' with your own configuration.

		```python
		env['aws']['AWS_ACCESS_KEY_ID'] = 'MY_ACCESS_KEY'
		env['aws']['AWS_SECRET_ACCESS_KEY'] = 'MY_SECRET_ACCESS_KEY'
		env['common']['HOST_NOVA'] = 'this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
		env['common']['URL_NOVA'] = 'http://this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
		env['nova']['CNAME'] = 'this-is-my-dv-nova'
		```

	1. `./run.py`

# Notes

* If you use AWS IAM user credential instead of master account, it must have IAMFullAccess, AWSElasticBeanstalkFullAccess and PowerUserAccess permissions.
![alt text](https://github.com/addnull/johanna/raw/master/docs/images/iam_user_permissions.png "IAM user permissions")

# Links

* [PyCon APAC 2016](https://www.pycon.kr/2016apac/program/15)
* [Slideshare](http://www.slideshare.net/addnull/daily-continuous-deployment-custom-cli-aws-elastic-beanstalk-64946800)
