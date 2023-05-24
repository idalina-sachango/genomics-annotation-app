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

Archiving

* I archive free users files after 5 minutes by using `subporcess.Popen()` with a python file `wait.py`. This script sleeps for 5 minutes. After it is done sleeping,it checks the user type to see whether to archive files or persist them. If the user is a free user, it sends a delete message to my archive queue. The util instance is listening for delete messages from my archive queue in one tmux session and begins the process of deleting result files from s3 once its received a message. 

Restoring

* If in the endpoint for subscribing in views.py, a user upgrades to a premium user, a message gets sent to the restore queue with the current users job list. In util/restore.py, I begin the process of archive retrieval by looping thorugh the job list and finding all jobs marked with `results_file_archive_id` defined. For each job that meets this criteria, I initiate a retrieval job. I use a try/except for expedited retrieval. If I cannot access expedited retrieval, I inititate standard retreival. After this is started, I finish by sending message to my thaw message queue with the job id to begin the "thaw" process and deleting the message. 