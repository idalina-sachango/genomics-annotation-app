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
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.client import Config
from botocore.exceptions import ClientError

from flask import (abort, flash, redirect, render_template,
  request, session, url_for)

from gas import app, db
from decorators import authenticated, is_premium
from auth import get_profile, update_profile
# # adding anntools to the system path
# sys.path.insert(0, '/home/ec2-user/mpcs-cc/anntools')
# import driver

dynamo = boto3.resource('dynamodb', region_name = app.config["AWS_REGION_NAME"])
table = dynamo.Table(app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'])
results_bucket = app.config["AWS_S3_RESULTS_BUCKET"]

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
            driver.run(sys.argv[1], "vcf")
            # create job unique id
            job_id = sys.argv[1].split("/")[1]
            # extract user id
            user_id = session['primary_identity']
            # grab file name without full path
            file_name = sys.argv[1].split("/")[2]
            # grab annotator log file with and without job id
            log_file = f"output/{job_id}/{file_name}.count.log"
            # grab annotator result file with and without job id
            file_name_wo_vcf = file_name.split(".vcf")[0]
            result_file_name = f"{file_name_wo_vcf}.annot.vcf"
            result_file_path = f"output/{job_id}/{result_file_name}"
            # Upload the log and result file
            s3 = boto3.client('s3')
            # extract prefix
            prefix = app.config['AWS_S3_KEY_PREFIX'] + user_id

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