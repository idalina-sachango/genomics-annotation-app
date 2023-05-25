# gas-framework
An enhanced web framework (based on [Flask](http://flask.pocoo.org/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](http://getbootstrap.com/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts for notifications, archival, and restoration
* `/aws` - AWS user data files


__Changes__:
1. `annotatation_details.html` `{{ annotation['complete_time'] }}` got changed to `{{ annotation['completion_time'] }}`

2. Changed file path of output to `user/job_id/file_name`. 

3. Added helper functions for sending messages to SNS topics in the `/util` folder. These are used for the annotator functions, `run.py` and `annotator.py` and also for `views.py`

4. Added `wait.py` script in the `/ann` folder  to time 5 minutes from the end of a job and archive if user is still a free user. 

__Archiving Process__:

* I archive free users files after 5 minutes by using `subprocess.Popen()` with a python script `wait.py`. This process is started in `run.py` in the annotator. This script sleeps for 5 minutes. After it is done sleeping, it checks the user type to see whether to archive files or persist them. If the user is a free user, it sends a delete message to my archive queue. The util instance is listening for delete messages from my archive queue in one tmux session and begins the process of deleting result files from s3 once its received a message. 

__Restoring Process__:

* If in the endpoint for subscribing in views.py, a user upgrades to a premium user, a message gets sent to the restore queue with the current users job list. In util/restore.py, I begin the process of archive retrieval by looping thorugh the job list and finding all jobs marked with `results_file_archive_id` defined. For each job that meets this criteria, I initiate a retrieval job. I use a try/except for expedited retrieval. If I cannot access expedited retrieval, I inititate standard retreival. After this is started, I finish by sending message to my thaw message queue with the Glacier job id, user id, and Dynamo DB job id to begin the "thaw" process. Then I delete the message. 

__Thaw Process__:

* Messages coming into the thaw queue are read and I call `Glacier.describe_job` to check on the status of the previous restore job. Once the job is complete, I get the name of the file by querying the Dynamo DB table for the job details and grabbing "s3_key_result_file", I grab the output of the archive retreival by calling `Glacier.get_job_output`, and finally, I put the file into the correct S3 bucket via `S3.put_object` - specifying the file body, the bucket name, and the key when doing so.


__Issue__:

* Annotation details page does not display "restoring" message when user switches from free to premium for result file. I tried editing the HTML after I'd launched my autoscaler, but the HTML changes didn't show and I ran out of time. The result file is re-uploaded to S3 after 4-5 hours after standard retrieval, though. Code for this process is in `/util`.

