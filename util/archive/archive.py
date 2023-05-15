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

# Add utility code here

#Then use the session to get the resource
s3 = boto3.client('s3')
result = s3.list_objects(Bucket=results_bucket_name, Prefix=prefix, Delimiter='/')
for o in result.get('CommonPrefixes'):
    user_file_path = o.get('Prefix')
    # select all free users from s3
    user_id = user_file_path.split("/")[1]
    user_profile = helpers.get_user_profile(id=user_id, db_name=db_name)
    user_type = [x for x in user_profile if x == "free_user"]
    print(user_type)

# for objects in my_bucket.objects.filter(Prefix="csv_files/"):
#     print(objects.key)



# download(?) file from s3

# upload file to glacier using boto3

# add a column to dynamodb table with glacier ID

# update dynamodb table with new column for the job id



### EOF