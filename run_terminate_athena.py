#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_athena(name, settings):
    print_session(f'terminate athena: {name}')

    aws_cli = AWSCli(settings['AWS_REGION'])

    catalog_name = settings['CATALOG']
    database_name = settings['DATABASE']
    tables = settings['TABLES']

    print_message('terminate athena tables')
    for tt in tables:
        table_name = tt['NAME']
        s3_location = tt['S3_LOCATION']

        cmd = ['athena', 'start-query-execution']
        cmd += ['--query-string', f'DROP TABLE {database_name}.{table_name};']
        cmd += ['--query-execution-context', f'Database={database_name},Catalog={catalog_name}']
        cmd += ['--result-configuration', f'OutputLocation=s3://{s3_location}/']
        aws_cli.run(cmd, ignore_error=True)

    time.sleep(10)

    print_message('terminate athena database')
    cmd = ['athena', 'start-query-execution']
    cmd += ['--query-string', f'DROP DATABASE {database_name};']
    cmd += ['--query-execution-context', f'Database={database_name},Catalog={catalog_name}']
    cmd += ['--result-configuration', f'OutputLocation=s3://{s3_location}/']
    aws_cli.run(cmd, ignore_error=True)


print_session('terminate athena')

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('athena', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    run_terminate_athena(settings['NAME'], settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'athena: {mm} is not found in config.json')
