#!/usr/bin/env bash
set -euox pipefail

uv run black --check .
uv run flake8 .
uv run isort --check-only --diff tests
