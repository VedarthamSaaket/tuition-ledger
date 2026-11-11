import argparse
from pathlib import Path

from . import dictionary


def main() -> None:
    parser = argparse.ArgumentParser(prog="ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dictionary", help="write the data dictionary")
    d.add_argument("--out", default="docs")
    args = parser.parse_args()
    if args.command == "dictionary":
        dictionary.write(Path(args.out))
        print(f"wrote {args.out}/data_dictionary.md and data_dictionary.csv")


if __name__ == "__main__":
    main()
