import requests
import subprocess
import json
import os
import shutil
import uuid
import sys
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.client import Config
from botocore.exceptions import ClientError
from configparser import ConfigParser
# adding util to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/gas/util')
from helpers import get_user_profile, send_email_ses

config = ConfigParser(os.environ)
config.read('ann_config.ini')

region_name = config["aws"]["AwsRegionName"]
db_table_name = config["dynamodb"]["TableName"]
inputs_bucket = config["s3"]["InputsBucket"]
results_bucket = config["s3"]["ResultsBucket"]
request_topic = config["aws"]["RequestTopic"]
request_URL = config["aws"]["RequestURL"]
prefixs3 = config["s3"]["PrefixS3"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(db_table_name)

if "output" not in os.listdir("./"):
    os.mkdir("./output")

### Helpers
def sns_send_requests(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=region_name)
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
    client = boto3.client('sns', region_name=region_name)
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

## Annotator code

url = request_URL
queue = boto3.resource("sqs", region_name=region_name).Queue(url)

while True:
    messages = queue.receive_messages(WaitTimeSeconds=10)
    for message in messages:
        try:
            s3 = boto3.client('s3')
            body = json.loads(message.body)
            # extract message
            messge = json.loads(body["Message"])
            print("INCOMING MESSAGE\n\n",messge)
            # extract job id
            job_id = messge["job_id"]
            # extract user id
            user_id = messge['user_id']
            email = [x for x in get_user_profile(user_id, "idalina_accounts") if "@uchicago.edu" in str(x)]
            # extract file name
            file_param = messge["s3_key_input_file"]
            # extract prefix
            prefix = prefixs3 + user_id
            # set pucket full file path
            bucket_file_path = f"{prefix}/{file_param}"
            file_name = messge["input_file_name"]

            # write output to jobs own directory
            if job_id not in os.listdir("output"):
                os.makedirs(f"output/{job_id}")
            s3.download_file(
                inputs_bucket,
                bucket_file_path,
                f"output/{job_id}/{file_param}"
            )

            # write to dynamodb and spawn annotator process
            try:
                # update dynamoDB job status to running
                response = table.update_item(
                    TableName=db_table_name,
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
                    completion_message = {
                        "email": email[0],
                        "message": "Result and log file uploaded to S3 and database updated."
                    }
                    sns_send_results(str(json.dumps(completion_message)))
                except Exception as err:
                    print(str(err))
            except:
                raise
        except:
            raise
        finally:
            message.delete()
    print("Done with loop\n\n")


