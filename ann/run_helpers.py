import boto3
import sys
import os
import uuid
# adding util to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/gas/util')
from helpers import get_user_profile, send_email_ses

from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('ann_config.ini')

requests_topic = config["aws"]["RequestTopic"]
results_topic = config["aws"]["ResultsTopic"]
archive_topic = config["aws"]["ArchiveTopic"]
region_name = config["aws"]["AwsRegionName"]
db_table_name = config["dynamodb"]["TableName"]

dynamo = boto3.resource('dynamodb', region_name = region_name)
table = dynamo.Table(db_table_name)

### Helpers
def sns_send_archive(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=region_name)
    response = client.publish(
        TopicArn=archive_topic,
        Message=message,
        Subject="request"
    )
    print("\n")
    print(response)
    print("\n")

def sns_send_requests(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=region_name)
    response = client.publish(
        TopicArn=requests_topic,
        Message=message,
        Subject="request"
    )
    print("\n")
    print(response)
    print("\n")

def sns_send_results(message):
    """
    Send message to SNS to deliver to queue.
    """
    client = boto3.client('sns', region_name=region_name)
    response = client.publish(
        TopicArn=results_topic,
        Message=message,
        Subject="result"
    )
    print("\n")
    print(response)
    print("\n")

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