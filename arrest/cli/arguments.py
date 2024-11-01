from argparse import ArgumentParser

from arrest import __version__

arg_parser = ArgumentParser(
    usage="\n arrest [options]",
    description="generate arrest services and resources from various definitions",
    add_help=True,
)

arg_parser.add_argument(
    "-v",
    "--version",
    action="version",
    version="%(prog)s {version}".format(version=__version__),
    help="display the current package version",
)

arg_parser.add_argument(
    "-o", "--output", default=None, help="output directory for generated files (default: ./api)"
)

arg_parser.add_argument(
    "--pydantic",
    choices=["v1", "v2"],
    default="v1",
    help="pydantic version to generate the schema definitions",
)
arg_parser.add_argument("-u", "--url", default=None, help="HTTP or file url for the openapi schema")
arg_parser.add_argument("-d", "--dir", default=None, help="Directory containing the files")
