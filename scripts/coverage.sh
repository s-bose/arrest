#!/usr/bin/env bash
set -euox pipefail

rm -rf .tox
[ -e .coverage ] && rm .coverage

uv run pytest --cov=arrest --cov-report=term-missing --no-cov-on-fail
