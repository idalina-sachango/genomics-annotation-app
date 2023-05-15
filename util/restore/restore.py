# restore.py
#
# NOTE: This file lives on the Utils instance
#
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
config.read('restore_config.ini')

db_name = config["postgres"]["TableName"]
dynamo_name = config["dynamo"]["TableName"]
results_bucket_name = config["s3"]["ResultsBucket"]
prefix = config["s3"]["PrefixS3"]
region_name = config["aws"]["AwsRegionName"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(dynamo_name)

# Add utility code here

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier/client/initiate_job.html

while True:
    glacier = boto3.client('glacier')
    glacier.initiate_job(
        vaultName = config["glacier"]["VaultName"],
        jobParameters={
            "Tier": "Expedited"
            "OutputLocation": {"S3": {
                "BucketName": config["s3"]["ResultsBucket"],
                "Prefix": config["s3"]["PrefixS3"],
                "AccessControlList": [{
                    "Grantee": {
                        "Type": "Group"
                    }
                }]
            }}
        },
    )
### EOF