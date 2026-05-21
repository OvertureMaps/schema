#!/usr/bin/env python3

from importlib import metadata
from pathlib import Path
import json
import re
import sys


def collect():
    """
    Collect Python package versions and print them as a JSON array.

    Form of the JSON array:

        [ {"package": "p1", "version": "v1"}, {"package": "p2", "version": "v2"}, ... ]
    """
    packages_dir = Path("packages")

    packages = sorted(
        d.name
        for d in packages_dir.iterdir()
        if d.is_dir() and d.name.startswith("overture-schema") and (d / "pyproject.toml").exists()
    )

    package_versions = [
        {"package": p, "version": metadata.version(p.replace("-", "."))}
        for p in packages
    ]

    print(json.dumps(package_versions, indent=2))


def compare(before_file: str, after_file: str):
    """
    Compare two JSON files containing package versions and print the packages that have a version
    number change as a JSON array.

    The output JSON array is sorted in topological order by package name, so those changed packages
    that do not depend on other changed packages appear first.

    Form of the JSON array:

        [ {"package": "p1", "before": "v1", "after": "v2"}, ... ]

    Note that `before` will be `null` if the package did not exist in the "before" file, and `after`
    will be `null` if the package did not exist in the "after" file.
    """
    before_array = load(before_file)
    after_array = load(after_file)

    before_dict = {item["package"]: item["version"] for item in before_array}
    after_dict = {item["package"]: item["version"] for item in after_array}

    def level(package: str) -> int:
        """
        Return the level of a package for topological sorting.

        This is brittle and hard to keep in sync, so we should replace it with a version that
        dynamically computes dependencies in the future.
        """
        if package == "overture-schema-system":
            return 0
        elif package in ["overture-schema-common", "overture-schema-core"]:
            return 1
        elif re.fullmatch(r'overture-schema-.*-theme', package) or package in ["overture-schema", "overture-schema-cli", "overture-schema-codegen", "overture-schema-annex"]:
            return 2
        else:
            raise ValueError(f"Unknown package for level computation: {package}")

    combined_keys = sorted(list(set(before_dict.keys()) | set(after_dict.keys())), key=level)

    changed_packages = []
    for package in combined_keys:
        before_version = before_dict.get(package)
        after_version = after_dict.get(package)
        if before_version != after_version:
            changed_packages.append(
                {
                    "package": package,
                    "before": before_version,
                    "after": after_version,
                }
            )

    print(json.dumps(changed_packages, indent=2))


def load(file_path: str) -> list[dict[str, str]]:
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    with path.open() as f:
        value = json.load(f)

    if not isinstance(value, list):
        print(
            f"File {file_path} contains unexpected root value: expected a `list` but got value {repr(value)} of type `{type(value).__name__}`"
        )
        sys.exit(1)

    for i, item in enumerate(value):
        if not isinstance(item, dict):
            print(
                f"File {file_path} contains unexpected item at index {i}: expected `dict` but got value {repr(item)} of type `{type(item).__name__}`"
            )
            sys.exit(1)
        elif sorted(item.keys()) != ["package", "version"]:
            print(
                f"File {file_path} contains unexpected item at index {i}: expected keys `['package', 'version']` but got keys {sorted(item.keys())}"
            )
            sys.exit(1)
        elif not isinstance(item["package"], str):
            print(
                f"File {file_path} contains unexpected item at index {i}: expected `package` to be of type `str` but got value {repr(item['package'])} of type `{type(item['package']).__name__}`"
            )
            sys.exit(1)
        elif not isinstance(item["version"], str):
            print(
                f"File {file_path} contains unexpected item at index {i}: expected `version` to be of type `str` but got value {repr(item['version'])} of type `{type(item['version']).__name__}`"
            )
            sys.exit(1)

    return value


def usage():
    print("Usage:")
    print(f"  ./{sys.argv[0]} collect")
    print(f"  ./{sys.argv[0]} compare BEFORE_FILE AFTER_FILE")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1]

    if cmd == "collect":
        collect()
    elif cmd == "compare":
        if len(sys.argv) != 4:
            usage()
        compare(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {cmd}")
        usage()


if __name__ == "__main__":
    main()
