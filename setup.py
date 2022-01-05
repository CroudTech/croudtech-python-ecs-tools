from setuptools import setup
import os

VERSION = "0.1.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="croudtech-ecs-tools",
    description="Tools for managing ECS Services and Tasks",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Jim Robinson",
    url="https://github.com/CroudTech/croudtech-ecs-tools",
    project_urls={
        "Issues": "https://github.com/CroudTech/croudtech-ecs-tools/issues",
        "CI": "https://github.com/CroudTech/croudtech-ecs-tools/actions",
        "Changelog": "https://github.com/CroudTech/croudtech-ecs-tools/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["croudtech_ecs_tools"],
    entry_points="""
        [console_scripts]
        croudtech-ecs-tools=croudtech_ecs_tools.cli:cli
    """,
    install_requires=[
        "boto3==1.20.28",
        "botocore==1.23.28; python_version >= '3.6'",
        "click==8.0.3",
        "jmespath==0.10.0; python_version >= '2.6' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "s3transfer==0.5.0; python_version >= '3.6'",
        "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "urllib3==1.26.7; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4' and python_version < '4'",
    ],
    extras_require={
        "test": ["pytest"]
    },
    python_requires=">=3.8",
)
