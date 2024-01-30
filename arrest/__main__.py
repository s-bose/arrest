import sys
from argparse import Namespace
from pathlib import Path
from typing import Optional, Sequence

import argcomplete

from arrest.common import Exit
from arrest.logging import logger

try:
    import datamodel_code_generator
    import jinja2
except ImportError:
    logger.warning("Dependencies missing. Please install extra dependencies by `pip install arrest[openapi]`")
    sys.exit(Exit.ERROR)

from arrest.cli.arguments import arg_parser
from arrest.openapi.parser import OpenAPIGenerator


def main(args: Optional[Sequence[str]] = None):
    namespace = Namespace()
    argcomplete.autocomplete(arg_parser)

    if args is None:  # pragma: no cover
        args = sys.argv[1:]

    _, unknown_args = arg_parser.parse_known_args(args, namespace=namespace)

    if unknown_args:
        print("unrecognized arguments: {}".format(" ".join(unknown_args)))
        arg_parser.print_help(file=sys.stdout)
        return Exit.ERROR

    if not args:
        arg_parser.print_help(file=sys.stdout)
        return Exit.ERROR

    if not namespace.url:
        print("Missing `--url`. An http or file url needs to be specified", file=sys.stdout)
        arg_parser.print_help(file=sys.stdout)
        return Exit.ERROR

    if not (output := namespace.output):
        output = Path().resolve(namespace.output)
        print(f"No output path specified. Using current directory {output!s}", file=sys.stdout)

    use_pydantic_v2 = namespace.pydantic == "v2"

    try:
        generator = OpenAPIGenerator(
            url=namespace.url,
            output_path=output,
            dir_name=namespace.dir,
            use_pydantic_v2=use_pydantic_v2,
        )

        generator.generate_schema()
        print("Files generated successfully", file=sys.stdout)
        return Exit.OK

    except Exception:
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return Exit.ERROR


if __name__ == "__main__":
    sys.exit(main())
