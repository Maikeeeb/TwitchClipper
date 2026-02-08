import os
import shutil
import sys

from webdriver_manager.firefox import GeckoDriverManager


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    backend_dir = os.path.join(repo_root, "backend")
    os.makedirs(backend_dir, exist_ok=True)

    driver_path = GeckoDriverManager().install()
    driver_name = "geckodriver.exe" if os.name == "nt" else "geckodriver"
    target_path = os.path.join(backend_dir, driver_name)

    shutil.copy(driver_path, target_path)
    print(f"Geckodriver installed at: {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
