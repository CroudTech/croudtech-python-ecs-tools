import click
import os
from .ecs_tools import EcsTools
from .ecr_tools import EcrTools

@click.group()
@click.version_option()
def cli():
    "Tools for managing ECS Services and Tasks"


@cli.command()
@click.option("--region", required=True, default=os.getenv("AWS_DEFAULT_REGION", "eu-west-2"))
def ecs_shell(region):
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
    command = f"aws ecs execute-command --cluster {cluster} --task {task_id} --container {container} --interactive --command bash"
    click.secho("Executing command", fg="green")
    click.secho(command, fg="cyan")
    os.system(command)

@cli.group()
def ecr():
    "Tools for managing ECR Repositories"

@ecr.command()
@click.option("--region", required=True, default=os.getenv("AWS_DEFAULT_REGION", "eu-west-2"))
@click.option("--days", required=True, default=30)

def find_stale_images(region, days):
    ecr_tools = EcrTools(region, click)
    ecr_tools.findStaleImages(days)

if __name__ == "__main__":
    cli()