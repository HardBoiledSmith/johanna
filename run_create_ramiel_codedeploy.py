#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_session
from run_common import print_message
from run_common import reset_template_dir

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

print_session('create codedeploy')

reset_template_dir(options)

settings = env.get('codedeploy', dict())
region = settings['AWS_REGION']

aws_cli = AWSCli(region)

print_message('create a user for codedeploy')

iam_user_name = 'ramiel_codedeploy_iam_session_user'
cc = ['iam', 'create-user']
cc += ['--user-name', iam_user_name]
aws_cli.run(cc)

iam_policy_name = 'ramiel_codedeploy_iam_session_permission'
cc = ['iam', 'create-policy']
cc += ['--policy-name', iam_policy_name]
cc += ['--policy-document', 'file://aws_iam/aws-codedeploy-ramiel-permission.json']
rr = result = aws_cli.run(cc)
policy_arn = rr['Policy']['Arn']

iam_role_name = 'ramiel_codedeploy_iam_session_role'
cc = ['iam', 'attach-user-policy']
cc += ['--user-name', iam_user_name]
cc += ['--policy-arn', policy_arn]
aws_cli.run(cc)

print_message('create a role for codedeploy')

cc = ['iam', 'create-role']
cc += ['--role-name', iam_role_name]
cc += ['--assume-role-policy-document', 'file://aws_iam/aws-codedeploy-ramiel-role.json']
rr = aws_cli.run(cc)

cc = ['iam', 'attach-role-policy']
cc += ['--role-name', iam_role_name]
cc += ['--policy-arn', policy_arn]
aws_cli.run(cc)

print_message('create codedeploy resources: applications and deployment groups')

for app in settings['APPLICATIONS']:
    app_name = app['NAME']
    cc = ['deploy', 'create-application']
    cc += ['--application-name', app_name]
    aws_cli.run(cc)

    for dep_group in app['DEPLOYMENT_GROUPS']:
        dep_name = dep_group['NAME']
        on_premises_tag_set = dep_group['ON_PREMISES_TAG_SET']

        cc = ['deploy', 'create-deployment-group']
        cc += ['--application-name', app_name]
        cc += ['--deployment-group-name', dep_name]
        cc += ['--service-role-arn', 'arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole']
        if on_premises_tag_set:
            cc += ['--on-premises-tag-set', on_premises_tag_set]
        aws_cli.run(cc)

print_message(f'create access key for codedeploy user {iam_user_name}')

cc = ['iam', 'create-access-key']
cc += ['--user-name', iam_user_name]
rr = aws_cli.run(cc)

pp = f'/tmp/{iam_user_name}.txt'
access_key = rr['AccessKey']['AccessKeyId']
secret_key = rr['AccessKey']['SecretAccessKey']
with open(pp, 'w', encoding='utf-8') as ff:
    ff.write(f'AccessKeyId={access_key}\n')
    ff.write(f'SecretAccessKeyId={secret_key}\n')

print_message('Use this generated access key and secret key to deploy Ramiel Monitoring Service')
print(f'''
- AccessKeyId: {access_key}')
- SecretAccessKey: {secret_key}

Also archived here: {pp}
''')
