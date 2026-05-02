import os
import subprocess
import sys


def run(cmd):
    print(f"\n>>> {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main():
    print("🚀 Setup Market Analyzer")

    # 1. Crear venv si no existe
    if not os.path.exists(".venv"):
        run(f"{sys.executable} -m venv .venv")

    # 2. Detectar python del venv
    if os.name == "nt":
        python_bin = ".venv\\Scripts\\python.exe"
    else:
        python_bin = ".venv/bin/python"

    # 3. Instalar dependencias
    run(f"{python_bin} -m pip install --upgrade pip")
    run(f"{python_bin} -m pip install -r requirements.txt")

    # 4. Instalar proyecto editable
    run(f"{python_bin} -m pip install -e .")

    # 5. Instalar playwright browsers
    run(f"{python_bin} -m playwright install chromium firefox")

    # 6. Crear .env si no existe
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""MARKET_ANALYZER_DB_URL=sqlite:///./data/app.db
MARKET_ANALYZER_RUNTIME_INTERVAL=180
MARKET_ANALYZER_LOG_LEVEL=INFO
MARKET_ANALYZER_BROWSER=chromium
MARKET_ANALYZER_BROWSER_FALLBACK=firefox
MARKET_ANALYZER_BROWSER_HEADLESS=true
""")
        print("✅ .env creado")

    print("\n✅ Setup completo")


if __name__ == "__main__":
    main()
