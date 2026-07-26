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
as ``Claudaco 1.202`` and ``Claudaco-1.202-Regular.ttf``.
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
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


# Characters explicitly observed in the user's Claude Code / terminal output.
EXPLICIT_CODEPOINTS = {
    0x00B7,  # · MIDDLE DOT (normally already present)
    0x2190,  # ← LEFTWARDS ARROW
    0x2191,  # ↑ UPWARDS ARROW
    0x2192,  # → RIGHTWARDS ARROW
    0x2193,  # ↓ DOWNWARDS ARROW
    0x21B3,  # ↳ DOWNWARDS ARROW WITH TIP RIGHTWARDS
    0x21C6,  # ⇆ LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    0x2299,  # ⊙ CIRCLED DOT OPERATOR
    0x22EF,  # ⋯ MIDLINE HORIZONTAL ELLIPSIS
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
    0x2699,  # ⚙ GEAR
    0x26A0,  # ⚠ WARNING SIGN
    0x2731,  # ✱ HEAVY ASTERISK
    0x276F,  # ❯ HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT
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


def _build_very_small_square(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    side = width * 0.317
    x0 = (width - side) / 2.0
    height = top - bottom
    y0 = bottom + height * 0.31
    _rect(pen, x0, y0, x0 + side, y0 + side)


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


def _build_cardinal_arrow(codepoint: int) -> Builder:
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

        if codepoint == 0x2192:  # right
            _rect(pen, x0, cy - weight / 2, x1, cy + weight / 2)
            _stroke_segment(pen, x1 - head_x, cy + head_y, x1, cy, weight)
            _stroke_segment(pen, x1 - head_x, cy - head_y, x1, cy, weight)
        elif codepoint == 0x2190:  # left
            _rect(pen, x0, cy - weight / 2, x1, cy + weight / 2)
            _stroke_segment(pen, x0 + head_x, cy + head_y, x0, cy, weight)
            _stroke_segment(pen, x0 + head_x, cy - head_y, x0, cy, weight)
        elif codepoint == 0x2191:  # up
            _rect(pen, cx - weight / 2, y0, cx + weight / 2, y1)
            _stroke_segment(pen, cx - head_x, y1 - head_y, cx, y1, weight)
            _stroke_segment(pen, cx + head_x, y1 - head_y, cx, y1, weight)
        elif codepoint == 0x2193:  # down
            _rect(pen, cx - weight / 2, y0, cx + weight / 2, y1)
            _stroke_segment(pen, cx - head_x, y0 + head_y, cx, y0, weight)
            _stroke_segment(pen, cx + head_x, y0 + head_y, cx, y0, weight)
        else:
            raise ValueError(f"Unsupported cardinal arrow: U+{codepoint:04X}")

    return builder


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


def _build_small_down_triangle(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    # Matches the proportions of the previously generated Monaco Claude Code 1.1 glyph.
    _polygon(
        pen,
        (
            (width * 0.2148, 825.0),
            (width * 0.7852, 825.0),
            (width * 0.5004, 315.0),
        ),
    )


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


def _build_heavy_chevron(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cx_left = width * 0.16
    cx_mid = width * 0.78
    y_mid = 735
    y_low = -15
    y_high = min(1485, top - 60)
    thickness = max(145, width * 0.125)
    points = (
        (cx_left, y_low + thickness),
        (cx_mid - thickness * 0.18, y_mid),
        (cx_left, y_high - thickness),
        (cx_left + thickness, y_high),
        (cx_mid + thickness, y_mid),
        (cx_left + thickness, y_low),
    )
    _polygon(pen, points)


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

        if codepoint in (0x25B3, 0x25B6, 0x25B8, 0x25BC):
            small = codepoint == 0x25B8
            half = width * (0.29 if small else 0.39)
            if codepoint == 0x25B3:
                outer = ((cx, cy + half), (cx + half, cy - half), (cx - half, cy - half))
                inset = width * 0.105
                inner = (
                    (cx, cy + half - inset * 1.8),
                    (cx + half - inset * 1.45, cy - half + inset),
                    (cx - half + inset * 1.45, cy - half + inset),
                )
                _polygon_ring(pen, outer, inner)
            elif codepoint in (0x25B6, 0x25B8):
                _polygon(pen, ((cx - half, cy - half), (cx - half, cy + half), (cx + half, cy)))
            else:
                _polygon(pen, ((cx - half, cy + half), (cx + half, cy + half), (cx, cy - half)))
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


def _build_midline_ellipsis(
    font: TTFont, pen: TTGlyphPen, width: int, bottom: int, top: int
) -> None:
    cy = bottom + (top - bottom) * 0.42
    radius = max(58.0, width * 0.052)
    for fraction in (0.23, 0.50, 0.77):
        _circle(pen, width * fraction, cy, radius, clockwise=True)


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
        0x2190: _build_cardinal_arrow(0x2190),
        0x2191: _build_cardinal_arrow(0x2191),
        0x2192: _build_cardinal_arrow(0x2192),
        0x2193: _build_cardinal_arrow(0x2193),
        0x21B3: _build_down_right_arrow,
        0x21C6: _build_exchange_arrows,
        0x2299: _build_circle_symbol(0x2299),
        0x22EF: _build_midline_ellipsis,
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
        0x256D: _build_arc_corner(0x256D),
        0x256E: _build_arc_corner(0x256E),
        0x256F: _build_arc_corner(0x256F),
        0x2570: _build_arc_corner(0x2570),
        0x25A0: _build_polygon_symbol(0x25A0),
        0x25A3: _build_square_with_small_square,
        0x25B0: _build_parallelogram(outlined=False),
        0x25B1: _build_parallelogram(outlined=True),
        0x25B3: _build_polygon_symbol(0x25B3),
        0x25B6: _build_polygon_symbol(0x25B6),
        0x25B8: _build_polygon_symbol(0x25B8),
        0x25BC: _build_polygon_symbol(0x25BC),
        0x25BE: _build_small_down_triangle,
        0x25C6: _build_polygon_symbol(0x25C6),
        0x25C8: _build_polygon_symbol(0x25C8),
        0x25C9: _build_circle_symbol(0x25C9),
        0x25CB: _build_circle_symbol(0x25CB),
        0x25CD: _build_circle_symbol(0x25CD),
        0x25CF: _build_circle_symbol(0x25CF),
        0x25D0: _build_half_black_circle,
        0x25D4: _build_circle_symbol(0x25D4),
        0x2699: _build_gear,
        0x26A0: _build_warning,
        0x2731: _build_heavy_asterisk,
        0x276F: _build_heavy_chevron,
        0x27F3: _build_clockwise_arrow,
        0x29C9: _build_joined_squares,
        0x2B16: _build_polygon_symbol(0x2B16),
        0x2B1D: _build_very_small_square,
        0x2B25: _build_polygon_symbol(0x2B25),
        0x2B29: _build_polygon_symbol(0x2B29),
        0x2B2A: _build_polygon_symbol(0x2B2A),
    }

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
        "--version", default="1.202", help="Version string (default: %(default)s)"
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

    print("Verified explicit Claude Code / terminal characters:")
    for codepoint in sorted(EXPLICIT_CODEPOINTS):
        print("  " + _format_codepoint(codepoint))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
