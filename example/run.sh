#!/usr/env/bin bash

. venv/bin/activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 --log-level info
