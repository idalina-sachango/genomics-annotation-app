# restore.py
#
# NOTE: This file lives on the Utils instance
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import sys
import boto3
import json

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers
from sns_helpers import (
    sns_send_thaw
)

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('restore_config.ini')

dynamo_name = config["dynamo"]["TableName"]
region_name = config["aws"]["AwsRegionName"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(dynamo_name)

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier/client/initiate_job.html
# Add utility code here
url = config["aws"]["RestoreURL"]
queue = boto3.resource("sqs", region_name=region_name).Queue(url)

while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        try:
            body = json.loads(message.body)
            # extract message
            messge = json.loads(body["Message"])
            # extract user id
            user_id = messge['user_id']
            # extract job list
            job_list = messge["job_list"]
            glacier = boto3.client('glacier')
            for job in job_list:
                if "results_file_archive_id" in job.keys():
                    print("archive id=", job["results_file_archive_id"])
                    if len(job["results_file_archive_id"]) > 0:
                        print(job["results_file_archive_id"])
                        try:
                            print("TRYING EXPEDITED RETRIEVAL")
                            # try expedited
                            response = glacier.initiate_job(
                                vaultName = config["glacier"]["VaultName"],
                                jobParameters={
                                    "Tier": "Expedited",
                                    "Type": "archive-retrieval",
                                    "ArchiveId": str(job["results_file_archive_id"]),
                                    "SNSTopic": "arn:aws:sns:us-east-1:659248683008:idalina_thaw"
                                },
                            )
                            # send to thaw message queue
                            job_id = response["jobId"]
                            mess = {
                                "job_id": job_id
                            }

                            sns_send_thaw(str(json.dumps(mess)))
                        except:
                            print("SWITCHING TO STANDARD RETRIEVAL")
                            # try standard if expedited didnt work
                            response = glacier.initiate_job(
                                vaultName = config["glacier"]["VaultName"],
                                jobParameters={
                                    "Tier": "Standard",
                                    "Type": "archive-retrieval",
                                    "ArchiveId": str(job["results_file_archive_id"]),
                                    "SNSTopic": "arn:aws:sns:us-east-1:659248683008:idalina_thaw"
                                },
                            )
                            # send to thaw message queue
                            job_id = response["jobId"]
                            mess = {
                                "job_id": job_id
                            }

                            sns_send_thaw(str(json.dumps(mess)))
            print("done processing job list!\n\n")
        except:
            raise
        finally:
            message.delete()
    print("done!\n\n")

### EOF