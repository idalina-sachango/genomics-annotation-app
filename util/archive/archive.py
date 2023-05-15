# archive.py
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
import shutil

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('archive_config.ini')

db_name = config["postgres"]["TableName"]
results_bucket_name = config["s3"]["ResultsBucket"]
prefix = config["s3"]["PrefixS3"]
region_name = config["aws"]["AwsRegionName"]


# Add utility code here
if "output" not in os.listdir("./"):
    os.mkdir("./output")

url = config["aws"]["ArchiveURL"]
queue = boto3.resource("sqs", region_name=region_name).Queue(url)

while True:
    if "output" not in os.listdir("./"):
        os.mkdir("./output")
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        body = json.loads(message.body)
        # extract message
        messge = json.loads(body["Message"])
        print("INCOMING MESSAGE\n\n",messge,"\n")
        # extract job id
        job_id = messge["job_id"]
        # extract user id
        user_id = messge['user_id']

        bucket_file_path = prefix + user_id

        # os.makedirs(f"output/{user_id}")
        # s3.download_file(
        #     config["s3"]["ResultsBucket"],
        #     bucket_file_path,
        #     f"output/{user_id}"
        # )
        s3 = boto3.client('s3')
        bucket = s3.list_objects(Bucket= results_bucket_name, Prefix=prefix)['Contents']

        for s3_object in bucket: 
            bucket_file_path = s3_object['Key']
            if "vcf" in bucket_file_path or "log" in bucket_file_path:
                file_name = s3_object['Key'].split("/")[2]
                print(file_name)
                print(bucket_file_path)
                try:
                    s3.download_file(
                        results_bucket_name, 
                        bucket_file_path, 
                        f"output/{file_name}"
                    )

                    response = client.upload_archive(
                        vaultName='string',
                        archiveDescription='string',
                        body=b'bytes'|file
                    )   
                except:
                    raise
    shutil.rmtree("output")

print("done!")




# upload file to glacier using boto3

# add a column to dynamodb table with glacier ID

# update dynamodb table with new column for the job id



### EOF