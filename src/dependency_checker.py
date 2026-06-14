from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
import sys


IMPORT_NAME_OVERRIDES = {
    "pillow": "PIL",
}


def ensure_requirements(requirements_path: Path) -> None:
    missing = find_missing_requirements(requirements_path)
    if not missing:
        return

    names = ", ".join(missing)
    print(f"缺少依赖：{names}")
    print("正在使用当前 Python 环境安装 requirements.txt 中的依赖...")
    command = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    try:
        subprocess.check_call(command)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"依赖安装失败，请手动运行：{' '.join(command)}\n错误：{exc}") from exc

    still_missing = find_missing_requirements(requirements_path)
    if still_missing:
        names = ", ".join(still_missing)
        raise SystemExit(f"依赖安装后仍缺少：{names}")


def find_missing_requirements(requirements_path: Path) -> list[str]:
    return [
        requirement
        for requirement in read_requirement_names(requirements_path)
        if importlib.util.find_spec(import_name_for_requirement(requirement)) is None
    ]


def read_requirement_names(requirements_path: Path) -> list[str]:
    if not requirements_path.exists():
        return []

    names: list[str] = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-") or "://" in line:
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)", line)
        if match:
            names.append(match.group(1))
    return names


def import_name_for_requirement(requirement: str) -> str:
    normalized = requirement.lower().replace("_", "-")
    return IMPORT_NAME_OVERRIDES.get(normalized, requirement.replace("-", "_"))
