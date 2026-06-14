from pathlib import Path

from src.dependency_checker import import_name_for_requirement, read_requirement_names, read_requirement_specs, requirement_name


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


def test_read_requirement_specs_keep_version_specifiers(tmp_path: Path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pandas>=2\npillow==11.3.0\n", encoding="utf-8")

    assert read_requirement_specs(requirements) == ["pandas>=2", "pillow==11.3.0"]
    assert requirement_name("pandas>=2") == "pandas"
