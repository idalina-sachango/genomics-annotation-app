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

dynamo = boto3.resource('dynamodb', region_name = app.config['AWS_REGION_NAME'])
table = dynamo.Table(app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'])

if "output" not in os.listdir("./"):
    os.mkdir("./output")

url = app.config['AWS_SNS_JOB_REQUEST_URL']
queue = boto3.resource("sqs", region_name=app.config['AWS_REGION_NAME']).Queue(url)

while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        try:
            s3 = boto3.client('s3')
            body = json.loads(message.body)
            messge = json.loads(body["Message"])
            # extract job id
            job_id = messge["job_id"]
            # extract user id
            user_id = session['primary_identity']
            # extract file name
            file_param = messge["s3_key_input_file"]
            # extract prefix
            prefix = app.config['AWS_S3_KEY_PREFIX'] + user_id
            # set pucket full file path
            bucket_file_path = f"{prefix}/{file_param}"
            file_name = messge["input_file_name"]

            # write output to jobs own directory
            if job_id not in os.listdir("output"):
                os.makedirs(f"output/{job_id}")
            s3.download_file(
                app.config['AWS_S3_INPUTS_BUCKET'],
                bucket_file_path,
                f"output/{job_id}/{file_param}"
            )

            # write to dynamodb and spawn annotator process
            try:
                # update dynamoDB job status to running
                response = table.update_item(
                    TableName=app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"],
                    Key={'job_id': job_id},
                    UpdateExpression='set job_status = :r',
                    ConditionExpression='job_status = :p',
                    ExpressionAttributeValues={
                        ':r': 'RUNNING',
                        ':p': 'PENDING'
                    },
                    ReturnValues='UPDATED_NEW'
                )
                try:
                    # spawn a subprocess using Popen
                    subprocess.Popen(["python", "./run.py", f"output/{job_id}/{file_param}"])
                except Exception as err:
                    print(str(err))
                    pass
            except:
                pass
        except:
            raise
        finally:
            message.delete()
    print("Done with loop\n\n")


### Helpers
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