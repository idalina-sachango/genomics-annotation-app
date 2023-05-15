import time
import json
import sys
from run_helpers import (
    sns_send_archive
)

user_id = sys.argv[1]
job_id = sys.argv[2]

time.sleep(300)
print(f"5 minutes are up. Deleting job : {job_id}")

arch = {
    "user_id": user_id,
    "job_id": job_id
}

sns_send_archive(str(json.dumps(arch)))