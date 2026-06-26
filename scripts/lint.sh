#!/usr/bin/env bash
set -euox pipefail

if [[ "${1:-}" == "--fix" ]]; then
    uv run ruff check --fix .
    uv run ruff format .
else
    uv run ruff check .
    uv run ruff format --check
fi
