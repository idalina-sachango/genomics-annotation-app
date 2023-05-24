# gas-framework
An enhanced web framework (based on [Flask](http://flask.pocoo.org/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](http://getbootstrap.com/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts for notifications, archival, and restoration
* `/aws` - AWS user data files


Changes 
* `annotatation_details.html` `{{ annotation['complete_time'] }}` got changed to `{{ annotation['completion_time'] }}`

* Changed file path of output to `user/job_id/file_name`. This is still a tentative edit. 

* Added helper functions for sending messages to SNS topics in the `util/` folder. These are used for the annotator functions, `run.py` and `annotator.py` and also for `views.py`

* Added `wait.py` script in the `ann` folder  to time 5 minutes from the end of a job and archive if user is still a free user. 

Archiving Process

* I archive free users files after 5 minutes by using `subporcess.Popen()` with a python file `wait.py`. This script sleeps for 5 minutes. After it is done sleeping,it checks the user type to see whether to archive files or persist them. If the user is a free user, it sends a delete message to my archive queue. The util instance is listening for delete messages from my archive queue in one tmux session and begins the process of deleting result files from s3 once its received a message. 

Restoring Process

* If in the endpoint for subscribing in views.py, a user upgrades to a premium user, a message gets sent to the restore queue with the current users job list. In util/restore.py, I begin the process of archive retrieval by looping thorugh the job list and finding all jobs marked with `results_file_archive_id` defined. For each job that meets this criteria, I initiate a retrieval job. I use a try/except for expedited retrieval. If I cannot access expedited retrieval, I inititate standard retreival. After this is started, I finish by sending message to my thaw message queue with the job id to begin the "thaw" process and deleting the message. 

Thaw Process

* I currently have code up for thawing the file from Glacier, but I could not get it to run as expected. At first, when I would inititate a job it would not show as completed after the 4-5 hour mark. I got this to work by specifying an SNS topic in the intitiate job function, but had trouble understanding how to read in the Streaming Body into S3

Issues Encountered:

* Queueing - sending multiple things into a queue within milliseconds of each other causes some processes to seemingly be dropped. I noticed this when trying to run several annotation jobs within a very short time frame. Certain jobs would be running and never move into completed while the jobs that came after them would. This was also true for subprocesses I ran in the annotator to wait and then archive. Some of those 'jobs' were dropped within this time frame as well. If I had more time, I would figure out the best way to make these processes run in parallel and without losing the message for any of them. 


