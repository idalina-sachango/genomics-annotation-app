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

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
from configparser import SafeConfigParser
config = SafeConfigParser(os.environ)
config.read('notify_config.ini')

db_name = config["dynamodb"]["TableName"]
results_bucket_name = config["s3"]["ResultsBucket"]
prefix = config["s3"]["PrefixS3"]

# Add utility code here

#Then use the session to get the resource
s3 = boto3.client('s3')
result = client.list_objects(Bucket=results_bucket_name, Prefix=prefix, Delimiter='/')
for o in result.get('CommonPrefixes'):
    print(o)
    # print 'sub folder : ', o.get('Prefix')

for objects in my_bucket.objects.filter(Prefix="csv_files/"):
    print(objects.key)

# select all free users from s3
user_profile = helpers.get_user_profile(job_id=None, db_name=db_name)
user_type = [x for x in user_profile if x == "free" or x == "premium"]

# download(?) file from s3

# upload file to glacier using boto3

# add a column to dynamodb table with glacier ID

# update dynamodb table with new column for the job id



### EOF