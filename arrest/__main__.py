import enum
import sys
from argparse import Namespace
from pathlib import Path
from typing import Optional, Sequence

import argcomplete

from arrest.cli.arguments import arg_parser
from arrest.openapi.parser import OpenAPIGenerator


class Exit(enum.Enum):
    """Exit reasons."""

    OK = 0
    ERROR = 1
    KeyboardInterrupt = 2


def main(args: Optional[Sequence[str]] = None):
    namespace = Namespace()
    argcomplete.autocomplete(arg_parser)

    arg_parser.parse_args(namespace=namespace)

    if args is None:  # pragma: no cover
        args = sys.argv[1:]

    output = Path().resolve(namespace.output)
    use_pydantic_v2 = namespace.pydantic == "v2"

    try:
        generator = OpenAPIGenerator(
            openapi_path=namespace.url,
            output_path=output,
            dir_name=namespace.dir,
            use_pydantic_v2=use_pydantic_v2,
        )
        generator.generate_schema()
        return Exit.OK
    except Exception:
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return Exit.ERROR


if __name__ == "__main__":
    sys.exit(main())
