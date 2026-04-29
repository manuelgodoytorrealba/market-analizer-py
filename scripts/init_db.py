import sys

from scripts.cli import main as cli_main


if __name__ == "__main__":
    raise SystemExit(cli_main(["init-db", *sys.argv[1:]]))
