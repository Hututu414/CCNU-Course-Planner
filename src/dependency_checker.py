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

    names = ", ".join(requirement_name(spec) for spec in missing)
    print(f"缺少依赖：{names}")
    print(f"当前 Python：{sys.executable}")
    print("正在使用当前 Python 环境安装缺少的依赖...")
    command = [sys.executable, "-m", "pip", "install", *missing]
    try:
        subprocess.check_call(command)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"依赖安装失败，请手动运行：{' '.join(command)}\n错误：{exc}") from exc

    still_missing = find_missing_requirements(requirements_path)
    if still_missing:
        names = ", ".join(requirement_name(spec) for spec in still_missing)
        raise SystemExit(f"依赖安装后仍缺少：{names}")


def find_missing_requirements(requirements_path: Path) -> list[str]:
    return [
        spec
        for spec in read_requirement_specs(requirements_path)
        if importlib.util.find_spec(import_name_for_requirement(requirement_name(spec))) is None
    ]


def read_requirement_names(requirements_path: Path) -> list[str]:
    return [requirement_name(spec) for spec in read_requirement_specs(requirements_path)]


def read_requirement_specs(requirements_path: Path) -> list[str]:
    if not requirements_path.exists():
        return []

    specs: list[str] = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-") or "://" in line:
            continue
        specs.append(line)
    return specs


def requirement_name(requirement_spec: str) -> str:
    match = re.match(r"([A-Za-z0-9_.-]+)", requirement_spec)
    return match.group(1) if match else requirement_spec


def import_name_for_requirement(requirement: str) -> str:
    normalized = requirement.lower().replace("_", "-")
    return IMPORT_NAME_OVERRIDES.get(normalized, requirement.replace("-", "_"))
