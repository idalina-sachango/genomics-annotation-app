import time
import json
import sys
# adding util to the system path
sys.path.insert(0, '/home/ec2-user/mpcs-cc/gas/util')
from helpers import get_user_profile
from sns_helpers import (
    sns_send_archive
)

user_id = sys.argv[1]
job_id = sys.argv[2]

time.sleep(300)
print("5 minutes are up.")

user_type = [x for x in get_user_profile(user_id, "idalina_accounts") \
    if "free_user" in str(x) or "premium_user" in str(x)]

if user_type[0] == "free_user":
    print(f"User is free user. Deleting job results: {job_id}")
    arch = {
        "user_id": user_id,
        "job_id": job_id
    }

    sns_send_archive(str(json.dumps(arch)))
else:
    print("User is a premium user. Persisting job results file.")
