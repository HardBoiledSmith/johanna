# johanna
> johanna make you convenient to manage (create, terminate, update) the complex backend systems on AWS 

<br>

## How To Play

1. `pip install --user -r requirements.txt`
2. `cp env.py.sample env.py`
3. Edit 'env.py' with your own configurations.

	example :
	```python
	env['aws']['AWS_ACCESS_KEY_ID'] = 'MY_ACCESS_KEY'
	env['aws']['AWS_SECRET_ACCESS_KEY'] = 'MY_SECRET_ACCESS_KEY'
	env['common']['HOST_NOVA'] = 'this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
	env['common']['URL_NOVA'] = 'http://this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
    env['nova']['CNAME'] = 'this-is-my-dv-nova'
	```
4. `./run.py`

	> You can view the command list when executing this command
