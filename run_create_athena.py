#!/usr/bin/env python3.11
import time

from env import env
from run_common import AWSCli
from run_common import print_session
from run_common import reset_template_dir

options, args = dict(), list()


def _wait_query_execution(aws_cli, res, timeout=30):
    query_execution_id = res['QueryExecutionId']
    start_time = time.time()
    while True:
        cmd = ['athena', 'get-query-execution']
        cmd += ['--query-execution-id', query_execution_id]
        rr = aws_cli.run(cmd)

        state = rr['QueryExecution']['Status']['State']
        print(f'query state: {state}')
        if state == 'SUCCEEDED':
            break
        elif state == 'FAILED':
            raise Exception()
        elif state == 'CANCELLED':
            raise Exception()

        if time.time() - start_time > timeout:
            raise Exception()

        time.sleep(2)


def run_create_athena(settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    catalog_name = settings['CATALOG']
    bucket_name = settings['S3_RESULT_BUCKET']
    database_name = settings['DATABASE']
    tables = settings['TABLES']

    cmd = ['s3api', 'create-bucket']
    cmd += ['--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['athena', 'list-databases']
    cmd += ['--catalog-name', catalog_name]
    rr = aws_cli.run(cmd)
    rr = rr['DatabaseList']
    rr = [ee['Name'] for ee in rr]
    if database_name not in rr:
        cmd = ['athena', 'start-query-execution']
        cmd += ['--query-string', 'CREATE DATABASE `hbsmith`;']
        cmd += ['--result-configuration', f'OutputLocation=s3://{bucket_name}']
        rr = aws_cli.run(cmd)
        _wait_query_execution(aws_cli, rr)

    cmd = ['athena', 'list-table-metadata']
    cmd += ['--catalog-name', catalog_name]
    cmd += ['--database-name', database_name]
    rr = aws_cli.run(cmd)
    rr = rr['TableMetadataList']
    table_exists = [ee['Name'] for ee in rr]

    for ee in tables:
        table_name = ee['NAME']
        table_query = ee['QUERY']

        if table_name in table_exists:
            continue

        cmd = ['athena', 'start-query-execution']
        cmd += ['--query-string', table_query]
        cmd += ['--query-execution-context', f'Database={database_name}']
        cmd += ['--result-configuration', f'OutputLocation=s3://{bucket_name}']
        rr = aws_cli.run(cmd)
        _wait_query_execution(aws_cli, rr)


if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

print_session('create athena')

reset_template_dir(options)

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

    run_create_athena(settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'athena: {mm} is not found in config.json')
