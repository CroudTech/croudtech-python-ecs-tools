import boto3
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mypy_boto3_cloudfront.client import CloudFrontClient
    from mypy_boto3_resourcegroupstaggingapi.client import ResourceGroupsTaggingAPIClient
    from mypy_boto3_sts.client import STSClient
    from mypy_boto3_cloudfront.type_defs import InvalidationTypeDef
else:
    CloudFrontClient = object
    ResourceGroupsTaggingAPIClient = object
    STSClient = object
    InvalidationTypeDef = object

from typing import List
import json
import time
import click
import os
from requests import get
from typing import TypedDict

class InvalidationType(TypedDict):
    Invalidation: InvalidationTypeDef

ip = get('https://api.ipify.org').content.decode('utf8')

class Cloudfront:
    def __init__(self) -> None:
        pass

    @property
    def sts_client(self) -> STSClient:
        if not hasattr(self, "_sts_client"):
            self._sts_client = boto3.client("sts")
        return self._sts_client
    
    def get_aws_user(self):
        user = self.sts_client.get_caller_identity()
        return user["Arn"]

    @property
    def resourcegroupstaggingapi_client(self) -> ResourceGroupsTaggingAPIClient:
        if not hasattr(self, "_resourcegroupstaggingapi"):
            self._resourcegroupstaggingapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
        return self._resourcegroupstaggingapi

    @property
    def cloudfront_client(self) -> CloudFrontClient:
        if not hasattr(self, "_cloudfront_client"):
            self._cloudfront_client = boto3.client("cloudfront", region_name="us-east-1")
        return self._cloudfront_client

    def get_distribution_arns_by_tag(self, tags):
        tag_filters = [{"Key": tag, "Values": [value]} for tag, value in tags.items()]
        
        distributions_search_result = self.resourcegroupstaggingapi_client.get_resources(
            TagFilters=tag_filters,
            ResourceTypeFilters=["cloudfront"]
        )

        return [result["ResourceARN"] for result in distributions_search_result["ResourceTagMappingList"]]
    
    def get_distribution_ids_by_tag(self, tags):
        return [arn.split("/").pop() for arn in self.get_distribution_arns_by_tag(tags)]
    
    def get_distributions_by_tag(self, tags):
        distributions = []
        for id in self.get_distribution_ids_by_tag(tags):
            distributions.append(self.cloudfront_client.get_distribution(Id=id))
        return distributions

    def clear_cache(self, environment, paths=None):
        if not paths:
            paths = ["/*"]
        invalidations = {}
        for id in self.get_distribution_ids_by_tag({"Environment": environment}):
            click.echo()
            invalidations[id] = self.cloudfront_client.create_invalidation(
                DistributionId=id,
                InvalidationBatch={
                    "Paths": {
                        "Items": paths,
                        "Quantity": len(paths)
                    },
                    "CallerReference": f"Ecs Tools CLI user: {self.get_aws_user()} ip: {ip}"
                }
            )["Invalidation"]
        print(json.dumps(invalidations, indent=2, default=str))
