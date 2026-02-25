"""Tests for CLI entrypoint."""

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner
from overture.schema.codegen.cli import cli
from overture.schema.codegen.specs import ModelSpec


class TestCliList:
    """Tests for the list command."""

    def test_list_command_exists(self, cli_runner: CliRunner) -> None:
        """list command should be available."""
        result = cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0

    def test_list_shows_discovered_models(self, cli_runner: CliRunner) -> None:
        """list command should show discovered models."""
        result = cli_runner.invoke(cli, ["list"])

        assert "Building" in result.output
        assert "Place" in result.output


class TestCliGenerate:
    """Tests for the generate command."""

    def test_generate_command_exists(self, cli_runner: CliRunner) -> None:
        """generate command should be available."""
        result = cli_runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Generate" in result.output or "generate" in result.output

    def test_generate_requires_format(self, cli_runner: CliRunner) -> None:
        """generate command should require --format."""
        result = cli_runner.invoke(cli, ["generate"])
        assert result.exit_code != 0

    def test_generate_markdown_to_stdout(self, cli_runner: CliRunner) -> None:
        """generate --format markdown should output markdown to stdout."""
        result = cli_runner.invoke(cli, ["generate", "--format", "markdown"])

        assert result.exit_code == 0
        assert "# Building" in result.output or "# " in result.output

    def test_generate_with_theme_filter(self, cli_runner: CliRunner) -> None:
        """generate --theme should filter to specific theme."""
        result = cli_runner.invoke(
            cli, ["generate", "--format", "markdown", "--theme", "buildings"]
        )

        assert result.exit_code == 0
        assert "Building" in result.output
        assert "Place" not in result.output

    def test_generate_markdown_feature_at_theme_level(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Markdown features go directly in theme directory."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "buildings",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        # Feature models at theme level
        assert (tmp_path / "buildings" / "building.md").exists()
        assert (tmp_path / "buildings" / "building_part.md").exists()

        # NOT in subdirectories
        assert not (tmp_path / "buildings" / "building" / "building.md").exists()

    def test_feature_pages_have_sidebar_position(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Feature pages include sidebar_position frontmatter."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "buildings",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        content = (tmp_path / "buildings" / "building.md").read_text()
        assert content.startswith("---\nsidebar_position: 1\n---\n")

    def test_generate_markdown_shared_types_mirror_modules(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Core/system types land in module-mirrored directories."""
        result = cli_runner.invoke(
            cli,
            ["generate", "--format", "markdown", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0

        core_dir = tmp_path / "core"
        assert core_dir.exists(), "core/ directory should exist"
        subdirs = [d.name for d in core_dir.iterdir() if d.is_dir()]
        assert len(subdirs) > 0, "core/ should have subdirectories"

    def test_generate_multiple_themes_to_output_dir(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """generate all themes should create subdirectories for each theme."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        subdirs = [d.name for d in tmp_path.iterdir() if d.is_dir()]
        assert "buildings" in subdirs
        assert "places" in subdirs

    def test_generate_no_duplicate_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """No type should produce duplicate output files."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        all_files = list(tmp_path.rglob("*.md"))
        all_paths = [str(f.relative_to(tmp_path)) for f in all_files]
        assert len(all_paths) == len(set(all_paths)), (
            f"Duplicate files: {[p for p in all_paths if all_paths.count(p) > 1]}"
        )


class TestCliGenerateLinkIntegrity:
    """Verify all markdown links resolve to existing files."""

    def test_all_links_resolve(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Every markdown link target should exist as a file."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        link_re = re.compile(r"\[.*?\]\(([^)]+\.md(?:#[^)]*)?)\)")
        broken: list[str] = []

        for md_file in tmp_path.rglob("*.md"):
            content = md_file.read_text()
            for match in link_re.finditer(content):
                href = match.group(1).split("#")[0]
                # Resolve relative path from the file's directory
                target = (md_file.parent / href).resolve()
                if not target.exists():
                    rel = md_file.relative_to(tmp_path)
                    broken.append(f"{rel}: {href}")

        assert not broken, "Broken links:\n" + "\n".join(broken)


class TestCliGenerateCategoryFiles:
    """Tests for _category_.json generation."""

    def test_generates_category_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Should generate _category_.json files in output directories."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "buildings",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        # Theme directory should have a category file
        cat_file = tmp_path / "buildings" / "_category_.json"
        assert cat_file.exists()
        data = json.loads(cat_file.read_text())
        assert data["label"] == "Buildings"

    def test_core_directory_has_category_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """core/ directory should have _category_.json."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        cat_file = tmp_path / "core" / "_category_.json"
        assert cat_file.exists()
        data = json.loads(cat_file.read_text())
        assert data["label"] == "Core"

    def test_feature_dirs_positioned_before_non_feature_dirs(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Feature directories should have lower position than non-feature directories."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        def pos(dir_name: str) -> int:
            data = json.loads((tmp_path / dir_name / "_category_.json").read_text())
            result: int = data["position"]
            return result

        # Feature directories (contain feature pages) should sort before
        # non-feature directories (core, system -- shared types only)
        feature_positions = [pos("buildings"), pos("places"), pos("transportation")]
        non_feature_positions = [pos("core"), pos("system")]

        assert max(feature_positions) < min(non_feature_positions)

    def test_subdirectories_have_no_position(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Only top-level directories get position values."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        data = json.loads(
            (tmp_path / "core" / "scoping" / "_category_.json").read_text()
        )
        assert "position" not in data


class TestCliGenerateEnums:
    """Tests for enum generation in the generate command."""

    def test_generate_markdown_includes_enum_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """generate --format markdown should create enum documentation files."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "buildings",
                "--output-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0

        # Enum files exist somewhere under the buildings directory
        all_md = list((tmp_path / "buildings").rglob("*.md"))
        all_names = [f.stem for f in all_md]

        assert "building" in all_names

        # Should have enum files beyond the feature models
        non_feature = [n for n in all_names if n not in ("building", "building_part")]
        assert len(non_feature) > 0, "Should generate enum documentation files"


class TestCliEntryPoint:
    """generate populates entry_point from discovery keys."""

    def test_generate_sets_entry_point_on_specs(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: list[ModelSpec] = []

        def spy(feature_specs: list, schema_root: str, output_dir: object) -> None:
            captured.extend(feature_specs)

        monkeypatch.setattr("overture.schema.codegen.cli._generate_markdown", spy)
        result = cli_runner.invoke(
            cli, ["generate", "--format", "markdown", "--theme", "buildings"]
        )

        assert result.exit_code == 0
        assert len(captured) > 0
        for spec in captured:
            assert spec.entry_point is not None, f"{spec.name} missing entry_point"
            assert ":" in spec.entry_point, (
                f"entry_point should be entry-point style: {spec.entry_point!r}"
            )


class TestCliHelp:
    """Tests for CLI help."""

    def test_main_help(self, cli_runner: CliRunner) -> None:
        """--help should show usage information."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "generate" in result.output
        assert "list" in result.output


class TestGenerateWithSegment:
    """Integration test: Segment union produces markdown output."""

    def test_segment_appears_in_markdown_output(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Generate markdown and verify Segment page exists."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "transportation",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        # Segment page should exist
        segment_files = list(tmp_path.rglob("segment.md"))
        assert len(segment_files) >= 1, f"No segment.md found in {tmp_path}"

        content = segment_files[0].read_text()
        assert "# Segment" in content
        assert "subtype" in content


class TestReverseReferences:
    """Integration test: Reverse references appear in generated markdown."""

    def test_used_by_sections_appear_in_markdown(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Generate markdown and verify Used By sections appear."""
        result = cli_runner.invoke(
            cli,
            [
                "generate",
                "--format",
                "markdown",
                "--theme",
                "buildings",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

        # Find a supplementary type that should have Used By section
        # For example, if Building references some enum or NewType
        all_md = list(tmp_path.rglob("*.md"))

        # At least one supplementary type should have a Used By section
        has_used_by = False
        for md_file in all_md:
            content = md_file.read_text()
            if "## Used By" in content:
                has_used_by = True
                break

        assert has_used_by, "No 'Used By' sections found in any generated markdown"
