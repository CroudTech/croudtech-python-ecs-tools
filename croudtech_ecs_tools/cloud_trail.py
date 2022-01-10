import boto3
from botocore.config import Config as Boto3Config
from datetime import datetime, timedelta

class CloudTrail:
    def __init__(self, region):
        self.region = region
        self.ecs_client = boto3.client("cloudtrail", config=Boto3Config(
            region_name= self.region
        ))

    def lookupEntries(self, event_name, days=30, resource=None):
        start_time = datetime.utcnow() - timedelta(days=days)
        
        paginator = self.ecs_client.get_paginator('lookup_events')
        response_iterator = paginator.paginate(
            StartTime = start_time,
            LookupAttributes = [
                {
                    "AttributeKey": "EventName",
                    "AttributeValue": event_name
                }
            ]
        )

        for page in response_iterator:
            for event in page["Events"]:
                yield event            

