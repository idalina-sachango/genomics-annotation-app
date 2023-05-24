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
        glacier = boto3.client('glacier')
        if "Completed" in messge.keys() and messge["Completed"]:
            try:
                status = glacier.describe_job(
                    vaultName=config["glacier"]["VaultName"],
                    jobId=messge["JobId"]
                )
                if status["Completed"]:
                    response = glacier.get_job_output(
                        vaultName=config["glacier"]["VaultName"],
                        jobId=messge["JobId"]
                    )
                    file_body = response["body"]
                    print(file_body.read())
                    print(json.loads(file_body.read()))
                    file_param = file_body.read()
                    prefix = config["s3"]["PrefixS3"]
                    result_file_name = response["Items"][0]["s3_key_result_file"]
                    s3 = boto3.client('s3')
                    s3.upload_fileobj(file_param, results_bucket, f"{prefix}/{result_file_name}")
            except Exception as err:
                print("Job id not in glacier")
                message.delete()
        
    print("done!\n\n")         

### EOF