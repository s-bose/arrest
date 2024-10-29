#!/usr/bin/env bash
set -euox pipefail

rm -rf .tox
[ -e .coverage ] && rm .coverage

tox
coverage report --show-missing
coverage html
coverage xml
