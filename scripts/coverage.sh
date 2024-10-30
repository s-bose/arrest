#!/usr/bin/env bash
set -euox pipefail

rm -rf .tox
[ -e .coverage ] && rm .coverage

poetry run tox
