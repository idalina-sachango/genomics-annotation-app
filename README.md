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

Archiving

* I archive free users files after 5 minutes by using `subporcess.Popen()` with a python file `wait.py`. This script sleeps for 5 minutes. After it is done sleeping, it sends a delete message to my archive queue. The util instance is listening for delete messages from my archive queue and begins the process of deleting result files from s3 once its received a message. 