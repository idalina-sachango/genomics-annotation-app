# thaw.py
#
# NOTE: This file lives on the Utils instance
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import sys
import boto3
import json
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('thaw_config.ini')


# Add utility code here
results_bucket = config["s3"]["ResultsBucket"]

dynamo_name = config["dynamo"]["TableName"]
region_name = config["aws"]["AwsRegionName"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(dynamo_name)

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier/client/initiate_job.html
# Add utility code here
url = config["aws"]["ThawURL"]
queue = boto3.resource("sqs", region_name=region_name).Queue(url)
while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        body = json.loads(message.body)
        # extract message
        messge = json.loads(body["Message"])
        if "job_id" in messge.keys():
            user_id = messge["user_id"]

            glacier = boto3.client('glacier')
            status = glacier.describe_job(
                vaultName=config["glacier"]["VaultName"],
                jobId=messge["job_id"]
            )

            
            if status["Completed"]:
                quer = response = table.query(
                    KeyConditionExpression=Key("job_id").eq(messge["dynamo_db"])
                )
                try:
                    response_output = glacier.get_job_output(
                        vaultName=config["glacier"]["VaultName"],
                        jobId=messge["job_id"]
                    )
                    file_body = response_output["body"]
                    prefix = config["s3"]["PrefixS3"] + user_id
                    result_file_name = quer["Items"][0]["s3_key_result_file"]

                    s3 = boto3.client('s3')
                    response = s3.put_object(
                        Body=file_body.read(),
                        Bucket=results_bucket, 
                        Key=f"{prefix}/{result_file_name}"
                    )
                    message.delete()
                except ClientError as err:
                    print(err) 
    print("done!\n\n")         

### EOF