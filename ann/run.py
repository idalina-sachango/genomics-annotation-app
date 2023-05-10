# run.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Wrapper script for running AnnTools
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import requests
import subprocess
import json
import os
import shutil
import uuid
import sys
import boto3
import time
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.client import Config
from botocore.exceptions import ClientError
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('ann_config.ini')
# adding anntools to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/anntools')
import driver

## Code
region_name = config["aws"]["AwsRegionName"]
db_table_name = config["dynamodb"]["TableName"]
inputs_bucket = config["s3"]["InputsBucket"]
results_bucket = config["s3"]["ResultsBucket"]
request_topic = config["aws"]["RequestTopic"]
request_URL = config["aws"]["RequestURL"]
prefixs3 = config["s3"]["PrefixS3"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(db_table_name)


"""A rudimentary timer for coarse-grained profiling
"""
class Timer(object):
    def __init__(self, verbose=True):
        self.verbose = verbose
    def __enter__(self):
        self.start = time.time()
        return self
    
    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        if self.verbose:
            print(f"Approximate runtime: {self.secs:.2f} seconds")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        with Timer():
            # run the annotator
            print("FILE", sys.argv[1])
            driver.run(sys.argv[1], "vcf")
            # create job unique id
            
            job_id = sys.argv[1].split("/")[2]
            # extract user id
            user_id = sys.argv[1].split("/")[1]
            # grab file name without full path
            file_name = sys.argv[1].split("/")[3]
            # grab annotator log file with and without job id
            log_file = f"output/{user_id}/{job_id}/{file_name}.count.log"
            # grab annotator result file with and without job id
            file_name_wo_vcf = file_name.split(".vcf")[0]
            result_file_name = f"{file_name_wo_vcf}.annot.vcf"
            result_file_path = f"output/{user_id}/{job_id}/{result_file_name}"
            # Upload the log and result file
            s3 = boto3.client('s3')
            # extract prefix
            prefix = prefixs3 + user_id

            with open(log_file, "rb") as f:
                s3.upload_fileobj(f, results_bucket, f"{prefix}/{file_name}.count.log")
            with open(result_file_path, "rb") as f:
                s3.upload_fileobj(f, results_bucket, f"{prefix}/{result_file_name}")

            # add the name of the S3 key for the results file
            # Adds the name of the S3 key for the log file
            # Adds the completion time (use the current system time)
            # Updates the “job_status” key to “COMPLETED”
            now = datetime.now()
            dt_string = now.strftime("%d%m%Y%H%M%S")
            r2 = table.update_item(
                Key={'job_id': str(job_id)},
                UpdateExpression="set job_status=:r, completion_time=:p, s3_key_log_file=:k, s3_key_result_file=:j",
                ExpressionAttributeValues={
                    ':r': "COMPLETED",
                    ':p': int(dt_string), # save it in UTC
                    ':k': file_name,
                    ':j': result_file_name},
                ReturnValues="UPDATED_NEW")
    else:
        print("A valid .vcf file must be provided as input to this program.")


def sns_send_requests(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=app.config["AWS_REGION_NAME"])
    print(message)
    response = client.publish(
        TopicArn="arn:aws:sns:us-east-1:659248683008:idalina_job_requests",
        Message=message,
        Subject="request"
    )
    print(response)

def sns_send_results(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=app.config["AWS_REGION_NAME"])
    print(message)
    response = client.publish(
        TopicArn="arn:aws:sns:us-east-1:659248683008:idalina_job_results",
        Message=message,
        Subject="result"
    )
    print(response)

def generate_unique_id():
    """
    generate unique id. 
    if id exists in directory, return to top.
    """
    job_id = uuid.uuid4()
    if job_id not in os.listdir("output"):
        return job_id
    return generate_unique_id()

def put_into_dynamo(item):
    """
    Place data into Dynamo DB
    """
    response = table.put_item(Item = item)
    print("*******************")
    print(response)
    print(f"Successfully wrote job ID {item['job_id']}")

def get_from_dynamo_primary(search_by_value, search_by_name):
    """
    Retrieve data from DynamoDB using primary key
    """
    # only with primary key
    response = table.get_item(Key = {search_by_name: search_by_value})
    return response

def get_from_dynamo_secondary():
    """
    Retrieve data from DynamoDB using secondary key
    """
    response = table.query(
        IndexName = "user_id_index",
        KeyConditionExpression = Key(search_by_name).eq(search_by_value)
    )
    return response["Items"]