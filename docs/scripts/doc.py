#!/usr/bin/env python3
import tempfile
import pathlib
import subprocess
import sys
import shutil

from overture.schema.core.discovery import discover_models

MKDOCS_YML = """
site_name: Overture Schema

theme:
  name: material

plugins:
  - awesome-pages
  - search
  - mkdocstrings:
      handlers:
        python:
          import:
          - https://docs.pydantic.dev/latest/objects.inv
          options:
            show_source: true
            show_root_heading: true
            show_signature: true
            show_root_full_path: false
            show_object_full_path: false
            filters: []
            extensions:
            - griffe_pydantic:
                schema: true
"""

INDEX_TEMPLATE = """# {package}

::: {package}
"""

MODULE_TEMPLATE = """# {module}

::: {module}
"""

MODEL_TEMPLATE = """# {model}

::: {entry}
    options:
        show_submodules: true
"""

def generate_docs():
    temp_dir = tempfile.mkdtemp()
    docs_dir = pathlib.Path(temp_dir) / "docs"
    docs_dir.mkdir()

    (docs_dir / "index.md").write_text(
        pathlib.Path("PYDANTIC_GUIDE_MKDOCS.md").read_text()
    )

    for model, cls in discover_models().items():
        name = model.type
        theme = model.theme

        entry = cls.__module__ + "." + cls.__name__
        if theme:
            file = docs_dir / "schema" / f"{theme}" / f"{name}.md"
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(MODEL_TEMPLATE.format(model=name, entry=entry))

    mkdocs_yml = MKDOCS_YML

    (pathlib.Path(temp_dir) / "mkdocs.yml").write_text(mkdocs_yml)

    return temp_dir


def run(tool):
    temp_dir = generate_docs()

    try:
        subprocess.run(
            [tool, "serve"],
            cwd=temp_dir,
            check=True
        )
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: doc <tool>")
        sys.exit(1)

    run(sys.argv[1])