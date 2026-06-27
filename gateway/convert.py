"""Convert attachments (PDF / Office / images / HTML / ...) to Markdown via markitdown.

markitdown is an optional dependency (the [convert] extra); it is imported lazily so the
gateway core never requires it. Returns Markdown text; writes nothing.
"""
from __future__ import annotations

from pathlib import Path

MAX_CONVERT_BYTES = 50 * 1024 * 1024


def to_markdown(path: Path) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError:
        raise ValueError("convert_unavailable: install the [convert] extra (markitdown) to convert documents")
    p = Path(path)
    if p.stat().st_size > MAX_CONVERT_BYTES:
        raise ValueError(f"too_large: {p.name} is over {MAX_CONVERT_BYTES // (1024 * 1024)} MiB")
    try:
        result = MarkItDown().convert(str(p))
    except Exception as e:
        raise ValueError(f"convert_failed: {p.name}: {e}")
    return result.text_content or ""
