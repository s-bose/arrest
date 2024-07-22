#!/usr/bin/env bash
set -euox pipefail

find . -name '*.pyc' -delete
find . -name '__pycache__' -delete