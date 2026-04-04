import sys

from scripts.cli import main as cli_main


def main() -> None:
    raise SystemExit(cli_main(["runtime", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
