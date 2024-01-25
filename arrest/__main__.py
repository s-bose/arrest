import sys
import asyncio
from pathlib import Path
from argparse import Namespace
import argcomplete
from arrest.openapi.parser import OpenAPIGenerator
from arrest.cli.arguments import arg_parser


def main():
    loop = asyncio.new_event_loop()

    namespace = Namespace()
    argcomplete.autocomplete(arg_parser)

    arg_parser.parse_args(namespace=namespace)
    output = Path().resolve(namespace.output)

    generator = OpenAPIGenerator(openapi_path=namespace.url, output_path=output, dir_name=namespace.dir)
    loop.run_until_complete(generator.generate_schema())
    loop.close()


if __name__ == "__main__":
    sys.exit(main())
