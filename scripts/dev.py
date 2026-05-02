import os
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print(f"\n>>> {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def get_venv_python():
    if os.name == "nt":
        return ".venv\\Scripts\\python.exe"
    return ".venv/bin/python"


def main():
    print("🔥 Iniciando entorno de desarrollo")

    python_bin = get_venv_python()

    # Validar que existe
    if not Path(python_bin).exists():
        print("❌ No se encontró el entorno virtual. Ejecuta primero setup.py")
        sys.exit(1)

    os.environ["PYTHONPATH"] = "."

    run(f"{python_bin} -m scripts.cli init-db")
    run(f"{python_bin} -m scripts.cli once --source wallapop")
    run(f"{python_bin} -m scripts.cli serve --reload")


if __name__ == "__main__":
    main()
