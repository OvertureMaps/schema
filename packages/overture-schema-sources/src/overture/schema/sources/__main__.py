"""CLI module for validating Sources JSON files.

Usage:
    uv run python -m overture.schema.sources <json_file_path>
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .models import Sources


def main() -> None:
    """Main function for CLI validation."""
    if len(sys.argv) != 2:
        print(
            "Usage: uv run python -m overture.schema.sources <json_file_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    json_file_path = Path(sys.argv[1])

    if not json_file_path.exists():
        print(f"Error: File '{json_file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not json_file_path.is_file():
        print(f"Error: '{json_file_path}' is not a file.", file=sys.stderr)
        sys.exit(1)

    try:
        # Read and parse the JSON file
        with json_file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate using Pydantic model
        sources = Sources.model_validate(data)

        print(f"✓ Successfully validated {json_file_path}")
        print(f"  - {len(sources.datasets)} datasets")
        print(f"  - {len(sources.license_priority)} license priorities")

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    except ValidationError as e:
        print(f"Error: Validation failed for '{json_file_path}':", file=sys.stderr)

        datasets = None
        if isinstance(data, dict):
            datasets = data.get("datasets")

        def source_name_for_error(loc):
            if not loc:
                return None
            if loc[0] != "datasets" or len(loc) < 2:
                return None

            dataset_index = loc[1]
            if not isinstance(dataset_index, int):
                return None

            if not isinstance(datasets, list):
                return None
            if dataset_index < 0 or dataset_index >= len(datasets):
                return None

            dataset = datasets[dataset_index]
            if not isinstance(dataset, dict):
                return None

            source_name = dataset.get("source_name")
            if isinstance(source_name, str) and source_name:
                return source_name

            return None

        def format_field_path(loc):
            if len(loc) <= 2:
                return ""

            field_parts = []
            for part in loc[2:]:
                if isinstance(part, str):
                    if "[" in part or "(" in part or ")" in part:
                        continue
                    field_parts.append(part)
                # Ignore numeric indices in the path to keep output concise

            return ".".join(field_parts)

        for error in e.errors():
            loc = error["loc"]
            source_name = source_name_for_error(loc)

            if source_name:
                field_path = format_field_path(loc)
                if field_path:
                    identifier = f"{source_name}: {field_path}"
                else:
                    identifier = source_name
            else:
                identifier = " -> ".join(str(part) for part in loc)

            print(f"  {identifier}: {error['msg']}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(
            f"Error: Unexpected error processing '{json_file_path}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
