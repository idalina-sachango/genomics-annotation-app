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

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('thaw_config.ini')


# Add utility code here

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
        print("INCOMING MESSAGE\n\n",messge,"\n")

        job_id = messge["job_id"]

        glacier = boto3.client('glacier')

        status = client.describe_job(
            vaultName=config["glacier"]["VaultName"],
            jobId=job_id
        )

        if status["Completed"]:
            response = client.get_job_output(
                vaultName=config["glacier"]["VaultName"],
                jobId=job_id
            )

            file_body = response["body"]

            

### EOF