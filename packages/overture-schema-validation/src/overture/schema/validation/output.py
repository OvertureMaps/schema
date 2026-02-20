"""Rich console output utilities."""

from rich.console import Console
from rich.text import Text


def rewrap(text: str, console: Console, indent: int = 0, padding_right: int = 0) -> str:
    """Unwrap and re-wrap text at console width with indentation.

    Args
    ----
    text : str
        The text to rewrap
    console : Console
        Rich Console instance for width and wrapping
    indent : int
        Number of spaces to indent (default: 0)
    padding_right : int
        Right padding to subtract from width (default: 0)

    Returns
    -------
    str
        Re-wrapped and indented text
    """
    unwrapped = " ".join(text.split())
    text_obj = Text(unwrapped)
    wrapped_lines = text_obj.wrap(console, console.width - indent - padding_right)
    return "\n".join(f"{' ' * indent}{line}" for line in wrapped_lines)
