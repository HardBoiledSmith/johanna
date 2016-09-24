How To Play

0. pip install --user -r requirements.txt
1. cp env.py.sample env.py
2. edit env.py with your own configuration.
(example)
	env['aws']['AWS_ACCESS_KEY_ID'] = 'MY_ACCESS_KEY'
	env['aws']['AWS_SECRET_ACCESS_KEY'] = 'MY_SECRET_ACCESS_KEY'
	env['common']['HOST_NOVA'] = 'this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
	env['common']['URL_NOVA'] = 'http://this-is-my-dv-nova.ap-northeast-2.elasticbeanstalk.com'
    env['nova']['CNAME'] = 'this-is-my-dv-nova'
3. ./run.py
