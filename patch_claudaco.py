#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Patch Monaco for Powerline into Claudaco with Unicode glyphs used by Claude Code/TUIs.

The patch is self-contained: it constructs the added glyphs from geometric
primitives and from the base font's own ASCII letters. It does not require a
second donor font.

Usage (PowerShell or cmd.exe):
    py -m pip install fonttools
    py patch_claudaco.py "Monaco for Powerline.ttf"

The default version creates a separately installable family and filename, such
as ``Claudaco 1.227`` and ``Claudaco-1.227-Regular.ttf``.
"""

from __future__ import annotations

import argparse
import math
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


LATIN_EXTENDED_D_LIGATURES = {
    0xA728: ("TZ", False),
    0xA729: ("tz", False),
    0xA732: ("AA", False),
    0xA733: ("aa", False),
    0xA734: ("AO", False),
    0xA735: ("ao", False),
    0xA736: ("AU", False),
    0xA737: ("au", False),
    0xA738: ("AV", False),
    0xA739: ("av", False),
    0xA73A: ("AV", True),
    0xA73B: ("av", True),
    0xA73C: ("AY", False),
    0xA73D: ("ay", False),
    0xA74E: ("OO", False),
    0xA74F: ("oo", False),
    0xA760: ("VY", False),
    0xA761: ("vy", False),
}

PRESENTATION_LIGATURES = {
    0xFB00: "ff",
    0xFB01: "fi",
    0xFB02: "fl",
    0xFB03: "ffi",
    0xFB04: "ffl",
    0xFB05: "ſt",
    0xFB06: "st",
}

LETTER_SEQUENCE_WIDTH_FACTOR = 1.35

DIRECTIONAL_TRIANGLES = {
    0x25B2: ("up", False, "regular"),
    0x25B3: ("up", True, "regular"),
    0x25B4: ("up", False, "small"),
    0x25B5: ("up", True, "small"),
    0x25B6: ("right", False, "regular"),
    0x25B7: ("right", True, "regular"),
    0x25B8: ("right", False, "small"),
    0x25B9: ("right", True, "small"),
    0x25BA: ("right", False, "pointer"),
    0x25BB: ("right", True, "pointer"),
    0x25BC: ("down", False, "regular"),
    0x25BD: ("down", True, "regular"),
    0x25BE: ("down", False, "small"),
    0x25BF: ("down", True, "small"),
    0x25C0: ("left", False, "regular"),
    0x25C1: ("left", True, "regular"),
    0x25C2: ("left", False, "small"),
    0x25C3: ("left", True, "small"),
    0x25C4: ("left", False, "pointer"),
    0x25C5: ("left", True, "pointer"),
}

ADJACENT_SQUARE_ADDITIONS = {
    0x25A1,
    0x25A2,
    *range(0x25A4, 0x25B0),
}


# Characters explicitly observed in the user's Claude Code / terminal output.
EXPLICIT_CODEPOINTS = {
    0x00B7,  # · MIDDLE DOT (normally already present)
    *range(0x0391, 0x03A2),  # Greek capitals alpha through rho
    *range(0x03A3, 0x03AA),  # Greek capitals sigma through omega; U+03A2 is unassigned
    *range(0x03B1, 0x03CA),  # Greek lowercase alphabet, including final sigma
    0x05BE,  # ־ HEBREW PUNCTUATION MAQAF
    0x05C0,  # ׀ HEBREW PUNCTUATION PASEQ
    0x05C3,  # ׃ HEBREW PUNCTUATION SOF PASUQ
    *range(0x05D0, 0x05EB),  # Hebrew letters alef through tav, including finals
    0x05F3,  # ׳ HEBREW PUNCTUATION GERESH
    0x05F4,  # ״ HEBREW PUNCTUATION GERSHAYIM
    0x2003,  # EM SPACE
    0x200A,  # HAIR SPACE
    0x2011,  # ‑ NON-BREAKING HYPHEN
    0x202F,  # NARROW NO-BREAK SPACE
    0x20AA,  # ₪ NEW SHEQEL SIGN
    0x2139,  # ℹ INFORMATION SOURCE
    0x2190,  # ← LEFTWARDS ARROW
    0x2191,  # ↑ UPWARDS ARROW
    0x2192,  # → RIGHTWARDS ARROW
    0x2193,  # ↓ DOWNWARDS ARROW
    0x2194,  # ↔ LEFT RIGHT ARROW
    0x2195,  # ↕ UP DOWN ARROW
    0x2196,  # ↖ NORTH WEST ARROW
    0x2197,  # ↗ NORTH EAST ARROW
    0x2198,  # ↘ SOUTH EAST ARROW
    0x2199,  # ↙ SOUTH WEST ARROW
    0x219C,  # ↜ LEFTWARDS WAVE ARROW
    0x219D,  # ↝ RIGHTWARDS WAVE ARROW
    0x21A9,  # ↩ LEFTWARDS ARROW WITH HOOK
    0x21AA,  # ↪ RIGHTWARDS ARROW WITH HOOK
    0x21AD,  # ↭ LEFT RIGHT WAVE ARROW
    0x21AF,  # ↯ DOWNWARDS ZIGZAG ARROW
    0x21B0,  # ↰ UPWARDS ARROW WITH TIP LEFTWARDS
    0x21B1,  # ↱ UPWARDS ARROW WITH TIP RIGHTWARDS
    0x21B2,  # ↲ DOWNWARDS ARROW WITH TIP LEFTWARDS
    0x21B3,  # ↳ DOWNWARDS ARROW WITH TIP RIGHTWARDS
    0x21B4,  # ↴ RIGHTWARDS ARROW WITH CORNER DOWNWARDS
    0x21B5,  # ↵ DOWNWARDS ARROW WITH CORNER LEFTWARDS
    0x21BB,  # ↻ CLOCKWISE OPEN CIRCLE ARROW
    0x21C6,  # ⇆ LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    0x21E7,  # ⇧ UPWARDS WHITE ARROW
    0x2205,  # ∅ EMPTY SET
    0x2208,  # ∈ ELEMENT OF
    0x2209,  # ∉ NOT AN ELEMENT OF
    0x220B,  # ∋ CONTAINS AS MEMBER
    0x220C,  # ∌ DOES NOT CONTAIN AS MEMBER
    0x2229,  # ∩ INTERSECTION
    0x222A,  # ∪ UNION
    0x2282,  # ⊂ SUBSET OF
    0x2283,  # ⊃ SUPERSET OF
    0x2284,  # ⊄ NOT A SUBSET OF
    0x2285,  # ⊅ NOT A SUPERSET OF
    0x2286,  # ⊆ SUBSET OF OR EQUAL TO
    0x2287,  # ⊇ SUPERSET OF OR EQUAL TO
    0x2299,  # ⊙ CIRCLED DOT OPERATOR
    0x22EE,  # ⋮ VERTICAL ELLIPSIS
    0x22EF,  # ⋯ MIDLINE HORIZONTAL ELLIPSIS
    0x2315,  # ⌕ TELEPHONE RECORDER
    0x23BF,  # ⎿ DENTISTRY SYMBOL LIGHT VERTICAL AND BOTTOM RIGHT
    0x23F5,  # ⏵ BLACK MEDIUM RIGHT-POINTING TRIANGLE
    0x23F8,  # ⏸ DOUBLE VERTICAL BAR
    0x24D8,  # ⓘ CIRCLED LATIN SMALL LETTER I
    0x24DB,  # ⓛ CIRCLED LATIN SMALL LETTER L
    0x24E6,  # ⓦ CIRCLED LATIN SMALL LETTER W
    0x2500,  # ─ BOX DRAWINGS LIGHT HORIZONTAL
    0x2502,  # │ BOX DRAWINGS LIGHT VERTICAL
    0x2503,  # ┃ BOX DRAWINGS HEAVY VERTICAL
    0x250C,  # ┌ BOX DRAWINGS LIGHT DOWN AND RIGHT
    0x2510,  # ┐ BOX DRAWINGS LIGHT DOWN AND LEFT
    0x2514,  # └ BOX DRAWINGS LIGHT UP AND RIGHT
    0x2518,  # ┘ BOX DRAWINGS LIGHT UP AND LEFT
    0x251C,  # ├ BOX DRAWINGS LIGHT VERTICAL AND RIGHT
    0x2524,  # ┤ BOX DRAWINGS LIGHT VERTICAL AND LEFT
    0x252C,  # ┬ BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
    0x2534,  # ┴ BOX DRAWINGS LIGHT UP AND HORIZONTAL
    0x254C,  # ╌ BOX DRAWINGS LIGHT DOUBLE DASH HORIZONTAL
    0x2550,  # ═ BOX DRAWINGS DOUBLE HORIZONTAL
    0x2551,  # ║ BOX DRAWINGS DOUBLE VERTICAL
    0x256D,  # ╭ BOX DRAWINGS LIGHT ARC DOWN AND RIGHT
    0x256E,  # ╮ BOX DRAWINGS LIGHT ARC DOWN AND LEFT
    0x256F,  # ╯ BOX DRAWINGS LIGHT ARC UP AND LEFT
    0x2570,  # ╰ BOX DRAWINGS LIGHT ARC UP AND RIGHT
    0x2579,  # ╹ BOX DRAWINGS HEAVY UP
    0x2580,  # ▀ UPPER HALF BLOCK
    0x2584,  # ▄ LOWER HALF BLOCK
    0x2588,  # █ FULL BLOCK
    0x258C,  # ▌ LEFT HALF BLOCK
    0x2590,  # ▐ RIGHT HALF BLOCK
    0x2598,  # ▘ QUADRANT UPPER LEFT
    0x259B,  # ▛ ... UPPER LEFT, UPPER RIGHT, LOWER LEFT
    0x259C,  # ▜ ... UPPER LEFT, UPPER RIGHT, LOWER RIGHT
    0x259D,  # ▝ QUADRANT UPPER RIGHT
    0x25A0,  # ■ BLACK SQUARE
    *ADJACENT_SQUARE_ADDITIONS,
    0x25A3,  # ▣ WHITE SQUARE CONTAINING BLACK SMALL SQUARE
    0x25B0,  # ▰ BLACK PARALLELOGRAM
    0x25B1,  # ▱ WHITE PARALLELOGRAM
    0x25B3,  # △ WHITE UP-POINTING TRIANGLE
    0x25B6,  # ▶ BLACK RIGHT-POINTING TRIANGLE
    0x25B8,  # ▸ BLACK RIGHT-POINTING SMALL TRIANGLE
    0x25BC,  # ▼ BLACK DOWN-POINTING TRIANGLE
    0x25BE,  # ▾ BLACK DOWN-POINTING SMALL TRIANGLE
    0x25C6,  # ◆ BLACK DIAMOND
    0x25C8,  # ◈ WHITE DIAMOND CONTAINING BLACK SMALL DIAMOND
    0x25C9,  # ◉ FISHEYE
    0x25CB,  # ○ WHITE CIRCLE
    0x25CD,  # ◍ CIRCLE WITH VERTICAL FILL
    0x25CF,  # ● BLACK CIRCLE
    0x25D0,  # ◐ CIRCLE WITH LEFT HALF BLACK
    0x25D4,  # ◔ CIRCLE WITH UPPER RIGHT QUADRANT BLACK
    *DIRECTIONAL_TRIANGLES,
    0x25C7,  # ◇ WHITE DIAMOND
    0x25CC,  # ◌ DOTTED CIRCLE
    0x25CE,  # ◎ BULLSEYE
    *range(0x25E2, 0x25E6),  # Corner triangles
    0x25FB,  # ◻ WHITE MEDIUM SQUARE
    0x2699,  # ⚙ GEAR
    0x26A0,  # ⚠ WARNING SIGN
    0x2731,  # ✱ HEAVY ASTERISK
    *range(0x276C, 0x2772),  # ❬–❱ ANGLE BRACKET ORNAMENTS
    0x27E8,  # ⟨ MATHEMATICAL LEFT ANGLE BRACKET
    0x27E9,  # ⟩ MATHEMATICAL RIGHT ANGLE BRACKET
    0x27F3,  # ⟳ CLOCKWISE GAPPED CIRCLE ARROW
    0x2800,  # ⠀ BRAILLE PATTERN BLANK
    0x2807,  # ⠇ BRAILLE PATTERN DOTS-123
    0x280B,  # ⠋ BRAILLE PATTERN DOTS-124
    0x280F,  # ⠏ BRAILLE PATTERN DOTS-1234
    0x2819,  # ⠙ BRAILLE PATTERN DOTS-145
    0x2826,  # ⠦ BRAILLE PATTERN DOTS-236
    0x2827,  # ⠧ BRAILLE PATTERN DOTS-1236
    0x2834,  # ⠴ BRAILLE PATTERN DOTS-356
    0x2838,  # ⠸ BRAILLE PATTERN DOTS-456
    0x2839,  # ⠹ BRAILLE PATTERN DOTS-1456
    0x283C,  # ⠼ BRAILLE PATTERN DOTS-3456
    0x29C9,  # ⧉ TWO JOINED SQUARES
    0x2B16,  # ⬖ DIAMOND WITH LEFT HALF BLACK
    0x2B1D,  # ⬝ BLACK VERY SMALL SQUARE
    0x2B25,  # ⬥ BLACK MEDIUM DIAMOND
    0x2B29,  # ⬩ BLACK SMALL DIAMOND
    0x2B2A,  # ⬪ BLACK SMALL LOZENGE
    0xE0B0,  # Powerline right hard divider (expected in base font)
    0xE0B2,  # Powerline left hard divider (expected in base font)
    0xF0A7,  # Private-use square bullet
    0xF0B7,  # Private-use bullet
    *LATIN_EXTENDED_D_LIGATURES,
    *PRESENTATION_LIGATURES,
    0xFFFD,  # � REPLACEMENT CHARACTER
}


# ---------- low-level outline helpers ----------

def _rect(
    pen: TTGlyphPen,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    clockwise: bool = True,
) -> None:
    """Add a rectangular contour."""
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if clockwise:
        points = ((x0, y0), (x0, y1), (x1, y1), (x1, y0))
    else:
        points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    pen.moveTo(points[0])
    for point in points[1:]:
        pen.lineTo(point)
    pen.closePath()


def _rounded_rect(
    pen: TTGlyphPen,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    radius: float,
    *,
    clockwise: bool = True,
) -> None:
    """Add a rounded rectangular contour."""
    radius = min(radius, abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0)
    if clockwise:
        pen.moveTo((x0 + radius, y0))
        pen.qCurveTo((x0, y0), (x0, y0 + radius))
        pen.lineTo((x0, y1 - radius))
        pen.qCurveTo((x0, y1), (x0 + radius, y1))
        pen.lineTo((x1 - radius, y1))
        pen.qCurveTo((x1, y1), (x1, y1 - radius))
        pen.lineTo((x1, y0 + radius))
        pen.qCurveTo((x1, y0), (x1 - radius, y0))
        pen.lineTo((x0 + radius, y0))
    else:
        pen.moveTo((x0 + radius, y0))
        pen.lineTo((x1 - radius, y0))
        pen.qCurveTo((x1, y0), (x1, y0 + radius))
        pen.lineTo((x1, y1 - radius))
        pen.qCurveTo((x1, y1), (x1 - radius, y1))
        pen.lineTo((x0 + radius, y1))
        pen.qCurveTo((x0, y1), (x0, y1 - radius))
        pen.lineTo((x0, y0 + radius))
        pen.qCurveTo((x0, y0), (x0 + radius, y0))
    pen.closePath()


def _polygon(pen: TTGlyphPen, points: Sequence[tuple[float, float]]) -> None:
    if len(points) < 3:
        raise ValueError("A polygon needs at least three points")
    pen.moveTo(points[0])
    for point in points[1:]:
        pen.lineTo(point)
    pen.closePath()


def _polygon_ring(
    pen: TTGlyphPen,
    outer: Sequence[tuple[float, float]],
    inner: Sequence[tuple[float, float]],
) -> None:
    """Add a polygon with a counter-wound inner cutout."""
    _polygon(pen, outer)
    _polygon(pen, tuple(reversed(inner)))


def _stroke_segment(
    pen: TTGlyphPen,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    thickness: float,
) -> None:
    """Add a rectangular stroke centered on the segment endpoints."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length <= 0:
        return
    nx = -dy / length * thickness / 2.0
    ny = dx / length * thickness / 2.0
    _polygon(
        pen,
        (
            (x0 + nx, y0 + ny),
            (x1 + nx, y1 + ny),
            (x1 - nx, y1 - ny),
            (x0 - nx, y0 - ny),
        ),
    )


def _ellipse_arc_band(
    pen: TTGlyphPen,
    cx: float,
    cy: float,
    radius_x: float,
    radius_y: float,
    start_angle: float,
    end_angle: float,
    thickness: float,
    *,
    segments: int = 20,
) -> None:
    """Add a filled band following an elliptical arc."""
    outer_x = radius_x + thickness / 2.0
    outer_y = radius_y + thickness / 2.0
    inner_x = max(1.0, radius_x - thickness / 2.0)
    inner_y = max(1.0, radius_y - thickness / 2.0)
    angles = [
        start_angle + (end_angle - start_angle) * index / segments
        for index in range(segments + 1)
    ]
    outer = [
        (cx + outer_x * math.cos(angle), cy + outer_y * math.sin(angle))
        for angle in angles
    ]
    inner = [
        (cx + inner_x * math.cos(angle), cy + inner_y * math.sin(angle))
        for angle in reversed(angles)
    ]
    _polygon(pen, tuple(outer + inner))


def _circle(
    pen: TTGlyphPen,
    cx: float,
    cy: float,
    radius: float,
    *,
    clockwise: bool,
    segments: int = 8,
) -> None:
    """Add a high-quality quadratic approximation of a circle."""
    if segments < 4 or segments % 2:
        raise ValueError("segments must be an even integer >= 4")
    direction = -1.0 if clockwise else 1.0
    delta = direction * (2.0 * math.pi / segments)
    start_angle = 0.0
    pen.moveTo((cx + radius, cy))
    angle = start_angle
    for _ in range(segments):
        next_angle = angle + delta
        mid = (angle + next_angle) / 2.0
        control_radius = radius / math.cos(abs(delta) / 2.0)
        control = (
            cx + control_radius * math.cos(mid),
            cy + control_radius * math.sin(mid),
        )
        end = (
            cx + radius * math.cos(next_angle),
            cy + radius * math.sin(next_angle),
        )
        pen.qCurveTo(control, end)
        angle = next_angle
    pen.closePath()


def _ring(
    pen: TTGlyphPen,
    cx: float,
    cy: float,
    outer_radius: float,
    inner_radius: float,
) -> None:
    _circle(pen, cx, cy, outer_radius, clockwise=True)
    _circle(pen, cx, cy, inner_radius, clockwise=False)


def _square_ring(
    pen: TTGlyphPen,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    stroke: float,
) -> None:
    _rect(pen, x0, y0, x1, y1, clockwise=True)
    _rect(
        pen,
        x0 + stroke,
        y0 + stroke,
        x1 - stroke,
        y1 - stroke,
        clockwise=False,
    )


def _bounds(font: TTFont, glyph_name: str) -> tuple[float, float, float, float]:
    glyph_set = font.getGlyphSet()
    bounds_pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(bounds_pen)
    if bounds_pen.bounds is None:
        return (0.0, 0.0, 0.0, 0.0)
    return bounds_pen.bounds


def _draw_existing_glyph_fitted(
    font: TTFont,
    source_name: str,
    destination_pen: TTGlyphPen,
    target_box: tuple[float, float, float, float],
) -> None:
    """Draw a base-font glyph into target_box, preserving aspect ratio."""
    x_min, y_min, x_max, y_max = _bounds(font, source_name)
    source_width = x_max - x_min
    source_height = y_max - y_min
    if source_width <= 0 or source_height <= 0:
        return

    target_x0, target_y0, target_x1, target_y1 = target_box
    target_width = target_x1 - target_x0
    target_height = target_y1 - target_y0
    scale = min(target_width / source_width, target_height / source_height)

    source_cx = (x_min + x_max) / 2.0
    source_cy = (y_min + y_max) / 2.0
    target_cx = (target_x0 + target_x1) / 2.0
    target_cy = (target_y0 + target_y1) / 2.0
    dx = target_cx - source_cx * scale
    dy = target_cy - source_cy * scale

    transform = Transform(scale, 0, 0, scale, dx, dy)
    transformed_pen = TransformPen(destination_pen, transform)
    font.getGlyphSet()[source_name].draw(transformed_pen)


# ---------- glyph builders ----------

Builder = Callable[[TTFont, TTGlyphPen, int, int, int], None]


def _build_blank(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    """Build an intentionally outline-free spacing glyph."""


def _build_greek_capital_sigma(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    height = top - bottom
    base = bottom + height * 0.20
    cap_height = bottom + height * 0.78
    middle = (base + cap_height) / 2.0
    stroke = max(140.0, width * 0.115)
    left = width * 0.20
    right = width * 0.80
    point = width * 0.61
    _stroke_segment(pen, left, cap_height, right, cap_height, stroke)
    _stroke_segment(pen, left, cap_height, point, middle, stroke)
    _stroke_segment(pen, point, middle, left, base, stroke)
    _stroke_segment(pen, left, base, right, base, stroke)


GREEK_CAPITAL_ASCII = {
    0x0391: "A",
    0x0392: "B",
    0x0395: "E",
    0x0396: "Z",
    0x0397: "H",
    0x0399: "I",
    0x039A: "K",
    0x039C: "M",
    0x039D: "N",
    0x039F: "O",
    0x03A1: "P",
    0x03A4: "T",
    0x03A5: "Y",
    0x03A7: "X",
}


def _build_existing_character(character: str) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        source_name = font.getBestCmap().get(ord(character))
        if source_name is None:
            raise ValueError(f"Base font has no glyph for {character!r}")
        font.getGlyphSet()[source_name].draw(pen)

    return builder


def _build_letter_sequence(sequence: str, *, horizontal_bar: bool = False) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        margin = width * 0.035
        slot = (width - 2.0 * margin) / len(sequence)
        scale_x = LETTER_SEQUENCE_WIDTH_FACTOR * slot / width
        y_min = math.inf
        y_max = -math.inf
        for index, character in enumerate(sequence):
            dx = (
                margin
                + index * slot
                - slot * (LETTER_SEQUENCE_WIDTH_FACTOR - 1.0) / 2.0
            )
            if character == "ſ":
                stem_x = dx + slot * 0.58
                hook_cx = stem_x + slot * 0.14
                hook_cy = 1395.0
                weight = _light_box_weight(width)
                _rect(
                    pen,
                    stem_x - weight / 2.0,
                    0.0,
                    stem_x + weight / 2.0,
                    hook_cy,
                )
                _ellipse_arc_band(
                    pen,
                    hook_cx,
                    hook_cy,
                    slot * 0.14,
                    250.0,
                    math.pi,
                    math.pi / 2.0,
                    weight,
                    segments=16,
                )
                y_min = min(y_min, 0.0)
                y_max = max(y_max, hook_cy + 250.0 + weight / 2.0)
                continue
            source_name = cmap.get(ord(character))
            if source_name is None:
                raise ValueError(f"Base font has no glyph for {character!r}")
            _x_min, source_y_min, _x_max, source_y_max = _bounds(font, source_name)
            y_min = min(y_min, source_y_min)
            y_max = max(y_max, source_y_max)
            transformed = TransformPen(
                pen, Transform(scale_x, 0.0, 0.0, 1.0, dx, 0.0)
            )
            glyph_set[source_name].draw(transformed)
        if horizontal_bar:
            bar_y = (y_min + y_max) / 2.0
            weight = _light_box_weight(width)
            _rect(
                pen,
                width * 0.20,
                bar_y - weight / 2.0,
                width * 0.80,
                bar_y + weight / 2.0,
            )

    return builder


def _build_hebrew_character(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = max(110.0, _light_box_weight(width) * 1.34)
        x0, x1 = width * 0.19, width * 0.81
        xm = width * 0.50
        y0, y1 = 20.0, min(1435.0, top - 70.0)
        ym = (y0 + y1) / 2.0

        def stroke(
            ax: float, ay: float, bx: float, by: float, factor: float = 1.0
        ) -> None:
            _stroke_segment(pen, ax, ay, bx, by, weight * factor)

        if codepoint == 0x05D0:  # alef
            stroke(x1, y1, x0, y0)
            stroke(x0, y1 * 0.78, xm + width * 0.03, y1 * 0.52)
            stroke(xm - width * 0.02, y1 * 0.43, x1, y0 + 120)
        elif codepoint == 0x05D1:  # bet
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0 + 80)
            stroke(x1, y0 + 80, x0 - width * 0.05, y0 + 80)
        elif codepoint == 0x05D2:  # gimel
            stroke(x1 - width * 0.12, y1, x1 - width * 0.16, y0 + 360)
            stroke(x1 - width * 0.16, y0 + 360, x0 + width * 0.08, y0)
            stroke(x1 - width * 0.18, y0 + 290, x1, y0)
        elif codepoint == 0x05D3:  # dalet
            stroke(x0 - width * 0.03, y1, x1, y1)
            stroke(x1 - width * 0.05, y1, x1 - width * 0.05, y0)
        elif codepoint == 0x05D4:  # he
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0)
            stroke(x0 + width * 0.04, y0, x0 + width * 0.04, y1 * 0.65)
        elif codepoint == 0x05D5:  # vav
            stroke(xm - width * 0.08, y1, x1, y1)
            stroke(x1 - width * 0.06, y1, x1 - width * 0.06, y0)
        elif codepoint == 0x05D6:  # zayin
            stroke(x0 + width * 0.12, y1, x1, y1)
            stroke(xm + width * 0.05, y1, xm - width * 0.01, y0)
        elif codepoint == 0x05D7:  # het
            stroke(x0, y1, x1, y1)
            stroke(x0 + width * 0.03, y1, x0 + width * 0.03, y0)
            stroke(x1 - width * 0.03, y1, x1 - width * 0.03, y0)
        elif codepoint == 0x05D8:  # tet
            stroke(x0 + width * 0.05, y1 * 0.76, x0 + width * 0.05, y0 + 170)
            stroke(x0 + width * 0.05, y0 + 170, xm, y0)
            stroke(xm, y0, x1, y0 + 190)
            stroke(x1, y0 + 190, x1, y1)
            stroke(x1, y1, xm + width * 0.05, y1)
            stroke(xm + width * 0.05, y1, x0 + width * 0.12, y1 * 0.62)
        elif codepoint == 0x05D9:  # yod
            stroke(xm, y1, x1, y1)
            stroke(x1 - width * 0.05, y1, x1 - width * 0.12, y1 * 0.63)
        elif codepoint == 0x05DA:  # final kaf
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, bottom + 80)
        elif codepoint == 0x05DB:  # kaf
            stroke(x0 + width * 0.08, y1, x1, y1)
            stroke(x1, y1, x1, y0 + 210)
            stroke(x1, y0 + 210, x0, y0 + 70)
        elif codepoint == 0x05DC:  # lamed
            stroke(xm + width * 0.03, y1 + 390, x1, y1 + 390)
            stroke(x1, y1 + 390, x1 - width * 0.08, ym)
            stroke(x1 - width * 0.08, ym, x0 + width * 0.07, y0 + 210)
            stroke(x0 + width * 0.07, y0 + 210, xm, y0)
        elif codepoint == 0x05DD:  # final mem
            _polygon_ring(
                pen,
                ((x0, y0), (x1, y0), (x1, y1), (x0, y1)),
                (
                    (x0 + weight, y0 + weight),
                    (x1 - weight, y0 + weight),
                    (x1 - weight, y1 - weight),
                    (x0 + weight, y1 - weight),
                ),
            )
        elif codepoint == 0x05DE:  # mem
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0)
            stroke(x1, y0, xm - width * 0.04, y0)
            stroke(x0, y1, xm + width * 0.05, y0 + 230)
        elif codepoint == 0x05DF:  # final nun
            stroke(xm + width * 0.13, y1, xm + width * 0.13, bottom + 50)
        elif codepoint == 0x05E0:  # nun
            stroke(x1 - width * 0.08, y1, x1 - width * 0.08, y0 + 120)
            stroke(x1 - width * 0.08, y0 + 120, x0 + width * 0.08, y0 + 120)
        elif codepoint == 0x05E1:  # samekh
            _ellipse_arc_band(
                pen,
                xm,
                ym,
                width * 0.31,
                (y1 - y0) * 0.50,
                0,
                2 * math.pi,
                weight,
                segments=28,
            )
        elif codepoint == 0x05E2:  # ayin
            stroke(x0, y1, xm + width * 0.02, y0 + 120)
            stroke(x1, y1, xm + width * 0.02, y0 + 120)
            stroke(xm + width * 0.02, y0 + 120, x0, y0)
        elif codepoint == 0x05E3:  # final pe
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, bottom + 70)
            stroke(x1, y0 + 260, x0 + width * 0.08, y0 + 260)
            stroke(x0 + width * 0.08, y0 + 260, x0 + width * 0.08, ym)
        elif codepoint == 0x05E4:  # pe
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0 + 170)
            stroke(x1, y0 + 170, x0, y0 + 70)
            stroke(x0 + width * 0.12, ym + 80, xm + width * 0.12, ym + 80)
        elif codepoint == 0x05E5:  # final tsadi
            stroke(x0 + width * 0.05, y1, xm + width * 0.04, ym)
            stroke(x1, y1, xm + width * 0.04, ym)
            stroke(xm + width * 0.04, ym, xm + width * 0.13, bottom + 40)
        elif codepoint == 0x05E6:  # tsadi
            stroke(x0 + width * 0.05, y1, xm + width * 0.04, ym)
            stroke(x1, y1, xm + width * 0.04, ym)
            stroke(xm + width * 0.04, ym, x0 + width * 0.10, y0)
            stroke(x0 + width * 0.10, y0, x1, y0)
        elif codepoint == 0x05E7:  # qof
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0 + 250)
            stroke(x1, y0 + 250, xm + width * 0.02, y0 + 250)
            stroke(x0 + width * 0.08, ym, x0 + width * 0.08, bottom + 40)
        elif codepoint == 0x05E8:  # resh
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0)
        elif codepoint == 0x05E9:  # shin
            stroke(x0, y1, x0 + width * 0.08, y0 + 190)
            stroke(xm, y1, xm, y0 + 80)
            stroke(x1, y1, x1 - width * 0.08, y0 + 190)
            stroke(x0 + width * 0.08, y0 + 190, xm, y0)
            stroke(x1 - width * 0.08, y0 + 190, xm, y0)
        elif codepoint == 0x05EA:  # tav
            stroke(x0, y1, x1, y1)
            stroke(x1, y1, x1, y0)
            stroke(x0 + width * 0.04, y1, x0 + width * 0.13, y0)
        elif codepoint == 0x05BE:  # maqaf
            _rect(pen, x0, y1 * 0.66, x1, y1 * 0.66 + weight)
        elif codepoint == 0x05C0:  # paseq
            _rect(pen, xm - weight / 2, y0 + 170, xm + weight / 2, y1 - 170)
        elif codepoint == 0x05C3:  # sof pasuq
            _circle(pen, xm, ym + 230, weight * 0.62, clockwise=True)
            _circle(pen, xm, ym - 230, weight * 0.62, clockwise=True)
        elif codepoint in (0x05F3, 0x05F4):  # geresh and gershayim
            count = 1 if codepoint == 0x05F3 else 2
            start_x = xm - (count - 1) * width * 0.11
            for index in range(count):
                x = start_x + index * width * 0.22
                stroke(x + width * 0.05, y1, x - width * 0.03, y1 * 0.70)
        elif codepoint == 0x20AA:  # new sheqel sign
            stroke(x0, y0, x0, y1)
            stroke(x0, y1, xm + width * 0.02, y1)
            stroke(xm + width * 0.02, y1, xm + width * 0.02, ym)
            stroke(x1, y1, x1, y0)
            stroke(x1, y0, xm - width * 0.02, y0)
            stroke(xm - width * 0.02, y0, xm - width * 0.02, ym)
        else:
            raise ValueError(f"Unsupported Hebrew character: U+{codepoint:04X}")

    return builder


def _build_greek_capital(codepoint: int) -> Builder:
    if codepoint in GREEK_CAPITAL_ASCII:
        return _build_existing_character(GREEK_CAPITAL_ASCII[codepoint])

    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        if codepoint == 0x03A3:
            _build_greek_capital_sigma(font, pen, width, bottom, top)
            return

        height = top - bottom
        base = bottom + height * 0.20
        cap_height = bottom + height * 0.78
        middle = (base + cap_height) / 2.0
        stroke = max(140.0, width * 0.115)
        cx = width / 2.0
        left = width * 0.20
        right = width * 0.80

        def line(x0: float, y0: float, x1: float, y1: float) -> None:
            _stroke_segment(pen, x0, y0, x1, y1, stroke)

        if codepoint == 0x0393:  # Gamma
            line(left, base, left, cap_height)
            line(left, cap_height, right, cap_height)
        elif codepoint == 0x0394:  # Delta
            outer = ((cx, cap_height), (right, base), (left, base))
            inset = width * 0.105
            inner = (
                (cx, cap_height - inset * 2.0),
                (right - inset * 1.35, base + inset),
                (left + inset * 1.35, base + inset),
            )
            _polygon_ring(pen, outer, inner)
        elif codepoint == 0x0398:  # Theta
            radius_x = width * 0.31
            radius_y = (cap_height - base) * 0.48
            _ellipse_arc_band(
                pen,
                cx,
                middle,
                radius_x,
                radius_y,
                2.0 * math.pi,
                0.0,
                stroke,
                segments=32,
            )
            line(cx - radius_x * 0.72, middle, cx + radius_x * 0.72, middle)
        elif codepoint == 0x039B:  # Lamda
            line(left, base, cx, cap_height)
            line(cx, cap_height, right, base)
        elif codepoint == 0x039E:  # Xi
            line(left, cap_height, right, cap_height)
            line(width * 0.29, middle, width * 0.71, middle)
            line(left, base, right, base)
        elif codepoint == 0x03A0:  # Pi
            line(left, base, left, cap_height)
            line(left, cap_height, right, cap_height)
            line(right, cap_height, right, base)
        elif codepoint == 0x03A6:  # Phi
            radius_x = width * 0.30
            radius_y = (cap_height - base) * 0.32
            _ellipse_arc_band(
                pen,
                cx,
                middle,
                radius_x,
                radius_y,
                2.0 * math.pi,
                0.0,
                stroke,
                segments=32,
            )
            line(cx, base, cx, cap_height)
        elif codepoint == 0x03A8:  # Psi
            join_y = middle + width * 0.05
            line(width * 0.22, cap_height, cx, join_y)
            line(width * 0.78, cap_height, cx, join_y)
            line(cx, cap_height, cx, base)
        elif codepoint == 0x03A9:  # Omega
            radius_x = width * 0.31
            radius_y = cap_height - base
            _ellipse_arc_band(
                pen,
                cx,
                base,
                radius_x,
                radius_y,
                math.pi,
                0.0,
                stroke,
                segments=32,
            )
            line(cx - radius_x, base, width * 0.08, base)
            line(cx + radius_x, base, width * 0.92, base)
        else:
            raise ValueError(f"Unsupported Greek capital: U+{codepoint:04X}")

    return builder


def _build_greek_delta(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width * 0.52
    cy = bottom + (top - bottom) * 0.31
    radius_x = width * 0.29
    radius_y = width * 0.31
    stroke = max(84.0, width * 0.072)
    _ellipse_arc_band(
        pen, cx, cy, radius_x, radius_y, 2.0 * math.pi, 0.0, stroke, segments=32
    )
    _stroke_segment(
        pen,
        cx + radius_x * 0.38,
        cy + radius_y * 0.82,
        cx - radius_x * 0.30,
        cy + radius_y * 1.55,
        stroke,
    )
    _stroke_segment(
        pen,
        cx - radius_x * 0.30,
        cy + radius_y * 1.55,
        cx + radius_x * 0.55,
        cy + radius_y * 1.75,
        stroke,
    )


def _build_greek_epsilon(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width * 0.52
    cy = bottom + (top - bottom) * 0.40
    radius_x = width * 0.31
    radius_y = width * 0.30
    stroke = max(84.0, width * 0.072)
    _ellipse_arc_band(
        pen,
        cx,
        cy,
        radius_x,
        radius_y,
        math.pi * 1.72,
        math.pi * 0.28,
        stroke,
        segments=28,
    )
    _rect(
        pen,
        cx - radius_x,
        cy - stroke / 2.0,
        cx + radius_x * 0.72,
        cy + stroke / 2.0,
    )


def _build_greek_letter(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        if codepoint == 0x03B4:
            _build_greek_delta(font, pen, width, bottom, top)
            return
        if codepoint == 0x03B5:
            _build_greek_epsilon(font, pen, width, bottom, top)
            return

        height = top - bottom
        base = bottom + height * 0.20
        x_height = bottom + height * 0.57
        ascender = bottom + height * 0.76
        descender = bottom + height * 0.08
        middle = (base + x_height) / 2.0
        stroke = max(84.0, width * 0.072)
        cx = width / 2.0

        def line(x0: float, y0: float, x1: float, y1: float) -> None:
            _stroke_segment(pen, x0, y0, x1, y1, stroke)

        def arc(
            arc_cx: float,
            arc_cy: float,
            radius_x: float,
            radius_y: float,
            start: float,
            end: float,
        ) -> None:
            _ellipse_arc_band(
                pen,
                arc_cx,
                arc_cy,
                radius_x,
                radius_y,
                end,
                start,
                stroke,
                segments=24,
            )

        def oval(
            oval_cx: float, oval_cy: float, radius_x: float, radius_y: float
        ) -> None:
            arc(oval_cx, oval_cy, radius_x, radius_y, 0.0, 2.0 * math.pi)

        if codepoint == 0x03B1:  # alpha
            oval(width * 0.47, middle, width * 0.27, (x_height - base) * 0.48)
            line(width * 0.70, base, width * 0.73, x_height)
        elif codepoint == 0x03B2:  # beta
            line(width * 0.30, descender, width * 0.30, ascender)
            oval(width * 0.51, ascender - width * 0.23, width * 0.22, width * 0.22)
            oval(width * 0.53, base + width * 0.24, width * 0.25, width * 0.24)
        elif codepoint == 0x03B3:  # gamma
            line(width * 0.23, x_height, cx, middle)
            line(width * 0.77, x_height, cx, middle)
            line(cx, middle, width * 0.43, descender)
        elif codepoint == 0x03B6:  # zeta
            line(width * 0.25, ascender, width * 0.76, ascender)
            line(width * 0.76, ascender, width * 0.30, middle)
            line(width * 0.30, middle, width * 0.70, base)
            line(width * 0.70, base, width * 0.48, descender)
            line(width * 0.48, descender, width * 0.72, descender)
        elif codepoint == 0x03B7:  # eta
            line(width * 0.27, base, width * 0.27, x_height)
            line(width * 0.27, x_height, width * 0.70, x_height)
            line(width * 0.70, x_height, width * 0.70, descender)
        elif codepoint == 0x03B8:  # theta
            oval(cx, (base + ascender) / 2.0, width * 0.28, (ascender - base) * 0.48)
            line(width * 0.30, middle, width * 0.70, middle)
        elif codepoint == 0x03B9:  # iota
            line(width * 0.50, x_height, width * 0.50, base + stroke * 0.35)
            line(width * 0.50, base + stroke * 0.35, width * 0.61, base)
        elif codepoint == 0x03BA:  # kappa
            line(width * 0.28, base, width * 0.28, x_height)
            line(width * 0.28, middle, width * 0.73, x_height)
            line(width * 0.28, middle, width * 0.76, base)
        elif codepoint == 0x03BB:  # lamda
            line(width * 0.23, base, width * 0.55, ascender)
            line(width * 0.55, ascender, width * 0.79, base)
        elif codepoint == 0x03BC:  # mu
            line(width * 0.25, descender, width * 0.25, x_height)
            arc(cx, base + width * 0.24, width * 0.25, width * 0.24, math.pi, 2.0 * math.pi)
            line(width * 0.75, base + width * 0.24, width * 0.75, x_height)
        elif codepoint == 0x03BD:  # nu
            line(width * 0.23, x_height, cx, base)
            line(cx, base, width * 0.77, x_height)
        elif codepoint == 0x03BE:  # xi
            line(width * 0.27, ascender, width * 0.73, ascender)
            line(width * 0.73, ascender, width * 0.34, middle + width * 0.16)
            line(width * 0.34, middle + width * 0.16, width * 0.68, middle)
            line(width * 0.68, middle, width * 0.32, base)
            line(width * 0.32, base, width * 0.68, descender)
            line(width * 0.68, descender, width * 0.78, descender + stroke)
        elif codepoint == 0x03BF:  # omicron
            oval(cx, middle, width * 0.29, (x_height - base) * 0.48)
        elif codepoint == 0x03C0:  # pi
            line(width * 0.20, x_height, width * 0.80, x_height)
            line(width * 0.29, x_height, width * 0.29, base)
            line(width * 0.71, x_height, width * 0.71, base)
        elif codepoint == 0x03C1:  # rho
            line(width * 0.28, descender, width * 0.28, x_height)
            oval(width * 0.52, middle + width * 0.03, width * 0.25, width * 0.27)
        elif codepoint == 0x03C2:  # final sigma
            arc(cx, middle, width * 0.29, (x_height - base) * 0.48, math.pi * 0.22, math.pi * 1.62)
            line(width * 0.54, base + stroke, width * 0.70, descender)
            line(width * 0.70, descender, width * 0.55, descender - stroke * 0.45)
        elif codepoint == 0x03C3:  # sigma
            oval(width * 0.48, middle, width * 0.28, (x_height - base) * 0.48)
            line(width * 0.48, x_height, width * 0.78, x_height)
        elif codepoint == 0x03C4:  # tau
            line(width * 0.21, x_height, width * 0.79, x_height)
            line(cx, x_height, cx, base)
        elif codepoint == 0x03C5:  # upsilon
            line(width * 0.25, x_height, width * 0.25, base + width * 0.23)
            arc(cx, base + width * 0.23, width * 0.25, width * 0.23, math.pi, 2.0 * math.pi)
            line(width * 0.75, base + width * 0.23, width * 0.75, x_height)
        elif codepoint == 0x03C6:  # phi
            oval(cx, middle, width * 0.29, (x_height - base) * 0.43)
            line(cx, descender, cx, x_height + width * 0.18)
        elif codepoint == 0x03C7:  # chi
            line(width * 0.24, x_height, width * 0.74, descender)
            line(width * 0.76, x_height, width * 0.26, descender)
        elif codepoint == 0x03C8:  # psi
            line(width * 0.23, x_height, width * 0.23, base + width * 0.22)
            arc(cx, base + width * 0.22, width * 0.27, width * 0.22, math.pi, 2.0 * math.pi)
            line(width * 0.77, base + width * 0.22, width * 0.77, x_height)
            line(cx, descender, cx, x_height + width * 0.14)
        elif codepoint == 0x03C9:  # omega
            arc(width * 0.38, middle, width * 0.18, (x_height - base) * 0.48, math.pi, 2.0 * math.pi)
            arc(width * 0.62, middle, width * 0.18, (x_height - base) * 0.48, math.pi, 2.0 * math.pi)
            line(width * 0.20, middle, width * 0.20, x_height)
            line(width * 0.80, middle, width * 0.80, x_height)
        else:
            raise ValueError(f"Unsupported Greek letter: U+{codepoint:04X}")

    return builder


def _light_box_weight(width: int) -> float:
    return max(82.0, width * 0.0667)


def _heavy_box_weight(width: int) -> float:
    return max(190.0, width * 0.165)


def _build_light_horizontal(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    mid_y = (bottom + top) / 2.0
    overdraw = max(16.0, width * 0.014)
    _rect(pen, -overdraw, mid_y - weight / 2.0, width + overdraw, mid_y + weight / 2.0)


def _build_light_vertical(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    mid_x = width / 2.0
    overdraw = max(16.0, width * 0.014)
    _rect(pen, mid_x - weight / 2.0, bottom - overdraw, mid_x + weight / 2.0, top + overdraw)


def _build_heavy_vertical(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _heavy_box_weight(width)
    mid_x = width / 2.0
    overdraw = max(16.0, width * 0.014)
    _rect(pen, mid_x - weight / 2.0, bottom - overdraw, mid_x + weight / 2.0, top + overdraw)


def _build_double_dash_horizontal(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    mid_y = (bottom + top) / 2.0
    # Two equal dashes, with equal-looking gaps both within and between cells.
    _rect(pen, 0.0, mid_y - weight / 2.0, width * 5.0 / 12.0, mid_y + weight / 2.0)
    _rect(pen, width * 7.0 / 12.0, mid_y - weight / 2.0, width, mid_y + weight / 2.0)


def _build_double_horizontal(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    mid_y = (bottom + top) / 2.0
    offset = width * 0.105
    overdraw = max(16.0, width * 0.014)
    for line_y in (mid_y - offset, mid_y + offset):
        _rect(
            pen,
            -overdraw,
            line_y - weight / 2.0,
            width + overdraw,
            line_y + weight / 2.0,
        )


def _build_double_vertical(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    mid_x = width / 2.0
    offset = width * 0.105
    overdraw = max(16.0, width * 0.014)
    for line_x in (mid_x - offset, mid_x + offset):
        _rect(
            pen,
            line_x - weight / 2.0,
            bottom - overdraw,
            line_x + weight / 2.0,
            top + overdraw,
        )


def _build_arc_corner(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = _light_box_weight(width)
        radius_x = width / 2.0
        radius_y = (top - bottom) / 2.0
        if codepoint == 0x256D:  # ╭ down and right
            cx, cy, start, end = width, bottom, math.pi, math.pi / 2.0
        elif codepoint == 0x256E:  # ╮ down and left
            cx, cy, start, end = 0.0, bottom, 0.0, math.pi / 2.0
        elif codepoint == 0x256F:  # ╯ up and left
            cx, cy, start, end = 0.0, top, -math.pi / 2.0, 0.0
        elif codepoint == 0x2570:  # ╰ up and right
            cx, cy, start, end = width, top, math.pi, 3.0 * math.pi / 2.0
        else:
            raise ValueError(f"Unsupported arc-corner codepoint: U+{codepoint:04X}")
        _ellipse_arc_band(
            pen, cx, cy, radius_x, radius_y, start, end, weight, segments=24
        )

    return builder


def _build_dentistry_bottom_right(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    # U+23BF is used by Claude Code as a light branch/continuation elbow.
    weight = _light_box_weight(width)
    height = top - bottom
    x = width * 0.495
    y_turn = bottom + height * 0.135
    y_top = bottom + height * 0.88
    x_end = width + max(18.0, width * 0.02)
    _rect(pen, x - weight / 2.0, y_turn, x + weight / 2.0, y_top)
    _rect(pen, x, y_turn - weight / 2.0, x_end, y_turn + weight / 2.0)
    # Fill the inside of the bend so rasterizers do not leave a pinhole.
    _rect(pen, x - weight / 2.0, y_turn - weight / 2.0, x + weight / 2.0, y_turn + weight / 2.0)


def _build_telephone_recorder(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width * 0.56
    cy = bottom + (top - bottom) * 0.43
    outer = width * 0.34
    stroke = max(88.0, width * 0.076)
    _stroke_segment(
        pen,
        cx - outer * 0.68,
        cy - outer * 0.68,
        width * 0.12,
        cy - outer * 1.28,
        stroke,
    )
    _ring(pen, cx, cy, outer, outer - stroke)


def _build_very_small_square(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    side = width * 0.317
    x0 = (width - side) / 2.0
    height = top - bottom
    y0 = bottom + height * 0.31
    _rect(pen, x0, y0, x0 + side, y0 + side)


def _build_white_medium_square(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    side = width * 0.68
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    _square_ring(
        pen,
        cx - side / 2.0,
        cy - side / 2.0,
        cx + side / 2.0,
        cy + side / 2.0,
        width * 0.085,
    )


def _build_down_right_arrow(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    # Geometric rendering of ↳ with an open, light arrowhead.
    weight = _light_box_weight(width)
    height = top - bottom
    x_stem = width * 0.267
    y_low = bottom + height * 0.25
    y_high = bottom + height * 0.71
    tip_x = width * 0.825
    head_back_x = width * 0.465
    head_half = height * 0.09
    shaft_end = tip_x - weight * 0.45
    _rect(pen, x_stem - weight / 2.0, y_low, x_stem + weight / 2.0, y_high)
    _rect(pen, x_stem, y_low - weight / 2.0, shaft_end, y_low + weight / 2.0)
    _rect(
        pen,
        x_stem - weight / 2.0,
        y_low - weight / 2.0,
        x_stem + weight / 2.0,
        y_low + weight / 2.0,
    )
    _stroke_segment(pen, head_back_x, y_low + head_half, tip_x, y_low, weight * 0.82)
    _stroke_segment(pen, head_back_x, y_low - head_half, tip_x, y_low, weight * 0.82)


def _build_bent_tip_arrow(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        if codepoint not in (0x21B0, 0x21B1, 0x21B2):
            raise ValueError(f"Unsupported bent-tip arrow: U+{codepoint:04X}")
        left = codepoint in (0x21B0, 0x21B2)
        up = codepoint in (0x21B0, 0x21B1)
        # Reflect ↳ across the cell horizontally and between its stem endpoints
        # vertically. Keep filled contours clockwise after an odd reflection.
        destination = ReverseContourPen(pen) if left != up else pen
        transform = Transform(
            -1 if left else 1,
            0,
            0,
            -1 if up else 1,
            width if left else 0,
            2 * bottom + (top - bottom) * (0.25 + 0.71) if up else 0,
        )
        _build_down_right_arrow(
            font, TransformPen(destination, transform), width, bottom, top
        )

    return builder


def _build_corner_arrow(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = _light_box_weight(width)
        height = top - bottom
        if codepoint == 0x21B4:
            x_turn = width * 0.70
            y_turn = bottom + height * 0.68
            y_tip = bottom + height * 0.25
            _rect(
                pen, width * 0.14, y_turn - weight / 2,
                x_turn + weight / 2, y_turn + weight / 2,
            )
            _rect(
                pen, x_turn - weight / 2, y_tip + weight * 0.45,
                x_turn + weight / 2, y_turn,
            )
            for x_back in (x_turn - width * 0.22, x_turn + width * 0.22):
                _stroke_segment(
                    pen, x_back, y_tip + height * 0.15,
                    x_turn, y_tip, weight * 0.82,
                )
        elif codepoint == 0x21B5:
            # ↵ has a broad horizontal return stroke and a shorter vertical
            # tail than the long downward stem of ↲.
            x_turn = width * 0.80
            x_tip = width * 0.14
            y_turn = bottom + height * 0.37
            _rect(
                pen, x_turn - weight / 2, y_turn,
                x_turn + weight / 2, bottom + height * 0.71,
            )
            _rect(
                pen, x_tip + weight * 0.45, y_turn - weight / 2,
                x_turn + weight / 2, y_turn + weight / 2,
            )
            for y_back in (y_turn - height * 0.10, y_turn + height * 0.10):
                _stroke_segment(
                    pen, width * 0.38, y_back, x_tip, y_turn, weight * 0.82
                )
        else:
            raise ValueError(f"Unsupported corner arrow: U+{codepoint:04X}")

    return builder


def _build_hook_arrow(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        if codepoint not in (0x21A9, 0x21AA):
            raise ValueError(f"Unsupported hook arrow: U+{codepoint:04X}")
        if codepoint == 0x21AA:
            pen = TransformPen(ReverseContourPen(pen), Transform(-1, 0, 0, 1, width, 0))
        weight = _light_box_weight(width)
        height = top - bottom
        x_tip = width * 0.14
        x_hook = width * 0.70
        y = bottom + height * 0.42
        radius_y = height * 0.10
        _rect(pen, x_tip + weight * 0.45, y - weight / 2, x_hook, y + weight / 2)
        _ellipse_arc_band(
            pen, x_hook, y + radius_y, width * 0.16, radius_y,
            math.pi / 2, -math.pi / 2, weight,
        )
        for y_back in (y - height * 0.10, y + height * 0.10):
            _stroke_segment(
                pen, width * 0.38, y_back, x_tip, y, weight * 0.82
            )

    return builder


def _build_basic_arrow(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = _light_box_weight(width)
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.46
        x0, x1 = width * 0.14, width * 0.86
        y0, y1 = bottom + (top - bottom) * 0.17, bottom + (top - bottom) * 0.75
        head_x = width * 0.22
        head_y = (top - bottom) * 0.12

        if codepoint in (0x2190, 0x2192, 0x2194):
            _rect(pen, x0, cy - weight / 2, x1, cy + weight / 2)
            if codepoint in (0x2192, 0x2194):
                _stroke_segment(pen, x1 - head_x, cy + head_y, x1, cy, weight)
                _stroke_segment(pen, x1 - head_x, cy - head_y, x1, cy, weight)
            if codepoint in (0x2190, 0x2194):
                _stroke_segment(pen, x0 + head_x, cy + head_y, x0, cy, weight)
                _stroke_segment(pen, x0 + head_x, cy - head_y, x0, cy, weight)
        elif codepoint in (0x2191, 0x2193, 0x2195):
            _rect(pen, cx - weight / 2, y0, cx + weight / 2, y1)
            if codepoint in (0x2191, 0x2195):
                _stroke_segment(pen, cx - head_x, y1 - head_y, cx, y1, weight)
                _stroke_segment(pen, cx + head_x, y1 - head_y, cx, y1, weight)
            if codepoint in (0x2193, 0x2195):
                _stroke_segment(pen, cx - head_x, y0 + head_y, cx, y0, weight)
                _stroke_segment(pen, cx + head_x, y0 + head_y, cx, y0, weight)
        elif codepoint in (0x2196, 0x2197, 0x2198, 0x2199):
            west = codepoint in (0x2196, 0x2199)
            north = codepoint in (0x2196, 0x2197)
            tip_x, tail_x = (x0, x1) if west else (x1, x0)
            tip_y, tail_y = (y1, y0) if north else (y0, y1)
            head_base_x = tip_x + (head_x if west else -head_x)
            head_base_y = tip_y + (-head_y if north else head_y)
            _stroke_segment(pen, tail_x, tail_y, tip_x, tip_y, weight)
            _stroke_segment(pen, tip_x, tip_y, head_base_x, tip_y, weight)
            _stroke_segment(pen, tip_x, tip_y, tip_x, head_base_y, weight)
        else:
            raise ValueError(f"Unsupported basic arrow: U+{codepoint:04X}")

    return builder


def _build_wave_arrow(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = _light_box_weight(width)
        height = top - bottom
        cy = bottom + height * 0.46
        x0, x1 = width * 0.12, width * 0.88
        amplitude = height * 0.065
        head_x = width * 0.20
        head_y = height * 0.105
        segments = 16
        points = [
            (
                x0 + (x1 - x0) * index / segments,
                cy + amplitude * math.sin(4.0 * math.pi * index / segments),
            )
            for index in range(segments + 1)
        ]
        upper = []
        lower = []
        for index, (x, y) in enumerate(points):
            previous = points[max(0, index - 1)]
            following = points[min(segments, index + 1)]
            dx = following[0] - previous[0]
            dy = following[1] - previous[1]
            length = math.hypot(dx, dy)
            nx = -dy / length * weight / 2.0
            ny = dx / length * weight / 2.0
            upper.append((x + nx, y + ny))
            lower.append((x - nx, y - ny))
        _polygon(pen, (*upper, *reversed(lower)))

        if codepoint in (0x219C, 0x21AD):
            _stroke_segment(pen, x0 + head_x, cy + head_y, x0, cy, weight)
            _stroke_segment(pen, x0 + head_x, cy - head_y, x0, cy, weight)
        if codepoint in (0x219D, 0x21AD):
            _stroke_segment(pen, x1 - head_x, cy + head_y, x1, cy, weight)
            _stroke_segment(pen, x1 - head_x, cy - head_y, x1, cy, weight)
        if codepoint not in (0x219C, 0x219D, 0x21AD):
            raise ValueError(f"Unsupported wave arrow: U+{codepoint:04X}")

    return builder


def _build_downwards_zigzag_arrow(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    weight = _light_box_weight(width)
    height = top - bottom
    cx = width / 2.0
    y0, y1 = bottom + height * 0.18, bottom + height * 0.76
    offset = width * 0.14
    head_x = width * 0.21
    head_y = height * 0.115
    points = (
        (cx, y1),
        (cx - offset, y1 - height * 0.145),
        (cx + offset, y1 - height * 0.29),
        (cx - offset, y1 - height * 0.435),
        (cx, y0),
    )
    for start, end in zip(points, points[1:]):
        _stroke_segment(pen, *start, *end, weight)
    _stroke_segment(pen, cx - head_x, y0 + head_y, cx, y0, weight)
    _stroke_segment(pen, cx + head_x, y0 + head_y, cx, y0, weight)


def _build_exchange_arrows(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    """Build U+21C6 with a left arrow above a right arrow."""
    weight = _light_box_weight(width)
    x0, x1 = width * 0.12, width * 0.88
    upper_y = bottom + (top - bottom) * 0.59
    lower_y = bottom + (top - bottom) * 0.33
    head_x = width * 0.22
    head_y = (top - bottom) * 0.075

    _rect(pen, x0, upper_y - weight / 2, x1, upper_y + weight / 2)
    _stroke_segment(pen, x0 + head_x, upper_y + head_y, x0, upper_y, weight)
    _stroke_segment(pen, x0 + head_x, upper_y - head_y, x0, upper_y, weight)
    _rect(pen, x0, lower_y - weight / 2, x1, lower_y + weight / 2)
    _stroke_segment(pen, x1 - head_x, lower_y + head_y, x1, lower_y, weight)
    _stroke_segment(pen, x1 - head_x, lower_y - head_y, x1, lower_y, weight)


def _build_upwards_white_arrow(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    height = top - bottom
    tip_y = bottom + height * 0.83
    shoulder_y = bottom + height * 0.51
    base_y = bottom + height * 0.18
    head_half = width * 0.45
    stem_half = width * 0.17
    outer = (
        (cx, tip_y),
        (cx + head_half, shoulder_y),
        (cx + stem_half, shoulder_y),
        (cx + stem_half, base_y),
        (cx - stem_half, base_y),
        (cx - stem_half, shoulder_y),
        (cx - head_half, shoulder_y),
    )
    inner = (
        (cx, tip_y - height * 0.072),
        (cx + width * 0.315, shoulder_y + height * 0.04),
        (cx + width * 0.09, shoulder_y + height * 0.04),
        (cx + width * 0.09, base_y + height * 0.04),
        (cx - width * 0.09, base_y + height * 0.04),
        (cx - width * 0.09, shoulder_y + height * 0.04),
        (cx - width * 0.315, shoulder_y + height * 0.04),
    )
    _polygon_ring(pen, outer, inner)


def _build_empty_set(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    radius_x = width * 0.34
    radius_y = width * 0.43
    stroke = max(84.0, width * 0.072)
    _ellipse_arc_band(
        pen, cx, cy, radius_x, radius_y, 0.0, 2.0 * math.pi, stroke, segments=32
    )
    _stroke_segment(
        pen,
        cx - radius_x * 1.05,
        cy - radius_y * 1.05,
        cx + radius_x * 1.05,
        cy + radius_y * 1.05,
        stroke,
    )


def _build_membership(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        reflected = codepoint in (0x220B, 0x220C)
        negated = codepoint in (0x2209, 0x220C)
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.42
        radius_x = width * 0.31
        radius_y = width * 0.36
        stroke = max(82.0, width * 0.069)
        if reflected:
            start, end = 2.0 * math.pi / 3.0, -2.0 * math.pi / 3.0
            bar_x0, bar_x1 = cx - radius_x * 0.90, cx + radius_x
        else:
            start, end = math.pi / 3.0, 5.0 * math.pi / 3.0
            bar_x0, bar_x1 = cx - radius_x, cx + radius_x * 0.90
        _ellipse_arc_band(
            pen, cx, cy, radius_x, radius_y, start, end, stroke, segments=24
        )
        _rect(pen, bar_x0, cy - stroke / 2.0, bar_x1, cy + stroke / 2.0)
        if negated:
            _stroke_segment(
                pen,
                cx - radius_x * 1.15,
                cy - radius_y * 1.18,
                cx + radius_x * 1.15,
                cy + radius_y * 1.18,
                stroke * 0.82,
            )

    return builder


def _build_set_union(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.45
        radius_x = width * 0.34
        radius_y = width * 0.42
        stroke = max(84.0, width * 0.072)
        if codepoint == 0x2229:
            start, end = 0.0, math.pi
        elif codepoint == 0x222A:
            start, end = math.pi, 2.0 * math.pi
        else:
            raise ValueError(f"Unsupported set union operator: U+{codepoint:04X}")
        _ellipse_arc_band(
            pen, cx, cy, radius_x, radius_y, start, end, stroke, segments=20
        )

    return builder


def _build_subset_relation(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        reflected = codepoint in (0x2283, 0x2285, 0x2287)
        negated = codepoint in (0x2284, 0x2285)
        includes_equal = codepoint in (0x2286, 0x2287)
        cx = width / 2.0
        cy = bottom + (top - bottom) * (0.51 if includes_equal else 0.42)
        radius_x = width * 0.31
        radius_y = width * (0.27 if includes_equal else 0.38)
        stroke = max(82.0, width * 0.069)
        if reflected:
            start, end = 2.0 * math.pi / 3.0, -2.0 * math.pi / 3.0
        else:
            start, end = math.pi / 3.0, 5.0 * math.pi / 3.0
        _ellipse_arc_band(
            pen, cx, cy, radius_x, radius_y, start, end, stroke, segments=24
        )
        if includes_equal:
            y0 = bottom + (top - bottom) * 0.20
            for y in (y0, y0 + stroke * 1.65):
                _rect(
                    pen,
                    cx - radius_x,
                    y - stroke / 2.0,
                    cx + radius_x,
                    y + stroke / 2.0,
                )
        if negated:
            _stroke_segment(
                pen,
                cx - radius_x * 1.15,
                cy - radius_y * 1.18,
                cx + radius_x * 1.15,
                cy + radius_y * 1.18,
                stroke * 0.82,
            )

    return builder


def _build_box_junction(codepoint: int) -> Builder:
    directions: Mapping[int, tuple[str, ...]] = {
        0x250C: ("down", "right"),
        0x2510: ("down", "left"),
        0x2514: ("up", "right"),
        0x2518: ("up", "left"),
        0x251C: ("up", "down", "right"),
        0x2524: ("up", "down", "left"),
        0x252C: ("down", "left", "right"),
        0x2534: ("up", "left", "right"),
    }

    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        weight = _light_box_weight(width)
        cx = width / 2.0
        cy = (bottom + top) / 2.0
        overdraw = max(16.0, width * 0.014)
        for direction in directions[codepoint]:
            if direction == "left":
                _rect(pen, -overdraw, cy - weight / 2, cx + weight / 2, cy + weight / 2)
            elif direction == "right":
                _rect(pen, cx - weight / 2, cy - weight / 2, width + overdraw, cy + weight / 2)
            elif direction == "up":
                _rect(pen, cx - weight / 2, cy - weight / 2, cx + weight / 2, top + overdraw)
            else:
                _rect(pen, cx - weight / 2, bottom - overdraw, cx + weight / 2, cy + weight / 2)

    return builder


def _build_braille(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        bits = codepoint - 0x2800
        x_positions = (width * 0.34, width * 0.66)
        y_positions = tuple(
            bottom + (top - bottom) * fraction for fraction in (0.70, 0.54, 0.38, 0.22)
        )
        dot_positions = {
            1: (0, 0),
            2: (0, 1),
            3: (0, 2),
            4: (1, 0),
            5: (1, 1),
            6: (1, 2),
            7: (0, 3),
            8: (1, 3),
        }
        radius = max(72.0, width * 0.062)
        for dot, (column, row) in dot_positions.items():
            if bits & (1 << (dot - 1)):
                _circle(
                    pen,
                    x_positions[column],
                    y_positions[row],
                    radius,
                    clockwise=True,
                )

    return builder


def _build_pause(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    visual_bottom = 40
    visual_top = min(1480, top - 70)
    bar_width = max(165, round(width * 0.155))
    gap = max(145, round(width * 0.145))
    cx = width / 2.0
    _rect(pen, cx - gap / 2 - bar_width, visual_bottom, cx - gap / 2, visual_top)
    _rect(pen, cx + gap / 2, visual_bottom, cx + gap / 2 + bar_width, visual_top)


def _build_play(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    y0 = -10
    y1 = min(1420, top - 50)
    x0 = round(width * 0.22)
    x1 = round(width * 0.86)
    _polygon(pen, ((x0, y0), (x0, y1), (x1, (y0 + y1) / 2.0)))


def _build_angle_bracket(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        left = codepoint in (0x276C, 0x276E, 0x2770, 0x27E8)
        if codepoint in (0x276C, 0x276D):
            base_x, tip_x = width * 0.25, width * 0.72
            y_low, y_high = 80, min(1390, top - 80)
            thickness = max(100, width * 0.085)
        elif codepoint in (0x276E, 0x276F):
            base_x, tip_x = width * 0.16, width * 0.78
            y_low, y_high = -15, min(1485, top - 60)
            thickness = max(145, width * 0.125)
        elif codepoint in (0x2770, 0x2771):
            base_x, tip_x = width * 0.24, width * 0.72
            y_low, y_high = -45, min(1530, top - 35)
            thickness = max(140, width * 0.12)
        elif codepoint in (0x27E8, 0x27E9):
            base_x, tip_x = width * 0.31, width * 0.68
            y_low, y_high = -55, min(1540, top - 30)
            thickness = max(78, width * 0.065)
        else:
            raise ValueError(f"Unsupported angle bracket: U+{codepoint:04X}")

        y_mid = (y_low + y_high) / 2.0
        points = (
            (base_x, y_low + thickness),
            (tip_x - thickness * 0.18, y_mid),
            (base_x, y_high - thickness),
            (base_x + thickness, y_high),
            (tip_x + thickness, y_mid),
            (base_x + thickness, y_low),
        )
        if left:
            points = tuple((width - x, y) for x, y in points)
        _polygon(pen, points)

    return builder


def _build_joined_squares(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    stroke = max(85, round(width * 0.075))
    size = round(width * 0.60)
    back_x0 = round(width * 0.10)
    back_y0 = 440
    front_x0 = round(width * 0.30)
    front_y0 = 120
    _square_ring(pen, back_x0, back_y0, back_x0 + size, back_y0 + size, stroke)
    _square_ring(
        pen, front_x0, front_y0, front_x0 + size, front_y0 + size, stroke
    )


def _build_square_with_small_square(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    side = round(width * 0.80)
    x0 = (width - side) / 2.0
    y0 = 80
    stroke = max(90, round(width * 0.08))
    _square_ring(pen, x0, y0, x0 + side, y0 + side, stroke)
    inner_side = round(side * 0.31)
    inner_x0 = width / 2.0 - inner_side / 2.0
    inner_y0 = y0 + side / 2.0 - inner_side / 2.0
    _rect(pen, inner_x0, inner_y0, inner_x0 + inner_side, inner_y0 + inner_side)


def _build_parallelogram(*, outlined: bool) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        x0 = width * 0.10
        x1 = width * 0.90
        y0 = 150.0
        y1 = min(1070.0, top - 180.0)
        skew = width * 0.17
        _polygon(pen, ((x0, y0), (x0 + skew, y1), (x1, y1), (x1 - skew, y0)))

        if outlined:
            inset = max(105.0, width * 0.085)
            inner_y0 = y0 + inset
            inner_y1 = y1 - inset
            edge_shift = skew * inset / (y1 - y0)
            _polygon(
                pen,
                (
                    (x0 + inset + edge_shift, inner_y0),
                    (x1 - skew - inset + edge_shift, inner_y0),
                    (x1 - inset - edge_shift, inner_y1),
                    (x0 + skew + inset - edge_shift, inner_y1),
                ),
            )

    return builder


def _build_half_black_circle(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = 570
    outer_radius = min(width * 0.445, 550)
    stroke = max(90, width * 0.075)
    inner_radius = outer_radius - stroke
    _ring(pen, cx, cy, outer_radius, inner_radius)

    # Fill the left half inside the outlined circle.
    pen.moveTo((cx, cy + inner_radius))
    pen.lineTo((cx, cy - inner_radius))
    segments = 4
    angle = -math.pi / 2.0
    delta = -math.pi / segments
    for _ in range(segments):
        next_angle = angle + delta
        mid = (angle + next_angle) / 2.0
        control_radius = inner_radius / math.cos(abs(delta) / 2.0)
        control = (
            cx + control_radius * math.cos(mid),
            cy + control_radius * math.sin(mid),
        )
        end = (
            cx + inner_radius * math.cos(next_angle),
            cy + inner_radius * math.sin(next_angle),
        )
        pen.qCurveTo(control, end)
        angle = next_angle
    pen.closePath()


def _filled_circle_sector(
    pen: TTGlyphPen,
    cx: float,
    cy: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    *,
    segments: int = 8,
) -> None:
    points = [(cx, cy)]
    points.extend(
        (
            cx + radius * math.cos(start_angle + (end_angle - start_angle) * index / segments),
            cy + radius * math.sin(start_angle + (end_angle - start_angle) * index / segments),
        )
        for index in range(segments + 1)
    )
    _polygon(pen, points)


def _build_circle_symbol(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.42
        radius = width * 0.39
        stroke = max(84.0, width * 0.072)
        inner = radius - stroke

        if codepoint == 0x25CF:  # black circle
            _circle(pen, cx, cy, radius, clockwise=True)
            return

        _ring(pen, cx, cy, radius, inner)
        if codepoint == 0x2299:  # circled dot
            _circle(pen, cx, cy, width * 0.075, clockwise=True)
        elif codepoint == 0x25C9:  # fisheye
            _circle(pen, cx, cy, width * 0.14, clockwise=True)
        elif codepoint == 0x25CD:  # vertical fill
            fill_width = width * 0.16
            _rect(
                pen,
                cx - fill_width / 2,
                cy - inner * 0.94,
                cx + fill_width / 2,
                cy + inner * 0.94,
            )
        elif codepoint == 0x25D4:  # upper-right quadrant black
            _filled_circle_sector(pen, cx, cy, inner, 0.0, math.pi / 2.0)
        elif codepoint == 0x25CE:  # bullseye
            _ring(pen, cx, cy, width * 0.18, width * 0.10)
        elif codepoint != 0x25CB:
            raise ValueError(f"Unsupported circle symbol: U+{codepoint:04X}")

    return builder


def _build_polygon_symbol(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.42
        if codepoint == 0x25A0:  # black square
            side = width * 0.68
            _rect(pen, cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
            return

        if codepoint in DIRECTIONAL_TRIANGLES:
            direction, outlined, style = DIRECTIONAL_TRIANGLES[codepoint]
            if style == "regular":
                half_x = half_y = width * 0.39
                inner_scale = 0.68
            elif style == "small":
                half_x = half_y = width * 0.27
                inner_scale = 0.60
            else:
                half_x = width * 0.43
                half_y = width * 0.23
                inner_scale = 0.58

            def points(scale: float) -> tuple[tuple[float, float], ...]:
                hx = half_x * scale
                hy = half_y * scale
                if direction == "up":
                    return ((cx, cy + hy), (cx + hx, cy - hy), (cx - hx, cy - hy))
                if direction == "right":
                    return ((cx - hx, cy - hy), (cx - hx, cy + hy), (cx + hx, cy))
                if direction == "down":
                    return ((cx - hx, cy + hy), (cx + hx, cy + hy), (cx, cy - hy))
                return ((cx + hx, cy + hy), (cx + hx, cy - hy), (cx - hx, cy))

            outer = points(1.0)
            if outlined:
                _polygon_ring(pen, outer, points(inner_scale))
            else:
                _polygon(pen, outer)
            return

        diamond_half = {
            0x25C6: width * 0.40,
            0x2B25: width * 0.34,
            0x2B29: width * 0.25,
            0x2B2A: width * 0.20,
        }.get(codepoint, width * 0.40)
        outer = (
            (cx, cy + diamond_half),
            (cx + diamond_half, cy),
            (cx, cy - diamond_half),
            (cx - diamond_half, cy),
        )
        if codepoint in (0x25C6, 0x2B25, 0x2B29, 0x2B2A):
            _polygon(pen, outer)
        elif codepoint == 0x25C7:
            _polygon_ring(
                pen,
                outer,
                (
                    (cx, cy + diamond_half * 0.72),
                    (cx + diamond_half * 0.72, cy),
                    (cx, cy - diamond_half * 0.72),
                    (cx - diamond_half * 0.72, cy),
                ),
            )
        elif codepoint == 0x25C8:
            inner_half = diamond_half * 0.34
            _polygon_ring(
                pen,
                outer,
                (
                    (cx, cy + diamond_half * 0.72),
                    (cx + diamond_half * 0.72, cy),
                    (cx, cy - diamond_half * 0.72),
                    (cx - diamond_half * 0.72, cy),
                ),
            )
            _polygon(
                pen,
                (
                    (cx, cy + inner_half),
                    (cx + inner_half, cy),
                    (cx, cy - inner_half),
                    (cx - inner_half, cy),
                ),
            )
        elif codepoint == 0x2B16:
            inner_half = diamond_half * 0.72
            _polygon_ring(
                pen,
                outer,
                (
                    (cx, cy + inner_half),
                    (cx + inner_half, cy),
                    (cx, cy - inner_half),
                    (cx - inner_half, cy),
                ),
            )
            _polygon(pen, ((cx, cy + inner_half), (cx, cy - inner_half), (cx - inner_half, cy)))
        else:
            raise ValueError(f"Unsupported polygon symbol: U+{codepoint:04X}")

    return builder


def _build_square_family(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cx = width / 2.0
        cy = bottom + (top - bottom) * 0.42
        side = width * 0.68
        stroke = width * 0.085

        def rectangular_ring(
            x0: float, y0: float, x1: float, y1: float
        ) -> None:
            _rect(pen, x0, y0, x1, y1)
            _rect(
                pen,
                x0 + stroke,
                y0 + stroke,
                x1 - stroke,
                y1 - stroke,
                clockwise=False,
            )

        if codepoint in (0x25A1, *range(0x25A4, 0x25AA)):
            x0, x1 = cx - side / 2.0, cx + side / 2.0
            y0, y1 = cy - side / 2.0, cy + side / 2.0
            rectangular_ring(x0, y0, x1, y1)
            inset = stroke * 1.65
            ix0, ix1 = x0 + inset, x1 - inset
            iy0, iy1 = y0 + inset, y1 - inset
            line = stroke * 0.48
            if codepoint in (0x25A4, 0x25A6):
                for fraction in (0.25, 0.50, 0.75):
                    y = iy0 + (iy1 - iy0) * fraction
                    _rect(pen, ix0, y - line / 2.0, ix1, y + line / 2.0)
            if codepoint in (0x25A5, 0x25A6):
                for fraction in (0.25, 0.50, 0.75):
                    x = ix0 + (ix1 - ix0) * fraction
                    _rect(pen, x - line / 2.0, iy0, x + line / 2.0, iy1)
            if codepoint in (0x25A7, 0x25A9):
                _stroke_segment(pen, ix0, iy1, ix1, iy0, line)
                _stroke_segment(
                    pen, ix0, (iy0 + iy1) / 2.0, (ix0 + ix1) / 2.0, iy0, line
                )
                _stroke_segment(
                    pen, (ix0 + ix1) / 2.0, iy1, ix1, (iy0 + iy1) / 2.0, line
                )
            if codepoint in (0x25A8, 0x25A9):
                _stroke_segment(pen, ix0, iy0, ix1, iy1, line)
                _stroke_segment(
                    pen, ix0, (iy0 + iy1) / 2.0, (ix0 + ix1) / 2.0, iy1, line
                )
                _stroke_segment(
                    pen, (ix0 + ix1) / 2.0, iy0, ix1, (iy0 + iy1) / 2.0, line
                )
            return

        if codepoint == 0x25A2:
            x0, x1 = cx - side / 2.0, cx + side / 2.0
            y0, y1 = cy - side / 2.0, cy + side / 2.0
            _rounded_rect(pen, x0, y0, x1, y1, width * 0.10)
            _rounded_rect(
                pen,
                x0 + stroke,
                y0 + stroke,
                x1 - stroke,
                y1 - stroke,
                width * 0.045,
                clockwise=False,
            )
            return

        if codepoint in (0x25AA, 0x25AB):
            small = width * 0.34
            x0, x1 = cx - small / 2.0, cx + small / 2.0
            y0, y1 = cy - small / 2.0, cy + small / 2.0
        elif codepoint in (0x25AC, 0x25AD):
            x0, x1 = cx - width * 0.39, cx + width * 0.39
            y0, y1 = cy - width * 0.18, cy + width * 0.18
        elif codepoint in (0x25AE, 0x25AF):
            x0, x1 = cx - width * 0.18, cx + width * 0.18
            y0, y1 = cy - width * 0.39, cy + width * 0.39
        else:
            raise ValueError(f"Unsupported square-family symbol: U+{codepoint:04X}")

        if codepoint in (0x25AB, 0x25AD, 0x25AF):
            rectangular_ring(x0, y0, x1, y1)
        else:
            _rect(pen, x0, y0, x1, y1)

    return builder


def _build_dotted_circle(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    orbit = width * 0.34
    dot_radius = width * 0.043
    for index in range(12):
        angle = index * math.pi / 6.0
        _circle(
            pen,
            cx + orbit * math.cos(angle),
            cy + orbit * math.sin(angle),
            dot_radius,
            clockwise=True,
        )


def _build_corner_triangle(codepoint: int) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cy = bottom + (top - bottom) * 0.42
        x0, x1 = width * 0.12, width * 0.88
        y0, y1 = cy - width * 0.38, cy + width * 0.38
        points = {
            0x25E2: ((x0, y0), (x1, y0), (x1, y1)),
            0x25E3: ((x0, y0), (x1, y0), (x0, y1)),
            0x25E4: ((x0, y0), (x0, y1), (x1, y1)),
            0x25E5: ((x1, y0), (x0, y1), (x1, y1)),
        }
        _polygon(pen, points[codepoint])

    return builder


def _build_midline_ellipsis(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cy = bottom + (top - bottom) * 0.42
    radius = max(58.0, width * 0.052)
    for fraction in (0.23, 0.50, 0.77):
        _circle(pen, width * fraction, cy, radius, clockwise=True)


def _build_vertical_ellipsis(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    radius = max(58.0, width * 0.052)
    for offset in (-0.27, 0.0, 0.27):
        _circle(pen, cx, cy + width * offset, radius, clockwise=True)


def _build_bullet(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    _circle(pen, width / 2.0, (bottom + top) / 2.0, width * 0.347, clockwise=True)


def _build_replacement_character(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    source_name = font.getBestCmap().get(ord("?"))
    if source_name is None:
        raise ValueError("Base font has no question-mark glyph")
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    half = width * 0.44
    inner_half = half * 0.72
    _polygon_ring(
        pen,
        ((cx, cy + half), (cx + half, cy), (cx, cy - half), (cx - half, cy)),
        (
            (cx, cy + inner_half),
            (cx + inner_half, cy),
            (cx, cy - inner_half),
            (cx - inner_half, cy),
        ),
    )
    _draw_existing_glyph_fitted(
        font,
        source_name,
        pen,
        (cx - width * 0.17, cy - width * 0.25, cx + width * 0.17, cy + width * 0.25),
    )


def _build_heavy_asterisk(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    radius = width * 0.38
    weight = max(115.0, width * 0.10)
    for angle in (0.0, math.pi / 3, 2 * math.pi / 3):
        dx, dy = radius * math.cos(angle), radius * math.sin(angle)
        _stroke_segment(pen, cx - dx, cy - dy, cx + dx, cy + dy, weight)


def _build_clockwise_arrow(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    radius = width * 0.34
    weight = _light_box_weight(width)
    start = math.radians(55)
    end = math.radians(345)
    _ellipse_arc_band(pen, cx, cy, radius, radius, start, end, weight, segments=28)
    tip_x = cx + radius * math.cos(end)
    tip_y = cy + radius * math.sin(end)
    direction_x = math.sin(end)
    direction_y = -math.cos(end)
    length = width * 0.24
    half_base = width * 0.09
    back_x = tip_x - direction_x * length
    back_y = tip_y - direction_y * length
    normal_x = -direction_y
    normal_y = direction_x
    _polygon(
        pen,
        (
            (tip_x, tip_y),
            (back_x + normal_x * half_base, back_y + normal_y * half_base),
            (back_x - normal_x * half_base, back_y - normal_y * half_base),
        ),
    )


def _build_warning(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.40
    half = width * 0.43
    outer = ((cx, cy + half), (cx + half, cy - half), (cx - half, cy - half))
    inset = width * 0.10
    inner = (
        (cx, cy + half - inset * 2.0),
        (cx + half - inset * 1.55, cy - half + inset),
        (cx - half + inset * 1.55, cy - half + inset),
    )
    _polygon_ring(pen, outer, inner)
    stem_width = width * 0.09
    _rect(pen, cx - stem_width / 2, cy - width * 0.03, cx + stem_width / 2, cy + width * 0.24)
    _circle(pen, cx, cy - width * 0.23, width * 0.055, clockwise=True)


def _build_gear(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx = width / 2.0
    cy = bottom + (top - bottom) * 0.42
    outer = width * 0.31
    inner = width * 0.14
    tooth_length = width * 0.13
    tooth_width = width * 0.13
    _ring(pen, cx, cy, outer, inner)
    for index in range(8):
        angle = index * math.pi / 4
        x0 = cx + (outer - tooth_width * 0.20) * math.cos(angle)
        y0 = cy + (outer - tooth_width * 0.20) * math.sin(angle)
        x1 = cx + (outer + tooth_length) * math.cos(angle)
        y1 = cy + (outer + tooth_length) * math.sin(angle)
        _stroke_segment(pen, x0, y0, x1, y1, tooth_width)


def _build_circled_character(character: str) -> Builder:
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        cmap = font.getBestCmap()
        source_name = cmap.get(ord(character))
        if source_name is None:
            raise ValueError(f"Base font has no glyph for {character!r}")

        cx = width / 2.0
        cy = 560
        outer_radius = min(width * 0.455, 560)
        stroke = max(105, width * 0.09)
        inner_radius = outer_radius - stroke
        _ring(pen, cx, cy, outer_radius, inner_radius)

        # Keep enough air between Monaco's own letterforms and the circle.
        target = (
            cx - inner_radius * 0.72,
            cy - inner_radius * 0.70,
            cx + inner_radius * 0.72,
            cy + inner_radius * 0.70,
        )
        _draw_existing_glyph_fitted(font, source_name, pen, target)

    return builder


def _build_box_half_lines(
    codepoint: int,
) -> Builder:
    # U+2574..U+257F: light/heavy half-lines and mixed opposing half-lines.
    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        mid_x = width / 2.0
        mid_y = (bottom + top) / 2.0
        light = max(90, width * 0.075)
        heavy = _heavy_box_weight(width)
        overdraw = max(15, width * 0.015)

        def horizontal(left: bool, weight: float) -> None:
            x0 = -overdraw if left else mid_x
            x1 = mid_x if left else width + overdraw
            _rect(pen, x0, mid_y - weight / 2, x1, mid_y + weight / 2)

        def vertical(up: bool, weight: float) -> None:
            y0 = mid_y if up else bottom - overdraw
            y1 = top + overdraw if up else mid_y
            _rect(pen, mid_x - weight / 2, y0, mid_x + weight / 2, y1)

        mapping: Mapping[int, tuple[tuple[str, bool, str], ...]] = {
            0x2574: (("h", True, "light"),),
            0x2575: (("v", True, "light"),),
            0x2576: (("h", False, "light"),),
            0x2577: (("v", False, "light"),),
            0x2578: (("h", True, "heavy"),),
            0x2579: (("v", True, "heavy"),),
            0x257A: (("h", False, "heavy"),),
            0x257B: (("v", False, "heavy"),),
            0x257C: (("h", True, "light"), ("h", False, "heavy")),
            0x257D: (("v", True, "light"), ("v", False, "heavy")),
            0x257E: (("h", True, "heavy"), ("h", False, "light")),
            0x257F: (("v", True, "heavy"), ("v", False, "light")),
        }
        for axis, first_half, weight_name in mapping[codepoint]:
            weight = heavy if weight_name == "heavy" else light
            if axis == "h":
                horizontal(first_half, weight)
            else:
                vertical(first_half, weight)

    return builder


def _build_block_element(codepoint: int) -> Builder:
    """Build all 32 characters in U+2580..U+259F."""

    def builder(
        font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
    ) -> None:
        overdraw_x = max(60, width * 0.050)
        overdraw_y = max(45, width * 0.038)
        join_overlap = max(24, width * 0.020)
        x0 = -overdraw_x
        x1 = width + overdraw_x
        y0 = bottom - overdraw_y
        y1 = top + overdraw_y
        logical_height = top - bottom

        def fill_rect(rx0: float, ry0: float, rx1: float, ry1: float) -> None:
            # Slightly overlap adjacent filled regions. This suppresses the
            # one-pixel hairlines that DirectWrite/FreeType can otherwise
            # expose where independently rasterized rectangles meet.
            original = (rx0, ry0, rx1, ry1)
            rx0 -= join_overlap
            ry0 -= join_overlap
            rx1 += join_overlap
            ry1 += join_overlap
            if abs(original[0]) < 1e-6:
                rx0 = x0
            if abs(original[2] - width) < 1e-6:
                rx1 = x1
            if abs(original[1] - bottom) < 1e-6:
                ry0 = y0
            if abs(original[3] - top) < 1e-6:
                ry1 = y1
            _rect(pen, rx0, ry0, rx1, ry1)

        if codepoint == 0x2580:  # upper half
            fill_rect(0, bottom + logical_height / 2, width, top)
            return
        if 0x2581 <= codepoint <= 0x2587:  # lower 1/8 ... 7/8
            eighths = codepoint - 0x2580
            fill_rect(0, bottom, width, bottom + logical_height * eighths / 8)
            return
        if codepoint == 0x2588:  # full block
            fill_rect(0, bottom, width, top)
            return
        if 0x2589 <= codepoint <= 0x258F:  # left 7/8 ... 1/8
            eighths = 8 - (codepoint - 0x2588)
            fill_rect(0, bottom, width * eighths / 8, top)
            return
        if codepoint == 0x2590:  # right half
            fill_rect(width / 2, bottom, width, top)
            return
        if 0x2591 <= codepoint <= 0x2593:  # shade patterns
            level = codepoint - 0x2590  # 1,2,3 => 25%, 50%, 75%
            columns = 8
            rows = 8
            cell_w = width / columns
            cell_h = logical_height / rows
            for row in range(rows):
                for col in range(columns):
                    bayer = (col + 2 * row) % 4
                    fill = (
                        bayer == 0
                        if level == 1
                        else (bayer % 2 == 0 if level == 2 else bayer != 0)
                    )
                    if fill:
                        fill_rect(
                            col * cell_w,
                            bottom + row * cell_h,
                            (col + 1) * cell_w,
                            bottom + (row + 1) * cell_h,
                        )
            return
        if codepoint == 0x2594:  # upper one eighth
            fill_rect(0, top - logical_height / 8, width, top)
            return
        if codepoint == 0x2595:  # right one eighth
            fill_rect(width * 7 / 8, bottom, width, top)
            return

        mid_x = width / 2
        mid_y = bottom + logical_height / 2
        quadrants: Mapping[int, tuple[str, ...]] = {
            0x2596: ("ll",),
            0x2597: ("lr",),
            0x2598: ("ul",),
            0x2599: ("ul", "ll", "lr"),
            0x259A: ("ul", "lr"),
            0x259B: ("ul", "ur", "ll"),
            0x259C: ("ul", "ur", "lr"),
            0x259D: ("ur",),
            0x259E: ("ur", "ll"),
            0x259F: ("ur", "ll", "lr"),
        }
        boxes = {
            "ul": (0, mid_y, mid_x, top),
            "ur": (mid_x, mid_y, width, top),
            "ll": (0, bottom, mid_x, mid_y),
            "lr": (mid_x, bottom, width, mid_y),
        }
        for quadrant in quadrants[codepoint]:
            fill_rect(*boxes[quadrant])

    return builder


# ---------- font mutation ----------

def _glyph_name_for(codepoint: int, existing_names: set[str]) -> str:
    base = f"uni{codepoint:04X}"
    if base not in existing_names:
        return base
    index = 1
    while f"{base}.claude{index}" in existing_names:
        index += 1
    return f"{base}.claude{index}"


def _install_glyph(
    font: TTFont,
    codepoint: int,
    builder: Builder,
    *,
    replace: bool,
) -> bool:
    cmap = font.getBestCmap()
    if codepoint in cmap and not replace:
        return False

    glyph_order = font.getGlyphOrder()
    existing_names = set(glyph_order)
    old_name = cmap.get(codepoint)
    glyph_name = old_name if old_name is not None else _glyph_name_for(codepoint, existing_names)

    width = font["hmtx"].metrics[font.getBestCmap()[ord("M")]][0]
    bottom = int(font["hhea"].descent)
    top = int(font["hhea"].ascent)
    pen = TTGlyphPen(font.getGlyphSet())
    builder(font, pen, width, bottom, top)
    glyph = pen.glyph()

    if glyph_name not in existing_names:
        glyph_order.append(glyph_name)
        font.setGlyphOrder(glyph_order)
    font["glyf"][glyph_name] = glyph
    glyph.recalcBounds(font["glyf"])
    lsb = int(getattr(glyph, "xMin", 0))
    font["hmtx"].metrics[glyph_name] = (width, lsb)

    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap[codepoint] = glyph_name
    return True


def _rename_font(font: TTFont, family: str, version: str) -> None:
    postscript = "".join(ch for ch in family if ch.isalnum()) + "-Regular"
    full_name = f"{family} Regular"
    unique_id = f"{family} Regular; {version}; ClaudeCodeGlyphPatch"

    values = {
        1: family,
        2: "Regular",
        3: unique_id,
        4: full_name,
        5: f"Version {version}; Claude Code glyph patch",
        6: postscript,
        16: family,
        17: "Regular",
        18: full_name,
    }
    name_table = font["name"]
    for name_id, text in values.items():
        name_table.removeNames(nameID=name_id)
        # Windows Unicode, English (United States)
        name_table.setName(text, name_id, 3, 1, 0x0409)
        # Macintosh Roman, English. The family name is ASCII by construction.
        name_table.setName(text, name_id, 1, 0, 0)


def _planned_builders() -> dict[int, Builder]:
    builders: dict[int, Builder] = {
        0x2003: _build_blank,
        0x200A: _build_blank,
        0x2011: _build_existing_character("-"),
        0x202F: _build_blank,
        0x05BE: _build_hebrew_character(0x05BE),
        0x05C0: _build_hebrew_character(0x05C0),
        0x05C3: _build_hebrew_character(0x05C3),
        0x05F3: _build_hebrew_character(0x05F3),
        0x05F4: _build_hebrew_character(0x05F4),
        0x20AA: _build_hebrew_character(0x20AA),
        0x2139: _build_circled_character("i"),
        0x2190: _build_basic_arrow(0x2190),
        0x2191: _build_basic_arrow(0x2191),
        0x2192: _build_basic_arrow(0x2192),
        0x2193: _build_basic_arrow(0x2193),
        0x2194: _build_basic_arrow(0x2194),
        0x2195: _build_basic_arrow(0x2195),
        0x2196: _build_basic_arrow(0x2196),
        0x2197: _build_basic_arrow(0x2197),
        0x2198: _build_basic_arrow(0x2198),
        0x2199: _build_basic_arrow(0x2199),
        0x219C: _build_wave_arrow(0x219C),
        0x219D: _build_wave_arrow(0x219D),
        0x21A9: _build_hook_arrow(0x21A9),
        0x21AA: _build_hook_arrow(0x21AA),
        0x21AD: _build_wave_arrow(0x21AD),
        0x21AF: _build_downwards_zigzag_arrow,
        0x21B0: _build_bent_tip_arrow(0x21B0),
        0x21B1: _build_bent_tip_arrow(0x21B1),
        0x21B2: _build_bent_tip_arrow(0x21B2),
        0x21B3: _build_down_right_arrow,
        0x21B4: _build_corner_arrow(0x21B4),
        0x21B5: _build_corner_arrow(0x21B5),
        0x21BB: _build_clockwise_arrow,
        0x21C6: _build_exchange_arrows,
        0x21E7: _build_upwards_white_arrow,
        0x2205: _build_empty_set,
        0x2208: _build_membership(0x2208),
        0x2209: _build_membership(0x2209),
        0x220B: _build_membership(0x220B),
        0x220C: _build_membership(0x220C),
        0x2229: _build_set_union(0x2229),
        0x222A: _build_set_union(0x222A),
        0x2282: _build_subset_relation(0x2282),
        0x2283: _build_subset_relation(0x2283),
        0x2284: _build_subset_relation(0x2284),
        0x2285: _build_subset_relation(0x2285),
        0x2286: _build_subset_relation(0x2286),
        0x2287: _build_subset_relation(0x2287),
        0x2299: _build_circle_symbol(0x2299),
        0x22EE: _build_vertical_ellipsis,
        0x22EF: _build_midline_ellipsis,
        0x2315: _build_telephone_recorder,
        0x23BF: _build_dentistry_bottom_right,
        0x23F5: _build_play,
        0x23F8: _build_pause,
        0x2500: _build_light_horizontal,
        0x2502: _build_light_vertical,
        0x2503: _build_heavy_vertical,
        0x250C: _build_box_junction(0x250C),
        0x2510: _build_box_junction(0x2510),
        0x2514: _build_box_junction(0x2514),
        0x2518: _build_box_junction(0x2518),
        0x251C: _build_box_junction(0x251C),
        0x2524: _build_box_junction(0x2524),
        0x252C: _build_box_junction(0x252C),
        0x2534: _build_box_junction(0x2534),
        0x254C: _build_double_dash_horizontal,
        0x2550: _build_double_horizontal,
        0x2551: _build_double_vertical,
        0x256D: _build_arc_corner(0x256D),
        0x256E: _build_arc_corner(0x256E),
        0x256F: _build_arc_corner(0x256F),
        0x2570: _build_arc_corner(0x2570),
        0x25A0: _build_polygon_symbol(0x25A0),
        0x25A3: _build_square_with_small_square,
        0x25B0: _build_parallelogram(outlined=False),
        0x25B1: _build_parallelogram(outlined=True),
        0x25C6: _build_polygon_symbol(0x25C6),
        0x25C7: _build_polygon_symbol(0x25C7),
        0x25C8: _build_polygon_symbol(0x25C8),
        0x25C9: _build_circle_symbol(0x25C9),
        0x25CB: _build_circle_symbol(0x25CB),
        0x25CC: _build_dotted_circle,
        0x25CD: _build_circle_symbol(0x25CD),
        0x25CE: _build_circle_symbol(0x25CE),
        0x25CF: _build_circle_symbol(0x25CF),
        0x25D0: _build_half_black_circle,
        0x25D4: _build_circle_symbol(0x25D4),
        0x25E2: _build_corner_triangle(0x25E2),
        0x25E3: _build_corner_triangle(0x25E3),
        0x25E4: _build_corner_triangle(0x25E4),
        0x25E5: _build_corner_triangle(0x25E5),
        0x25FB: _build_white_medium_square,
        0x2699: _build_gear,
        0x26A0: _build_warning,
        0x2731: _build_heavy_asterisk,
        0x276C: _build_angle_bracket(0x276C),
        0x276D: _build_angle_bracket(0x276D),
        0x276E: _build_angle_bracket(0x276E),
        0x276F: _build_angle_bracket(0x276F),
        0x2770: _build_angle_bracket(0x2770),
        0x2771: _build_angle_bracket(0x2771),
        0x27E8: _build_angle_bracket(0x27E8),
        0x27E9: _build_angle_bracket(0x27E9),
        0x27F3: _build_clockwise_arrow,
        0x29C9: _build_joined_squares,
        0x2B16: _build_polygon_symbol(0x2B16),
        0x2B1D: _build_very_small_square,
        0x2B25: _build_polygon_symbol(0x2B25),
        0x2B29: _build_polygon_symbol(0x2B29),
        0x2B2A: _build_polygon_symbol(0x2B2A),
        0xF0A7: _build_very_small_square,
        0xF0B7: _build_bullet,
        0xFFFD: _build_replacement_character,
    }

    for codepoint in range(0x03B1, 0x03CA):
        builders[codepoint] = _build_greek_letter(codepoint)
    for codepoint in (*range(0x0391, 0x03A2), *range(0x03A3, 0x03AA)):
        builders[codepoint] = _build_greek_capital(codepoint)
    for codepoint, (sequence, horizontal_bar) in LATIN_EXTENDED_D_LIGATURES.items():
        builders[codepoint] = _build_letter_sequence(
            sequence, horizontal_bar=horizontal_bar
        )
    for codepoint, sequence in PRESENTATION_LIGATURES.items():
        builders[codepoint] = _build_letter_sequence(sequence)
    for codepoint in range(0x05D0, 0x05EB):
        builders[codepoint] = _build_hebrew_character(codepoint)
    for codepoint in DIRECTIONAL_TRIANGLES:
        builders[codepoint] = _build_polygon_symbol(codepoint)
    for codepoint in ADJACENT_SQUARE_ADDITIONS:
        builders[codepoint] = _build_square_family(codepoint)

    # Complete block-elements range; this prevents seams in TUI artwork.
    for codepoint in range(0x2580, 0x25A0):
        builders[codepoint] = _build_block_element(codepoint)

    # The terminal sample used U+2579; include its neighboring half-line set.
    for codepoint in range(0x2574, 0x2580):
        builders[codepoint] = _build_box_half_lines(codepoint)

    # OpenCode uses these cells for its classic Braille spinner and logo padding.
    braille_codepoints = (
        0x2800,
        0x2807,
        0x280B,
        0x280F,
        0x2819,
        0x2826,
        0x2827,
        0x2834,
        0x2838,
        0x2839,
        0x283C,
    )
    for codepoint in braille_codepoints:
        builders[codepoint] = _build_braille(codepoint)

    # Circled capitals, circled lowercase letters, circled zero, and 1–9.
    for offset, character in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        builders[0x24B6 + offset] = _build_circled_character(character)
    for offset, character in enumerate("abcdefghijklmnopqrstuvwxyz"):
        builders[0x24D0 + offset] = _build_circled_character(character)
    builders[0x24EA] = _build_circled_character("0")
    for digit in range(1, 10):
        builders[0x245F + digit] = _build_circled_character(str(digit))

    return builders


def patch_font(
    input_path: Path,
    output_path: Path,
    *,
    family: str,
    version: str,
    replace_existing: bool,
) -> tuple[int, list[int], list[int]]:
    font = TTFont(str(input_path), recalcBBoxes=True, recalcTimestamp=False)
    required_tables = {"glyf", "loca", "hmtx", "cmap", "name", "head", "hhea", "maxp"}
    missing_tables = sorted(required_tables.difference(font.keys()))
    if missing_tables:
        raise ValueError(
            "This script expects a TrueType-outline font. Missing tables: "
            + ", ".join(missing_tables)
        )

    widths = {advance for advance, _lsb in font["hmtx"].metrics.values()}
    if len(widths) != 1:
        raise ValueError(
            f"The input is not strictly monospaced; found {len(widths)} advance widths"
        )

    builders = _planned_builders()
    added: list[int] = []
    skipped: list[int] = []
    for codepoint, builder in sorted(builders.items()):
        if _install_glyph(font, codepoint, builder, replace=replace_existing):
            added.append(codepoint)
        else:
            skipped.append(codepoint)

    _rename_font(font, family, version)
    try:
        font["head"].fontRevision = float(version)
    except ValueError:
        pass
    font["post"].isFixedPitch = 1
    font["maxp"].numGlyphs = len(font.getGlyphOrder())
    font["hhea"].numberOfHMetrics = len(font.getGlyphOrder())

    os2 = font.get("OS/2")
    if os2 is not None:
        best_cmap = font.getBestCmap()
        os2.usFirstCharIndex = min(best_cmap)
        os2.usLastCharIndex = min(max(best_cmap), 0xFFFF)
        try:
            os2.recalcUnicodeRanges(font)
        except Exception:
            pass
        try:
            os2.recalcAvgCharWidth(font)
        except Exception:
            pass

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(output_path), reorderTables=True)

    # Re-open to ensure that the generated file compiles and all requested
    # mappings survived serialization.
    check = TTFont(str(output_path), lazy=False)
    check_cmap = check.getBestCmap()
    still_missing = sorted(cp for cp in EXPLICIT_CODEPOINTS if cp not in check_cmap)
    return len(added), skipped, still_missing


def _format_codepoint(codepoint: int) -> str:
    try:
        name = unicodedata.name(chr(codepoint))
    except ValueError:
        name = "PRIVATE USE CHARACTER"
    return f"U+{codepoint:04X} {chr(codepoint)} {name}"


def _resolve_build_identity(
    version: str, family: str | None, output: Path | None
) -> tuple[str, Path]:
    return family or f"Claudaco {version}", output or Path(f"Claudaco-{version}-Regular.ttf")


def _update_latest_symlink(output_path: Path) -> Path:
    latest = output_path.parent / "Claudaco-Regular.ttf"
    temporary = latest.with_name(latest.name + ".tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(output_path.name)
    temporary.replace(latest)
    return latest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input TrueType font")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output font path (default: Claudaco-VERSION-Regular.ttf)",
    )
    parser.add_argument(
        "--family",
        help="Installed family name (default: Claudaco VERSION)",
    )
    parser.add_argument(
        "--version", default="1.227", help="Version string (default: %(default)s)"
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace code points already present instead of preserving them",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        parser.error(f"Input font does not exist: {args.input}")
    family, output = _resolve_build_identity(args.version, args.family, args.output)

    try:
        source_font = TTFont(str(args.input), lazy=True)
        bitmap_tables = [
            tag for tag in ("EBDT", "EBLC", "CBDT", "CBLC", "sbix") if tag in source_font
        ]
        source_font.close()
        added_count, skipped, still_missing = patch_font(
            args.input,
            output,
            family=family,
            version=args.version,
            replace_existing=args.replace_existing,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote: {output.resolve()}")
    print(f"Added/replaced mappings: {added_count}")
    if bitmap_tables:
        print("Preserved embedded bitmap tables: " + ", ".join(bitmap_tables))
    else:
        print("Note: the source has no embedded bitmap strikes; the output is outline-only.")
    if skipped:
        print(f"Preserved existing mappings: {len(skipped)}")
    if still_missing:
        print("WARNING: explicit characters still missing:", file=sys.stderr)
        for codepoint in still_missing:
            print("  " + _format_codepoint(codepoint), file=sys.stderr)
        return 2

    if args.output is None:
        try:
            latest = _update_latest_symlink(output)
        except OSError as exc:
            print(f"error: could not update latest-font symlink: {exc}", file=sys.stderr)
            return 1
        print(f"Latest: {latest.resolve()} via {latest}")

    print("Verified explicit Claude Code / terminal characters:")
    for codepoint in sorted(EXPLICIT_CODEPOINTS):
        print("  " + _format_codepoint(codepoint))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
