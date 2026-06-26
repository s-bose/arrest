#!/usr/bin/env bash
set -euox pipefail

uv run pytest -vvv $@
