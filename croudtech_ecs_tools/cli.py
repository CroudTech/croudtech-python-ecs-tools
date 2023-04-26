from email.policy import default
import click
import boto3
from botocore.config import Config as Boto3Config
from click.decorators import command
from click.termui import prompt
import os
from croudtech_ecs_tools.ecs import Ecs, EcsScaler, ServiceInfo, EcsTools
from croudtech_ecs_tools.cloudfront import Cloudfront
import json


@click.group()
@click.version_option()
def cli():
    "Tools for managing ECS Services and Tasks"

@cli.group()
@click.version_option()
def ecs():
    "Tools for managing ECS Services and Tasks"


@ecs.command()
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

@ecs.command()
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


@ecs.command()
@click.option("--cluster", required=True)
def list_service_discovery_endpoints(cluster):
    ecs_manager = Ecs(cluster=cluster)
    print(json.dumps(ecs_manager.list_ecs_service_endpoints(), indent=2, default=str))

@ecs.command()
@click.option("--cluster", required=False)
@click.option("--ip-filter", multiple=True)
def show_service_ips(cluster=None, ip_filter=None):
    service_info = ServiceInfo()
    print(json.dumps(service_info.show_service_ips(cluster, ip_filter), indent=2, default=str))

@ecs.command()
@click.argument("environment")
def scale_up(environment):
    ecs_scaler = EcsScaler(environment)
    ecs_scaler.scale_up()

@ecs.command()
@click.argument("environment")
def scale_down(environment):
    ecs_scaler = EcsScaler(environment)
    ecs_scaler.scale_down()

@cli.group()
@click.version_option()
def cloudfront():
    "Tools for managing Cloudfront Distributions"

@cloudfront.command()
@click.argument("environment")
@click.option("--paths", multiple=True)
def clear_cloudfront_cache(environment, paths):
    cloudfront_manager = Cloudfront()
    cloudfront_manager.clear_cache(environment, paths)

if __name__ == "__main__":
    cli()
