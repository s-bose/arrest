#!/usr/bin/env bash
set -euox pipefail

rm -rf .tox
[ -e .coverage ] && rm .coverage

poetry run tox
poetry run coverage report --show-missing
poetry run coverage html
poetry run coverage xml
