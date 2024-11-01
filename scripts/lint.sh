#!/usr/bin/env bash
set -euox pipefail

poetry run black --check .
poetry run flake8 .
isort --check-only --diff tests