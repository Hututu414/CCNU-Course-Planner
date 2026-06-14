from pathlib import Path

from src.dependency_checker import ensure_requirements


if __name__ == "__main__":
    ensure_requirements(Path(__file__).with_name("requirements.txt"))
    from src.app import run_app

    run_app()
