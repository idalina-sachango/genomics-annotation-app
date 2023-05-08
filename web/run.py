# run.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Wrapper script for running AnnTools
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import sys
import time
import subprocess
import boto3
from datetime import datetime
# adding anntools to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/anntools')
import driver

dynamo = boto3.resource('dynamodb', region_name = "us-east-1")
table = dynamo.Table('idalina_annotations')

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
            # grab file name without full path
            file_name = sys.argv[1].split("/")[2]
            # grab annotator log file with and without job id
            log_file = f"output/{job_id}/{file_name}.count.log"
            # grab annotator result file with and without job id
            file_name_wo_vcf = file_name.split(".vcf")[0]
            result_file_name = f"{file_name_wo_vcf}.annot.vcf"
            result_file_path = f"output/{job_id}/{result_file_name}"
            # Upload the log and result file
            # source: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html
            s3 = boto3.client('s3')

            with open(log_file, "rb") as f:
                s3.upload_fileobj(f, "mpcs-cc-gas-results", f"idalina/{file_name}.count.log")
            with open(result_file_path, "rb") as f:
                s3.upload_fileobj(f, "mpcs-cc-gas-results", f"idalina/{result_file_name}")

            # add the name of the S3 key for the results file
            # Adds the name of the S3 key for the log file
            # Adds the completion time (use the current system time)
            # Updates the “job_status” key to “COMPLETED”
            # datetime object containing current date and time
            # source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/client/update_item.html
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