from setuptools import setup
import os

VERSION = os.getenv("SEMVER", os.getenv("GitVersion_FullSemVer", "dev"))

with open(os.path.join(os.getcwd(), "requirements.txt")) as f:
    required = f.read().splitlines()


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
    install_requires=required,
    extras_require={
        "test": ["pytest"]
    },
    python_requires=">=3.8",
)
