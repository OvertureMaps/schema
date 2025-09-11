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
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  {location}: {error['msg']}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(
            f"Error: Unexpected error processing '{json_file_path}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
