import boto3
from mypy_boto3_ecs.type_defs import ServiceTypeDef
from mypy_boto3_servicediscovery.type_defs import NamespaceTypeDef
from typing import List
import json

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
                self._ecs_service_endpoints[hostname] = sd["Service"]["Name"]

        return self._ecs_service_endpoints

