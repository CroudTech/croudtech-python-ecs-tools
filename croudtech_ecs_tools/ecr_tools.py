from collections import defaultdict
from genericpath import exists
import boto3
from botocore.config import Config as Boto3Config

from .cloud_trail import CloudTrail
import json
from datetime import datetime
import os
import json_stream

class RegistryArn:
    arn_keys = [
        "type",
        "partition",
        "service",
        "region",
        "accountId",
        "resource",
    ]
    def __init__(self, arn):
        self.arn_string = arn
        self.arn = dict(zip(self.arn_keys, arn.split(":")))
        self.arn["resource"] = "/".join(self.arn["resource"].split("/")[1:])

    def __str__(self) -> str:
        return self.arn_string

    def __getattr__(self, __name: str):
        if __name in self.arn:
            return self.arn[__name]
        else:
            raise AttributeError()

    @property
    def image_url(self):
        return f"{self.accountId}.dkr.ecr.{self.region}.amazonaws.com/{self.resource}"
    
        

class EcrBatchGetImageEvent:
    def __init__(self, event):
        self.event = event

    @property
    def client_account(self):
        return self.event["userIdentity"]["accountId"]

    @property
    def user_name(self):
        if "userName" not in self.event["userIdentity"]["sessionContext"]["sessionIssuer"]:
            return "nouser"
        return self.event["userIdentity"]["sessionContext"]["sessionIssuer"]["userName"]

    @property
    def registry_arn(self):
        return RegistryArn(self.event["resources"][0]["ARN"])

    @property
    def is_digest(self):
        return "imageDigest" in self.event["requestParameters"]["imageIds"][0] and "imageTag" not in self.event["requestParameters"]["imageIds"][0]

    @property
    def image_tag(self):
        if "imageTag" in self.event["requestParameters"]["imageIds"][0] :
            return self.event["requestParameters"]["imageIds"][0]["imageTag"]
        elif "imageDigest" in self.event["requestParameters"]["imageIds"][0]:
            return self.event["requestParameters"]["imageIds"][0]["imageDigest"]
    
    @property
    def image_url(self):
        return f"{self.registry_arn.image_url}:{self.image_tag}"

    @property
    def event_time(self):
        return datetime.fromisoformat(self.event["eventTime"].replace("Z", ""))

    @property
    def dict(self):
        return {
            "EventTime": self.event_time,
            "ClientAccount": self.client_account,
            "UserName": self.user_name,
            "RegistryArn": self.registry_arn,
            "ImageTag": self.image_tag,
            "ImageUrl": self.image_url,
            "IsDigest": self.is_digest,
        }

    def __str__(self) -> str:
        return json.dumps(self.dict, indent=2, default=str)

class EcrRepo:
    
    def __init__(self, repo, ecr_client):
        self.ecr_client = ecr_client
        self.repo = repo
        self.repo["tags"] = self.getTags()

    def __getattr__(self, __name: str):
        if __name in self.repo:
            return self.repo[__name]
        else:
            raise AttributeError()

    def getTags(self):
        paginator = self.ecr_client.get_paginator("describe_images")
        response_iterator = paginator.paginate(
            registryId=self.registryId,
            repositoryName=self.repositoryName,            
            filter={
                'tagStatus': 'ANY'
            },
        )
        tags = []
        for page in response_iterator:
            for imageDetail in page["imageDetails"]:
                if "imageTags" in imageDetail:
                    tags.append(imageDetail["imageTags"])
        return tags

    def __str__(self):
        return json.dumps(self.repo, indent=2, default=str)

class EcrTools:
    cachefile = "./imagepulls.json"
    def __init__(self, region, output):
        self.region = region
        self.output = output
        self.ecr_client = boto3.client("ecr", config=Boto3Config(
            region_name= self.region
        ))

    def getRepos(self):
        if not hasattr(self, "repos"):
            self.repos = {}
            paginator = self.ecr_client.get_paginator('describe_repositories')
            response_iterator = paginator.paginate()
            for page in response_iterator:
                for repo in page["repositories"]:
                    self.repos[repo["repositoryArn"]] = EcrRepo(repo, self.ecr_client).repo
        return self.repos        

    def parseEventTime(self, item):
        item["EventTime"] = datetime.fromisoformat(item["EventTime"])
        return item

    def loadImagePullsFromCache(self):
        if os.path.exists(self.cachefile):
            with open(self.cachefile, "r") as f:
                f = open(self.cachefile)
                data = [self.parseEventTime(v) for v in json.load(f)]
                return data
        return []

    def fetchRecentImagePulls(self, days=30):
        filename = './imagepulls.json'
        if not hasattr(self, "imagePulls"):
            self.imagePulls = self.loadImagePullsFromCache()
            try:
                earliest = self.imagePulls[list(self.imagePulls.keys())[-1]]
                latest = self.imagePulls[list(self.imagePulls.keys())[0]]
            except:
                earliest = None
                latest = None
            # print(latest)
            # print(earliest)
            # exit()
            with open(self.cachefile, 'w+') as cachefile:
                cloud_trail = CloudTrail(self.region)
                get_image_events = cloud_trail.lookupEntries("BatchGetImage", days)
                for event in get_image_events:
                    event_object = EcrBatchGetImageEvent(json.loads(event["CloudTrailEvent"]))
                    if event_object.registry_arn not in  self.imagePulls:
                        event_dict = event_object.dict
                        if event_dict not in self.imagePulls:
                            self.imagePulls.append(event_object.dict)
                        # self.imagePulls = sorted(self.imagePulls, key=lambda x: (self.imagePulls[x]["EventTime"]))
                        self.imagePulls = list(sorted(self.imagePulls, key = lambda x: (x["EventTime"])))
                        cachefile.seek(0)
                        cachefile.write(json.dumps(self.imagePulls, indent=2, default=str))
                        self.output.secho(f"[{event_object.event_time}] Found image pull for {event_object.image_url}", fg="cyan")
                
        return self.imagePulls

    def findStaleImages(self, days=30):
        self.recentImagePulls = self.fetchRecentImagePulls(days)

        # print(json.dumps(self.getRepos(), indent=2, default=str))
        # print(json.dumps(self.fetchRecentImagePulls(days), indent=2, default=str))
