from pathlib import Path

from src.dependency_checker import import_name_for_requirement, read_requirement_names


def test_import_name_override_for_pillow():
    assert import_name_for_requirement("pillow") == "PIL"


def test_read_requirement_names_ignores_comments_and_options(tmp_path: Path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "# comment",
                "pandas>=2",
                "openpyxl # workbook reader",
                "-r other.txt",
                "https://example.com/pkg.whl",
            ]
        ),
        encoding="utf-8",
    )

    assert read_requirement_names(requirements) == ["pandas", "openpyxl"]
