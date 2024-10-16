#!/usr/bin/env python3.12
from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_codebuild_project():
    if not env.get('codebuild'):
        return False

    project_name_list = list()
    codebuild_list = env['codebuild']
    for sl in codebuild_list:
        if sl['TYPE'] == 'project':
            project_name_list.append(sl['NAME'])

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)

    return len(result['projects'])


results = list()

if describe_codebuild_project():
    results.append('CodeBuild Topic -------------- O')
else:
    results.append('CodeBuild Topic -------------- X')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
