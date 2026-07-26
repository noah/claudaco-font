#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Report terminal-facing OpenCode characters missing from a font cmap."""

from __future__ import annotations

import argparse
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


SOURCE_ROOTS = (Path("packages/tui/src"), Path("packages/opencode/src/cli"))
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}

# The run-mode demo intentionally exercises terminal fallback for CJK text.
DEMO_PATH = Path("packages/opencode/src/cli/cmd/run/demo.ts")
DEMO_CODEPOINTS = {0x5B57, 0x6F22}


def scan_sources(opencode_root: Path) -> dict[int, list[str]]:
    occurrences: dict[int, list[str]] = defaultdict(list)
    for relative_root in SOURCE_ROOTS:
        source_root = opencode_root / relative_root
        if not source_root.is_dir():
            raise ValueError(f"OpenCode source directory not found: {source_root}")
        for path in source_root.rglob("*"):
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(opencode_root)
            lines = path.read_text(encoding="utf-8").splitlines()
            for line_number, line in enumerate(lines, 1):
                codepoints = {ord(character) for character in line if ord(character) > 0x7F}
                for codepoint in sorted(codepoints):
                    if chr(codepoint).isspace():
                        continue
                    occurrences[codepoint].append(f"{relative}:{line_number}")
    return occurrences


def audit(opencode_root: Path, font_path: Path) -> int:
    occurrences = scan_sources(opencode_root)
    font = TTFont(str(font_path), lazy=False)
    cmap = font.getBestCmap()
    excluded = {
        codepoint
        for codepoint in DEMO_CODEPOINTS
        if codepoint in occurrences
        and all(
            Path(location.rsplit(":", 1)[0]) == DEMO_PATH
            for location in occurrences[codepoint]
        )
    }

    missing = set(occurrences).difference(cmap).difference(excluded)
    empty = set()
    glyph_set = font.getGlyphSet()
    for codepoint in set(occurrences).intersection(cmap).difference({0x2800}):
        bounds_pen = BoundsPen(glyph_set)
        glyph_set[cmap[codepoint]].draw(bounds_pen)
        if bounds_pen.bounds is None:
            empty.add(codepoint)
    font.close()

    uncovered = sorted(missing | empty)
    print(
        f"Scanned {len(occurrences)} codepoints in terminal-owned source; "
        f"covered {len(occurrences) - len(uncovered) - len(excluded)}; "
        f"excluded {len(excluded)}; uncovered {len(uncovered)}."
    )
    for codepoint in uncovered:
        character = chr(codepoint)
        name = unicodedata.name(character, "UNKNOWN")
        reason = "empty outline" if codepoint in empty else "missing cmap entry"
        print(f"U+{codepoint:04X} {character} {name} ({reason})")
        for location in occurrences[codepoint]:
            print(f"  {location}")
    return 1 if uncovered else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("opencode", type=Path, help="Path to an OpenCode checkout")
    parser.add_argument("font", type=Path, help="Font file to audit")
    args = parser.parse_args(argv)

    if not args.opencode.is_dir():
        parser.error(f"OpenCode checkout not found: {args.opencode}")
    if not args.font.is_file():
        parser.error(f"Font file not found: {args.font}")
    try:
        return audit(args.opencode, args.font)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
