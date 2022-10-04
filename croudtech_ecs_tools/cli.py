from email.policy import default
import click
import boto3
from botocore.config import Config as Boto3Config
from click.decorators import command
from click.termui import prompt
import os
from croudtech_ecs_tools.ecs import Ecs
import json



class EcsTools:
    _services = {}
    _tasks = {}

    def __init__(self, region):
        self.region = region
        print(self.region)
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
    
    def extractFromArn(self, arn):
        arn_parts = arn.split(":")[-1].split("/")[1:]
        return arn_parts

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

    def restart_service(self, service_arn, wait=False):
        try:
            cluster, service = self.extractFromArn(service_arn)
        except ValueError as err:
            click.echo(f"Invalid service ARN {service_arn}")
            return
        waiter = self.ecs_client.get_waiter('services_stable')
        
        self.ecs_client.update_service(
            cluster=cluster,
            service=service,
            forceNewDeployment=True
        )
        if wait:
            waiter.wait(
                cluster=cluster,
                services=[
                    service,
                ],            
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': 100
                }
            )
        return True

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

@click.group()
@click.version_option()
def cli():
    "Tools for managing ECS Services and Tasks"


@cli.command()
@click.option("--region", required=True, default=os.getenv("AWS_DEFAULT_REGION", "eu-west-2"))
@click.option("--command", default="bash")
def ecs_shell(region, command):
    ecs_tools = EcsTools(region)

    "Shell into an ECS task container"
    click.secho(ecs_tools.get_cluster_options(), fg="cyan")
    cluster = ecs_tools.clusters[int(click.prompt("Please select a cluster"))]

    click.secho(ecs_tools.get_service_options(cluster), fg="cyan")
    service_arn = ecs_tools.get_services(cluster)[int(click.prompt("Please select a service"))]

    click.secho(ecs_tools.get_task_options(cluster, service_arn), fg="cyan")
    task_arn = ecs_tools.get_tasks(cluster, service_arn)[int(click.prompt("Please select a task"))]

    click.echo(ecs_tools.get_task__container_options(cluster, task_arn))
    container = ecs_tools.get_task_containers(cluster, task_arn)[int(click.prompt("Please select a container"))]["name"]
    click.secho("Connecting to  Cluster:" + cluster + " Service:" + service_arn.split("/").pop() + " Task:" + task_arn.split("/").pop() + " Container: " + container, fg="green" )
    task_id = task_arn.split("/").pop()
    command = f"aws ecs execute-command --cluster {cluster} --task {task_id} --container {container} --interactive --command {command}"
    click.secho("Executing command", fg="green")
    click.secho(command, fg="cyan")
    os.system(command)

@cli.command()
@click.option("--region", required=True, default=os.getenv("AWS_DEFAULT_REGION", "eu-west-2"))
@click.option('--wait/--no-wait', default=False, help="Wait for service to become stable before exiting")
@click.argument("service_arn", required=False)
def restart_service(region, wait, service_arn):
    ecs_tools = EcsTools(region)
    if not service_arn: 
        
        click.secho(ecs_tools.get_cluster_options(), fg="cyan")
        cluster = ecs_tools.clusters[int(click.prompt("Please select a cluster"))]

        click.secho(ecs_tools.get_service_options(cluster), fg="cyan")
        service_arn = ecs_tools.get_services(cluster)[int(click.prompt("Please select a service"))]
    
    click.echo(f"Restarting ARN: {service_arn}")
    ecs_tools.restart_service(service_arn, wait)
    if wait:
        click.echo(f"Service {service_arn} restarted")


@cli.command()
@click.option("--cluster", required=True)
def list_service_discovery_endpoints(cluster):
    ecs_manager = Ecs(cluster=cluster)
    print(json.dumps(ecs_manager.list_ecs_service_endpoints(), indent=2, default=str))

if __name__ == "__main__":
    cli()