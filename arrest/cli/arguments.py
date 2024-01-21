from argparse import ArgumentParser

from arrest.defaults import OPENAPI_SCHEMA_FILENAME
from arrest.defaults import OPENAPI_SERVICE_FILENAME


arg_parser = ArgumentParser(
    usage="\n arrest [options]",
    description="generate arrest services and resources from various definitions",
    add_help=False,
)

arg_parser.add_argument(
    "-o", "--output", default=None, help="output directory for generated files (default: ./api)"
)

arg_parser.add_argument("--pydantic-version", choices=["v1", "v2"])

arg_parser.add_argument("--model-filename", default=OPENAPI_SCHEMA_FILENAME)
arg_parser.add_argument("--service-filename", default=OPENAPI_SERVICE_FILENAME)
arg_parser.add_argument("-v", "--verbose", action="store_false", default=None)
