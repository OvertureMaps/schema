"""Allow ``python -m overture.schema.validation`` to run the CLI."""

from .cli import cli

if __name__ == "__main__":
    cli()
