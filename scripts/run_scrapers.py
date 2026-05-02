import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (ROOT_DIR / ".venv").resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

from scripts.cli import main as cli_main


def main() -> None:
    raise SystemExit(cli_main(["once", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
