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

iam_policy_name = 'ramiel_codedeploy_iam_session_permission'
account_id = aws_cli.get_caller_account_id()
policy_arn = f'arn:aws:iam::{account_id}:policy/ramiel_codedeploy_iam_session_permission'
cc = ['iam', 'get-policy']
cc += ['--policy-arn', policy_arn]
rr = aws_cli.run(cc, ignore_error=True)
if not rr:
    cc = ['iam', 'create-policy']
    cc += ['--policy-name', iam_policy_name]
    cc += ['--policy-document', 'file://aws_iam/aws-codedeploy-ramiel-permission.json']
    rr = result = aws_cli.run(cc)

iam_user_name = 'ramiel_codedeploy_iam_session_user'
cc = ['iam', 'get-user']
cc += ['--user-name', iam_user_name]
rr = aws_cli.run(cc, ignore_error=True)
if not rr:
    cc = ['iam', 'create-user']
    cc += ['--user-name', iam_user_name]
    aws_cli.run(cc)

    cc = ['iam', 'attach-user-policy']
    cc += ['--user-name', iam_user_name]
    cc += ['--policy-arn', policy_arn]
    aws_cli.run(cc)

iam_role_name = 'ramiel_codedeploy_iam_session_role'
cc = ['iam', 'get-role']
cc += ['--role-name', iam_role_name]
rr = aws_cli.run(cc, ignore_error=True)
if not rr:
    cc = ['iam', 'create-role']
    cc += ['--role-name', iam_role_name]
    cc += ['--assume-role-policy-document', 'file://aws_iam/aws-codedeploy-ramiel-role.json']
    rr = aws_cli.run(cc)
    role_arn = rr['Role']['Arn']

print_message('create a role for codedeploy')

cc = ['iam', 'attach-role-policy']
cc += ['--role-name', iam_role_name]
cc += ['--policy-arn', policy_arn]
aws_cli.run(cc)

print_message('create codedeploy resources: applications and deployment groups')

for app in settings['APPLICATIONS']:
    app_name = app['NAME']

    cc = ['deploy', 'get-application']
    cc += ['--application-name', app_name]
    rr = aws_cli.run(cc, ignore_error=True)
    if not rr:
        cc = ['deploy', 'create-application']
        cc += ['--application-name', app_name]
        aws_cli.run(cc)

    for dep_group in app['DEPLOYMENT_GROUPS']:
        dep_name = dep_group['NAME']
        on_premises_tag_set = dep_group['ON_PREMISES_TAG_SET']

        cc = ['deploy', 'get-deployment-group']
        cc += ['--application-name', app_name]
        cc += ['--deployment-group-name', dep_name]
        rr = aws_cli.run(cc, ignore_error=True)
        if rr:
            continue

        cc = ['deploy', 'create-deployment-group']
        cc += ['--application-name', app_name]
        cc += ['--deployment-group-name', dep_name]
        cc += ['--service-role-arn', role_arn]
        if on_premises_tag_set:
            cc += ['--on-premises-tag-set', on_premises_tag_set]
        aws_cli.run(cc)

print_message(f'create access key for codedeploy user {iam_user_name}')

cc = ['iam', 'list-access-keys']
cc += ['--user-name', iam_user_name]
rr = aws_cli.run(cc, ignore_error=True)
if rr:
    print_message('Generate access key is skipped because the user already has access key(s)')
else:
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
