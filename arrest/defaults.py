import os

DEFAULT_TIMEOUT = int(os.getenv("ARREST_DEFAULT_TIMEOUT", "60"))  # sec
MAX_RETRIES = int(os.getenv("ARREST_MAX_RETRIES", "3"))

OPENAPI_SCHEMA_FILENAME = "models.py"
SERVICE_FILENAME = "service.py"
RESOURCE_FILENAME = "resources.py"
OPENAPI_DIRECTORY = "api"
