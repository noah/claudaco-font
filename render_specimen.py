#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render a full-page Claudaco specimen and every Unicode mapping to PNG.

Install requirements-specimen.txt, then run this after building the font:
    python render_specimen.py Claudaco-Regular.ttf
"""

from __future__ import annotations

import argparse
import math
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


def render_specimen(font_path: Path, output_path: Path, scale: int = 2) -> None:
    with TTFont(font_path) as font:
        cmap = font.getBestCmap()
        if not cmap or "glyf" not in font:
            raise ValueError("Expected a Unicode font with TrueType outlines")
        family = font["name"].getDebugName(1)
        version = font["name"].getDebugName(5).removeprefix("Version ").split(";")[0]
        glyph_count = len(font.getGlyphOrder())
        advances = {advance for advance, _ in font["hmtx"].metrics.values()}
        if len(advances) != 1:
            raise ValueError("Expected a strictly monospaced font")
        advance = advances.pop()
        line_height = (font["hhea"].ascent - font["hhea"].descent) / font["head"].unitsPerEm
        blank = {cp for cp, name in cmap.items() if font["glyf"][name].numberOfContours == 0}

    width, margin = 1800, 96
    columns, cell_height, grid_top = 32, 64, 1330
    rows = math.ceil(len(cmap) / columns)
    grid_bottom = grid_top + rows * cell_height
    height = grid_bottom + 140
    content_width = width - margin * 2
    cell_width = content_width / columns
    paper, ink, muted = "#f5f2e9", "#242b2a", "#666b65"
    accent, rule = "#20675c", "#d7d8ce"
    image = Image.new("RGB", (width * scale, height * scale), paper)
    draw = ImageDraw.Draw(image)

    @lru_cache(maxsize=None)
    def face(size: int) -> ImageFont.FreeTypeFont:
        # BASIC draws each encoded glyph without normalization or substitutions.
        # It also keeps isolated combining marks and the soft hyphen visible.
        return ImageFont.truetype(
            str(font_path), size * scale, layout_engine=ImageFont.Layout.BASIC
        )

    def text(
        x: float,
        y: float,
        value: str,
        size: int,
        color: str = ink,
        anchor: str = "lt",
    ) -> None:
        missing = set(map(ord, value)).difference(cmap)
        if missing:
            labels = ", ".join(f"U+{cp:04X}" for cp in sorted(missing))
            raise ValueError(f"Specimen text requires missing characters: {labels}")
        position = (x * scale, y * scale)
        bounds = draw.textbbox(position, value, font=face(size), anchor=anchor)
        if bounds[0] < 0 or bounds[1] < 0 or bounds[2] > image.width or bounds[3] > image.height:
            raise ValueError(f"Specimen text falls outside the page: {value!r}")
        draw.text(position, value, font=face(size), fill=color, anchor=anchor)

    def rectangle(box: tuple[float, float, float, float], color: str) -> None:
        draw.rectangle(tuple(round(value * scale) for value in box), fill=color)

    def line(x0: float, y0: float, x1: float, y1: float, color: str = rule) -> None:
        draw.line(
            (round(x0 * scale), round(y0 * scale), round(x1 * scale), round(y1 * scale)),
            fill=color,
            width=scale,
        )

    text(margin, 70, "A MONACO-DERIVED TERMINAL FACE", 18, accent)
    text(width - margin, 70, f"REGULAR / {version}", 18, accent, "rt")
    line(margin, 108, width - margin, 108, accent)
    text(margin - 3, 149, "Claudaco", 134)
    text(1110, 165, f"{len(cmap)} Unicode mappings", 24)
    text(1110, 211, f"{glyph_count} glyphs", 24)
    text(1110, 257, f"{advance:,} units per cell", 24, muted)

    text(margin, 337, "01 / READ THE RHYTHM", 18, accent)
    pangram = "The quick brown fox jumps over the lazy dog."
    text(margin, 389, pangram, 55)
    text(margin, 477, pangram.upper(), 32)
    text(margin, 541, "Pack my box with five dozen liquor jugs.", 28)
    text(margin, 591, "Sphinx of black quartz, judge my vow.", 28)
    text(margin, 650, "Il1 | O0Q | rn m | {} [] () <> | 0123456789", 25, muted)

    # Match terminal row height to the font's metrics so box rules meet.
    rectangle((margin, 747, 876, 1150), "#202d2c")
    text(126, 777, "IN THE TERMINAL", 17, "#a1c9bb")
    terminal_width = 42
    contents = [
        f" ⓘ Claudaco · Regular {version}",
        "",
        " ❯ build --font Claudaco",
        f" ↳ {len(cmap)} Unicode mappings",
        " ◦ small circles: ∘ ◦ ⚬ ○",
        " ▰▰▰▰▰▰▰▰▱▱  80%",
    ]
    if any(len(value) > terminal_width for value in contents):
        raise ValueError("Terminal sample is wider than its frame")
    terminal_lines = [
        "╭" + "─" * terminal_width + "╮",
        *("│" + value.ljust(terminal_width) + "│" for value in contents),
        "╰" + "─" * terminal_width + "╯",
    ]
    for index, value in enumerate(terminal_lines):
        text(126, 855 + index * 24 * line_height, value, 24, "#e7eee6", "ls")

    text(924, 765, "SCRIPTS / MARKS / MATHEMATICS", 17, accent)
    text(924, 818, "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ", 30)
    text(924, 870, "αβγδεζηθικλμνξοπρςστυφχψω", 30)
    # An alphabet chart, not running RTL text: keep Unicode order explicitly.
    for index, codepoint in enumerate(range(0x05D0, 0x05EB)):
        text(924 + index * 23, 965, chr(codepoint), 30, anchor="ls")
    text(924, 985, "Hebrew alphabet in Unicode order", 14, muted)
    text(924, 1030, "f ∘ g   ∅ ⊆ A   α β γ ∈ A   A ∩ B", 26)
    text(924, 1087, "◦ • ∘ ⚬ ○ ●   ← ↑ → ↓   ﬀ ﬁ ﬂ ﬃ ﬄ", 26)

    line(margin, 1196, width - margin, 1196, accent)
    text(margin, 1230, "02 / EVERY CHARACTER", 28)
    text(width - margin, 1237, f"{len(cmap)} MAPPINGS / UNICODE ORDER", 17, accent, "rt")
    text(margin, 1283, "Labels are hexadecimal Unicode code points. Blank cells are named.", 18, muted)

    rendered = []
    for index, codepoint in enumerate(sorted(cmap)):
        column, row = index % columns, index // columns
        x = margin + column * cell_width
        y = grid_top + row * cell_height
        center = x + cell_width / 2
        if row % 2 == 0:
            rectangle((x, y, x + cell_width, y + cell_height), "#fcfaf4")
        if codepoint in blank:
            text(center, y + 31, "BLANK" if codepoint == 0x2800 else "SPACE", 10, muted, "ms")
        else:
            text(center, y + 35, chr(codepoint), 30, anchor="ms")
        text(center, y + 58, f"{codepoint:04X}", 11, muted, "ms")
        rendered.append(codepoint)

    for row in range(rows + 1):
        y = grid_top + row * cell_height
        line(margin, y, width - margin, y)
    for column in range(columns + 1):
        x = margin + column * cell_width
        line(x, grid_top, x, grid_bottom)

    text(margin, grid_bottom + 40, "Rendered directly from the font. Every mapped character is shown above.", 18, muted)
    text(margin, grid_bottom + 88, family, 18, accent)
    text(width - margin, grid_bottom + 88, "FONT SPECIMEN / 01", 18, accent, "rt")
    assert rendered == sorted(cmap)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Font family", family)
    metadata.add_text("Glyph count", str(glyph_count))
    metadata.add_text("Unicode mappings", str(len(rendered)))
    metadata.add_text("Codepoints", " ".join(f"{cp:04X}" for cp in rendered))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", pnginfo=metadata, optimize=True)
    print(f"Wrote {output_path} ({image.width} × {image.height}); {len(rendered)} Unicode mappings.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path, nargs="?", default=Path("Claudaco-Regular.ttf"))
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("docs/claudaco-specimen.png")
    )
    parser.add_argument("--scale", type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args(argv)
    if not args.font.is_file():
        parser.error(f"Font not found: {args.font}; build Claudaco first")
    try:
        render_specimen(args.font, args.output, args.scale)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
