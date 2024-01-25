from argparse import ArgumentParser

arg_parser = ArgumentParser(
    usage="\n arrest [options]",
    description="generate arrest services and resources from various definitions",
    add_help=True,
)

arg_parser.add_argument(
    "-o", "--output", default=None, help="output directory for generated files (default: ./api)"
)

arg_parser.add_argument("--pydantic", choices=["v1", "v2"], default="v1")
arg_parser.add_argument("-u", "--url", required=True, help="HTTP or file url for the openapi schema")
arg_parser.add_argument("-d", "--dir", default=None)
