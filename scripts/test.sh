#!/usr/bin/env bash
set -euox pipefail

poetry run pytest -vvv $@