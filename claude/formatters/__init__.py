"""
Formatter registry for Claude Code hooks
Each language formatter is a separate module with a standard interface
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

# Formatter function signature: (file_path: Path, project_dir: Path) -> bool
FormatterFunc = Callable[[Path, Path], bool]

# Registry of file extensions to formatter functions
_FORMATTERS: Dict[str, FormatterFunc] = {}


def register_formatter(extensions: List[str], formatter: FormatterFunc) -> None:
    """
    Register a formatter function for one or more file extensions

    Args:
        extensions: List of file extensions (e.g., [".py", ".pyx"])
        formatter: Function that formats files of this type
    """
    for ext in extensions:
        _FORMATTERS[ext.lower()] = formatter


def get_formatter(file_path: Path) -> Optional[FormatterFunc]:
    """
    Get the appropriate formatter for a file

    Args:
        file_path: Path to the file

    Returns:
        Formatter function or None if no formatter registered
    """
    suffix = file_path.suffix.lower()
    return _FORMATTERS.get(suffix)


def get_supported_extensions() -> List[str]:
    """
    Get list of all supported file extensions

    Returns:
        List of extensions with registered formatters
    """
    return sorted(_FORMATTERS.keys())


# Import all formatters to register them
from . import python  # noqa: E402
from . import swift  # noqa: E402
from . import typescript  # noqa: E402
from . import json  # noqa: E402

# Future formatters can be added here:
# from . import go_formatter
# from . import rust_formatter
# from . import java_formatter
# from . import markdown_formatter
