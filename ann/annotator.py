import requests
import subprocess
import json
import os
import shutil
import uuid
import sys
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.client import Config
from botocore.exceptions import ClientError
from configparser import ConfigParser
# adding util to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/gas/util')
from helpers import get_user_profile, send_email_ses

config = ConfigParser(os.environ)
config.read('ann_config.ini')

region_name = config["aws"]["AwsRegionName"]
db_table_name = config["dynamodb"]["TableName"]
inputs_bucket = config["s3"]["InputsBucket"]
results_bucket = config["s3"]["ResultsBucket"]
request_URL = config["aws"]["RequestURL"]
prefixs3 = config["s3"]["PrefixS3"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(db_table_name)

if "output" not in os.listdir("./"):
    os.mkdir("./output")

## Annotator code
url = request_URL
queue = boto3.resource("sqs", region_name=region_name).Queue(url)
while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        s3 = boto3.client('s3')
        body = json.loads(message.body)
        # extract message
        messge = json.loads(body["Message"])
        # extract job id
        job_id = messge["job_id"]
        # extract user id
        user_id = messge['user_id']
        # extract file name
        file_param = messge["s3_key_input_file"]
        # extract prefix
        prefix = prefixs3 + user_id
        # set pucket full file path
        bucket_file_path = f"{prefix}/{file_param}"
        file_name = messge["input_file_name"]
        # write output to jobs own directory
        os.makedirs(f"output/{user_id}/{job_id}")  
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-download-file.html
            s3.download_file(
                inputs_bucket,
                bucket_file_path,
                f"output/{user_id}/{job_id}/{file_param}"
            )
            # write to dynamodb and spawn annotator process
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/client/update_item.html
            # update dynamoDB job status to running
            response = table.update_item(
                TableName=db_table_name,
                Key={'job_id': job_id},
                UpdateExpression='set job_status = :r',
                ConditionExpression='job_status = :p',
                ExpressionAttributeValues={
                    ':r': 'RUNNING',
                    ':p': 'PENDING'
                },
                ReturnValues='UPDATED_NEW'
            )
            # spawn a subprocess using Popen
            subprocess.Popen(["python", "./run.py", f"output/{user_id}/{job_id}/{file_param}"])
            message.delete()
        except ClientError as err:
            print(err)
    print("Done with loop\n\n")


