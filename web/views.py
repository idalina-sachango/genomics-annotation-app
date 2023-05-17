# views.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Application logic for the GAS
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import uuid
import time
import json
import requests
import sys
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

# adding util to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/gas/util')
from sns_helpers import (
    sns_send_archive,
    sns_send_results,
    sns_send_thaw,
    sns_send_requests,
    sns_send_restore,
    put_into_dynamo
)

dynamo = boto3.resource('dynamodb', region_name = app.config['AWS_REGION_NAME'])
table = dynamo.Table(app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'])


"""Start annotation request
Create the required AWS S3 policy document and render a form for
uploading an annotation input file using the policy document.

Note: You are welcome to use this code instead of your own
but you can replace the code below with your own if you prefer.
"""
@app.route('/annotate', methods=['GET'])
@authenticated
def annotate():
  # Create a session client to the S3 service
  s3 = boto3.client('s3',
    region_name=app.config['AWS_REGION_NAME'],
    config=Config(signature_version='s3v4'))
  # bucket name
  bucket = app.config['AWS_S3_INPUTS_BUCKET']
  # user id
  user_id = session['primary_identity']
  # Generate unique ID to be used as S3 key (name)
  key = app.config['AWS_S3_KEY_PREFIX'] + user_id + '/' + \
    str(uuid.uuid4()) + '~${filename}'
  # Create the redirect URL
  redirect_url = str(request.url) + '/job'
  # Define policy fields/conditions
  encryption = app.config['AWS_S3_ENCRYPTION']
  acl = app.config['AWS_S3_ACL']
  expiration = app.config['AWS_SIGNED_REQUEST_EXPIRATION']
  # policy 
  p_dict = {
    "fields": {
      # "expiration": app.config['AWS_SIGNED_REQUEST_EXPIRATION'], 
      "success_action_redirect": redirect_url,
      "x-amz-server-side-encryption": encryption,
      "acl": acl
    },
    "expiration": expiration,
    "conditions": [
      {"acl": acl},
      {"success_action_redirect": redirect_url},
      # ["starts-with", "$key", "idalina/"],
      ["starts-with", "$success_action_redirect", redirect_url],
      {"x-amz-server-side-encryption": encryption},
    ]
  }
  try:
    # generate signed POST request
    response = s3.generate_presigned_post(
      Bucket = bucket,
      Key = key,
      Fields=p_dict["fields"],
      Conditions = p_dict["conditions"],
      ExpiresIn = p_dict["expiration"]
    )
  except ClientError as e:
    app.logger.error(f"Unable to generate presigned URL for upload: {e}")
    return abort(500)
  # Render the upload form which will parse/submit the presigned POST
  return render_template('annotate.html', s3_post=response)


"""Fires off an annotation job
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.

Note: Update/replace the code below with your own from previous
homework assignments
"""
@app.route('/annotate/job', methods=['GET'])
@authenticated
def create_annotation_job_request():
  # Get bucket name, key, and job ID from the S3 redirect URL
  bucket = str(request.args.get('bucket'))
  key = str(request.args.get('key'))
  # get job id from filename
  file_name = key.split("/")[2]
  job_id = file_name.split("~")[0]
  # get user id and email
  user_id = session['primary_identity']
  user_email = session['email']
  # create a job item and persist it to the annotations database
  now = datetime.now()
  dt_string = now.strftime("%d%m%Y%H%M%S")
  data = {
    "job_id": job_id,
    "user_id": user_id,
    "input_file_name": file_name.split("~")[1],
    "s3_inputs_bucket": bucket,
    "s3_key_input_file": file_name,
    "submit_time": int(dt_string),
    "job_status": "PENDING"
  }
  try:
    # insert dynamo db
    put_into_dynamo(data)
    try:
      # publish notification to sns
      sns_send_requests(str(json.dumps(data)))
    except Exception as err:
      return jsonify({'code': 500, 'error': str(err)}), 500
  except Exception as err:
    return jsonify({'code': 500, 'error': str(err)}), 500
  return render_template('annotate_confirm.html', job_id=job_id)


"""List all annotations for the user
"""
@app.route('/annotations', methods=['GET'])
@authenticated
def annotations_list():
  # Get list of annotations to display
  #Make Initial Query
  user_id = session['primary_identity']
  response = table.query(
    IndexName="user_id_index",
    KeyConditionExpression=Key("user_id").eq(user_id)
  )
  list_of_jobs = response["Items"]
  for d in list_of_jobs:
    dt_time_format = "%d%m%Y%H%M%S"
    date_obj = datetime.strptime(str(d["submit_time"]), dt_time_format)
    d["submit_time"] = str(date_obj)
  return render_template('annotations.html', annotations=list_of_jobs)


"""Display details of a specific annotation job
"""
@app.route('/annotations/<id>', methods=['GET'])
@authenticated
def annotation_details(id):
  s3 = boto3.client('s3')
  #Make Initial Query
  response = table.query(
    KeyConditionExpression=Key("job_id").eq(id)
  )
  
  job = response["Items"][0]
  user_id = session["primary_identity"]
  # reformat date into human readable format
  dt_time_format = "%d%m%Y%H%M%S"

  start_date_obj = datetime.strptime(str(job["submit_time"]), dt_time_format)
  job["submit_time"] = str(start_date_obj)

  if "completion_time" in job.keys():
    end_date_obj = datetime.strptime(str(job["completion_time"]), dt_time_format)
    job["completion_time"] = str(end_date_obj)
  if ("completion_time" in job.keys()) and ("results_file_archive_id" not in job.keys()):
    # generate signed POST request
    try:
      url = s3.generate_presigned_url(
        'get_object',
        Params={
          'Bucket': app.config["AWS_S3_RESULTS_BUCKET"],
          'Key': app.config['AWS_S3_KEY_PREFIX'] + user_id + "/" + job["s3_key_result_file"]
        }
      )
      job["result_file_url"] = url
    except ClientError as e:
      logging.error(e)
  elif ("results_file_archive_id" in job.keys()) and (session.get('role') == "free_user"):
    return render_template('annotation_details.html', annotation=job, free_access_expired=True)
  return render_template('annotation_details.html', annotation=job)


"""Display the log file contents for an annotation job
"""
@app.route('/annotations/<id>/log', methods=['GET'])
@authenticated
def annotation_log(id):
  s3 = boto3.client('s3')
  #Make Initial Query
  response = table.query(
    KeyConditionExpression=Key("job_id").eq(id)
  )
  
  job = response["Items"][0]

  user_id = session["primary_identity"]

  response = "The annotation job is still running"
  if "completion_time" in job.keys():
    # generate signed POST request
    try:
      url = s3.generate_presigned_url(
        'get_object',
        Params={
          'Bucket': app.config["AWS_S3_RESULTS_BUCKET"],
          'Key': app.config['AWS_S3_KEY_PREFIX'] + user_id + "/" + job["s3_key_log_file"]
        }
      )
      response = requests.get(url).text
    except ClientError as e:
      logging.error(e)
  return render_template('view_log.html', log_file_contents=response, job_id=id)


"""Subscription management handler
"""
@app.route('/subscribe', methods=['GET', 'POST'])
@authenticated
def subscribe():
  if (request.method == 'GET'):
    # Display form to get subscriber credit card info
    if (session.get('role') == "free_user"):
      return render_template('subscribe.html')
    else:
      return redirect(url_for('profile'))

  elif (request.method == 'POST'):
    # Update user role to allow access to paid features
    update_profile(
      identity_id=session['primary_identity'],
      role="premium_user"
    )
    print("IN POST")

    # Update role in the session
    session['role'] = "premium_user"

    # Request restoration of the user's data from Glacier
    # Add code here to initiate restoration of archived user data
    # Make sure you handle files not yet archived!

    user_id = session["primary_identity"]

    #query dynamo db
    response = table.query(
      IndexName="user_id_index",
      KeyConditionExpression=Key("user_id").eq(user_id)
    )
    
  
    job_list = response["Items"]

    for j in job_list:
      j["submit_time"] = str(j["submit_time"])
      j["completion_time"] = str(j["completion_time"])

    message = {
      "user_id": user_id,
      "job_list": job_list
    }

    # send job list to message queue
    sns_send_restore(str(json.dumps(message)))

    # Display confirmation page
    return render_template('subscribe_confirm.html') 

"""Reset subscription
"""
@app.route('/unsubscribe', methods=['GET'])
@authenticated
def unsubscribe():
  # Hacky way to reset the user's role to a free user; simplifies testing
  update_profile(
    identity_id=session['primary_identity'],
    role="free_user"
  )
  return redirect(url_for('profile'))



"""DO NOT CHANGE CODE BELOW THIS LINE
*******************************************************************************
"""

"""Home page
"""
@app.route('/', methods=['GET'])
def home():
  return render_template('home.html')

"""Login page; send user to Globus Auth
"""
@app.route('/login', methods=['GET'])
def login():
  app.logger.info(f"Login attempted from IP {request.remote_addr}")
  # If user requested a specific page, save it session for redirect after auth
  if (request.args.get('next')):
    session['next'] = request.args.get('next')
  return redirect(url_for('authcallback'))

"""404 error handler
"""
@app.errorhandler(404)
def page_not_found(e):
  return render_template('error.html', 
    title='Page not found', alert_level='warning',
    message="The page you tried to reach does not exist. \
      Please check the URL and try again."
    ), 404

"""403 error handler
"""
@app.errorhandler(403)
def forbidden(e):
  return render_template('error.html',
    title='Not authorized', alert_level='danger',
    message="You are not authorized to access this page. \
      If you think you deserve to be granted access, please contact the \
      supreme leader of the mutating genome revolutionary party."
    ), 403

"""405 error handler
"""
@app.errorhandler(405)
def not_allowed(e):
  return render_template('error.html',
    title='Not allowed', alert_level='warning',
    message="You attempted an operation that's not allowed; \
      get your act together, hacker!"
    ), 405

"""500 error handler
"""
@app.errorhandler(500)
def internal_error(error):
  return render_template('error.html',
    title='Server error', alert_level='danger',
    message="The server encountered an error and could \
      not process your request."
    ), 500

### EOF
