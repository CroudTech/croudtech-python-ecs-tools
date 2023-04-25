import boto3
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import ServiceTypeDef
    from mypy_boto3_servicediscovery.type_defs import NamespaceTypeDef
    from mypy_boto3_ecs.client import ECSClient
else:
    ServiceTypeDef = object
    NamespaceTypeDef = object
    ECSClient = object

from typing import List
import json
from datetime import datetime
import click



def parse_arn(arn):
    elements = arn.split(':')
    result = {'arn': elements[0],
            'partition': elements[1],
            'service': elements[2],
            'region': elements[3],
            'account': elements[4]
           }
    if len(elements) == 7:
        result['resourcetype'], result['resource'] = elements[5:]
    elif '/' not in elements[5]:
        result['resource'] = elements[5]
        result['resourcetype'] = None
    else:
        result['resourcetype'], result['resource'] = elements[5].split('/')
    return result

def chunk_list(list_to_chunk, size):
    return [list_to_chunk[i * size:(i + 1) * size] for i in range((len(list_to_chunk) + size - 1) // size )]

class Ecs:
    def __init__(self, cluster):
        self.cluster_name = cluster        

    @property
    def ecs_client(self):
        if not hasattr(self, "_ecs_client"):
            self._ecs_client = boto3.client("ecs")
        return self._ecs_client

    @property
    def servicediscovery_client(self):
        if not hasattr(self, "_servicediscovery_client"):
            self._servicediscovery_client = boto3.client("servicediscovery")
        return self._servicediscovery_client

    @property
    def services(self) -> List[ServiceTypeDef]:
        if not hasattr(self, "_services"):
            self._services = []
            for service_arns in chunk_list(self.service_arns, 10):
                self._services = self._services + self.ecs_client.describe_services(cluster=self.cluster_name, services=service_arns)["services"]  
        return self._services

    @property
    def namespaces(self) -> List[NamespaceTypeDef]:
        if not hasattr(self, "_namespaces"):
            self._namespaces = {}
            paginator = self.servicediscovery_client.get_paginator("list_namespaces")
            response_iterator = paginator.paginate()
            for page in response_iterator:
                for namespace in page["Namespaces"]:
                    self._namespaces[namespace["Id"]] = namespace
        return self._namespaces

    @property
    def service_arns(self):
        if not hasattr(self, "_service_arns"):
            self._service_arns = []
            paginator = self.ecs_client.get_paginator("list_services")
            response_iterator = paginator.paginate(
                cluster=self.cluster_name,                
            )
            for page in response_iterator:
                self._service_arns = self._service_arns + page["serviceArns"]
        return self._service_arns

    def list_ecs_service_endpoints(self):
        self._ecs_service_endpoints = {}        
        for service in self.services:
            for service_registry_arn in service["serviceRegistries"]:
                sd = self.servicediscovery_client.get_service(Id=parse_arn(service_registry_arn["registryArn"])["resource"])
                hostname = ".".join([sd["Service"]["Name"], self.namespaces[sd["Service"]["NamespaceId"]]["Name"]])
                self._ecs_service_endpoints[hostname] = service["serviceName"]

        return self._ecs_service_endpoints


class ServiceInfo:
    def __init__(self):
        pass

    @property
    def clusters(self):
        if not hasattr(self, "_clusters"):
            self._clusters = []
            for cluster in self.ecs_client.list_clusters()["clusterArns"]:
                self._clusters.append(cluster.split("/").pop())
        return self._clusters
                

    @property
    def ecs_client(self) -> ECSClient:
        if not hasattr(self, "_ecs_client"):
            self._ecs_client = boto3.client("ecs")
        return self._ecs_client
    
    def get_tasks(self, cluster):
        paginator = self.ecs_client.get_paginator("list_tasks")
        task_arns = []
        for page in paginator.paginate(
            cluster=cluster
        ):
            task_arns = task_arns + page["taskArns"]
        return task_arns

    def get_task_descriptions(self, cluster):
        task_arns = self.get_tasks(cluster)
        descriptions = self.ecs_client.describe_tasks(
            cluster=cluster,
            tasks=task_arns
        )
        return descriptions["tasks"]

    def show_service_ips(self, cluster=None, ip_filter=None):
        if cluster:
            clusters = [cluster]
        else:
            clusters = self.clusters
        services = {}
        for cluster in clusters:
            for task in self.get_task_descriptions(cluster):
                for attachment in task["attachments"]:
                    if attachment["type"] == "ElasticNetworkInterface":
                        for detail in attachment["details"]:
                            if detail["name"] == "privateIPv4Address":                                
                                if (not ip_filter) or detail["value"] in ip_filter:
                                    if task["group"] not in services:
                                        services[task["group"]] = {}
                                    services[task["group"]] = {
                                        "task_arn": task["taskArn"],
                                        "ip_address": detail["value"]
                                    }
        return services


        

class EcsScaler:
    def __init__(self, environment) -> None:
        self.environment = environment

    @property
    def ecs_client(self):
        if not hasattr(self, "_ecs_client"):
            self._ecs_client = boto3.client("ecs")
        return self._ecs_client
    
    def get_ecs_clusters(self):
        clusters = self.ecs_client.describe_clusters(
            clusters=self.ecs_client.list_clusters()["clusterArns"],
            include=["TAGS"]
        )

        return [cluster for cluster in clusters["clusters"] if {"key": "Environment", "value": self.environment} in cluster["tags"]]
    
    def get_services(self):
        services = {}
        for cluster in self.get_ecs_clusters():
            if cluster["clusterArn"] not in services:
                services[cluster["clusterArn"]] = {}
            paginator = self.ecs_client.get_paginator('list_services')
            response_iterator = paginator.paginate(
                cluster=cluster["clusterArn"],                    
            )
            for page in response_iterator:
                for service in page["serviceArns"]:
                    service_data = self.ecs_client.describe_services(
                        services=page["serviceArns"], 
                        cluster=cluster["clusterArn"],
                        include=["TAGS"]
                    )
                    for service in service_data["services"]:
                        services[cluster["clusterArn"]][service["serviceArn"]] = service

        return services

    def scale_down(self):
        services = self.get_services()
        for cluster_arn, services in services.items():
            for service_arn, service in services.items():
                desired_count = str(service["desiredCount"])
                if int(desired_count) > 0:
                    self.ecs_client.tag_resource(resourceArn=service_arn, tags=[
                        {
                            "key": "downscaler_desired_count",
                            "value": desired_count
                        },
                        {
                            "key": "downscaler_scaled_down_at",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ])
                    self.ecs_client.update_service(service=service_arn, cluster=cluster_arn, desiredCount=0)
                    click.echo(f"Scaled down {service_arn} from {desired_count}")
    
    def scale_up(self):
        services = self.get_services()
        for cluster_arn, services in services.items():
            for service_arn, service in services.items():
                try:
                    desired_count = self.serviceTagsDict(service)["downscaler_desired_count"]
                    self.ecs_client.tag_resource(resourceArn=service_arn, tags=[
                        {
                            "key": "downscaler_scaled_up_at",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ])
                    self.ecs_client.update_service(service=service_arn, cluster=cluster_arn, desiredCount=int(desired_count))
                    click.echo(f"Scaled up {service_arn} to {desired_count}")
                except KeyError:
                    pass

    def serviceTagsDict(self, service):
        return {tag["key"]: tag["value"] for tag in service["tags"]}