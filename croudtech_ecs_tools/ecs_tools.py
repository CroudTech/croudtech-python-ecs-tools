import boto3
from botocore.config import Config as Boto3Config

class EcsTools:
    _services = {}
    _tasks = {}

    def __init__(self, region):
        self.region = region
        self.ecs_client = boto3.client("ecs", config=Boto3Config(
            region_name= self.region
        ))

    @property
    def clusters(self):
        if not hasattr(self, "_clusters"):
            paginator = self.ecs_client.get_paginator("list_clusters")
            response_iterator = paginator.paginate(
                PaginationConfig={
                    "PageSize": 10,
                }
            )
            self._clusters = []
            for page in response_iterator:
                for cluster in page["clusterArns"]:
                    self._clusters.append(cluster.split("/").pop())
            
        return self._clusters
    
    def get_services(self, cluster):
        if cluster not in self._services:
            self._services[cluster] = []
            paginator = self.ecs_client.get_paginator("list_services")

            response_iterator = paginator.paginate(
                cluster=cluster,           
                PaginationConfig={
                    "PageSize": 50,
                }
            )
            for page in response_iterator:
                for service in page["serviceArns"]:
                    self._services[cluster].append(service)
        return self._services[cluster]

    def get_tasks(self, cluster, service):
        task_key = cluster+service
        if task_key not in self._tasks:
            self._tasks[task_key] = []
            paginator = self.ecs_client.get_paginator("list_tasks")
            response_iterator = paginator.paginate(
                cluster=cluster,
                serviceName=service,           
                PaginationConfig={
                    "PageSize": 50,
                }
            )
            for page in response_iterator:
                for task in page["taskArns"]:
                    self._tasks[task_key].append(task)
        return self._tasks[task_key]

    def describe_task(self, cluster, task_arn):
        response = self.ecs_client.describe_tasks(
            cluster=cluster,
            tasks=[
                task_arn,
            ],            
        )
        task = response["tasks"].pop()
        return task

    def execute_command(self,cluster, container, task_arn, command="bash"):
        return self.ecs_client.execute_command(
            cluster=cluster,
            container=container["name"],
            command=command,
            interactive=True,
            task=task_arn
        )

    def get_task_containers(self, cluster, task_arn):
        return self.describe_task(cluster, task_arn)["containers"]
    
    def get_service_options(self, cluster):
        options = []
        for index, option in enumerate(self.get_services(cluster)):
            option_name = option.split("/").pop()
            options.append(f"{index}: {option_name}")
        return "\n".join(options)

    def get_task_options(self, cluster, service):
        options = []
        for index, option in enumerate(self.get_tasks(cluster, service)):
            option_name = option.split("/").pop()
            options.append(f"{index}: {option_name}")
        return "\n".join(options)

    def get_task__container_options(self, cluster, task_arn):
        options = []
        for index, option in enumerate(self.get_task_containers(cluster, task_arn)):
            option_name = option["name"]
            options.append(f"{index}: {option_name}")
        return "\n".join(options)

    def get_cluster_options(self):
        options = []
        for index, option in enumerate(self.clusters):
            options.append(f"{index}: {option}")
        return "\n".join(options)


