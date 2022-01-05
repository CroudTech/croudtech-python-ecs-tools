# croudtech-ecs-tools

[![PyPI](https://img.shields.io/pypi/v/croudtech-ecs-tools.svg)](https://pypi.org/project/croudtech-ecs-tools/)
[![Changelog](https://img.shields.io/github/v/release/CroudTech/croudtech-ecs-tools?include_prereleases&label=changelog)](https://github.com/CroudTech/croudtech-ecs-tools/releases)
[![Tests](https://github.com/CroudTech/croudtech-ecs-tools/workflows/Test/badge.svg)](https://github.com/CroudTech/croudtech-ecs-tools/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/CroudTech/croudtech-ecs-tools/blob/master/LICENSE)

Tools for managing ECS Services and Tasks

## Installation

Install this tool using `pip`:

    $ pip install croudtech-ecs-tools

## Usage

Usage instructions go here.

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd croudtech-ecs-tools
    python -m venv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
