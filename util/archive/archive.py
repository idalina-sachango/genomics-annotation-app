# archive.py
#
# NOTE: This file lives on the Utils instance
#
##
__author__ = 'Idalina Sachango'

import os
import io
import sys
import boto3
import json
import shutil
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('archive_config.ini')

db_name = config["postgres"]["TableName"]
dynamo_name = config["dynamo"]["TableName"]
results_bucket_name = config["s3"]["ResultsBucket"]
prefix = config["s3"]["PrefixS3"]
region_name = config["aws"]["AwsRegionName"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(dynamo_name)

# Add utility code here
url = config["aws"]["ArchiveURL"]
queue = boto3.resource("sqs", region_name=region_name).Queue(url)

while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        try: 
            body = json.loads(message.body)
            # extract message
            messge = json.loads(body["Message"])
            # extract job id
            job_id = messge["job_id"]
            # write output to jobs own directory
            os.makedirs(f"./output/{job_id}")
            # extract user id
            user_id = messge['user_id']
            bucket_file_path = prefix + user_id
            s3 = boto3.client('s3')
            # get result file name and path 
            quer = response = table.query(
                KeyConditionExpression=Key("job_id").eq(job_id)
            )
            result_name = quer["Items"][0]["s3_key_result_file"]
            result_user_id_path = f"{user_id}/{result_name}"
            bucket_file_path = prefix + result_user_id_path
            # download reuslt file
            # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-download-file.html
            s3.download_file(
                results_bucket_name, 
                bucket_file_path, 
                f"output/{job_id}/{result_name}"
            )
            # upload to glacier
            glacier = boto3.client('glacier')
            # Read the file into a seekable file-like object
            with open(f"output/{job_id}/{result_name}", 'rb') as file:
                file_contents = file.read()
                seekable_file = io.BytesIO(file_contents)
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier/client/upload_archive.html
                response = glacier.upload_archive(
                    vaultName=config["glacier"]["VaultName"],
                    body=seekable_file
                )
            # update dynamo db
            archive_id = response["archiveId"]
            response_db = table.update_item(
                TableName=dynamo_name,
                Key={'job_id': job_id},
                UpdateExpression='set results_file_archive_id = :r',
                ExpressionAttributeValues={
                    ':r': str(archive_id)
                },
                ReturnValues='UPDATED_NEW'
            )
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/delete_object.html
            s3.delete_object(
                Bucket=results_bucket_name,
                Key=bucket_file_path
            )      
        except:
            raise
        finally:
            message.delete()
            shutil.rmtree(f"./output/{job_id}")
    print("done!\n\n")

### EOF