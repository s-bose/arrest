import sys
from pathlib import Path


def main():
    print(Path().resolve())


if __name__ == "__main__":
    sys.exit(main())
