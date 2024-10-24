from contextvars import ContextVar

from arrest._config import ArrestConfig

__arrest_ctx = ContextVar[ArrestConfig]("__arrest_ctx")


DEFAULT_TIMEOUT = 120  # sec
MAX_RETRIES = 3
ROOT_RESOURCE = "root"

OPENAPI_SCHEMA_FILENAME = "models.py"
SERVICE_FILENAME = "service.py"
RESOURCE_FILENAME = "resources.py"
OPENAPI_DIRECTORY = "api"

# ARREST_CONFIG: ArrestConfig =
