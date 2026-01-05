# engine/persistence.py

import json
import os
import boto3
from config import OUTPUT_BUCKET, OUTPUT_PREFIX

s3 = boto3.client("s3")


def save_results_locally(summary, detailed, timestamp):
    os.makedirs("results", exist_ok=True)
    with open(f"results/summary_{timestamp}.json", "w") as f:
        json.dump(summary, f, indent=2)
    with open(f"results/detailed_{timestamp}.json", "w") as f:
        json.dump(detailed, f, indent=2)
    return True


def save_results_to_s3(summary, detailed, timestamp):
    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=f"{OUTPUT_PREFIX}summary_{timestamp}.json",
        Body=json.dumps(summary, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=f"{OUTPUT_PREFIX}detailed_{timestamp}.json",
        Body=json.dumps(detailed, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    return True
