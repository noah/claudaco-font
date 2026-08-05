#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

import patch_claudaco


OPENCODE_ADDITIONS = {
    0x2190,
    0x2191,
    0x2192,
    0x2193,
    0x21BB,
    0x21C6,
    0x2299,
    0x22EF,
    0x250C,
    0x2510,
    0x2514,
    0x2518,
    0x251C,
    0x2524,
    0x252C,
    0x2534,
    0x25A0,
    0x25B3,
    0x25B6,
    0x25B8,
    0x25BC,
    0x25C6,
    0x25C8,
    0x25C9,
    0x25CB,
    0x25CD,
    0x25CF,
    0x25D4,
    0x2699,
    0x26A0,
    0x2731,
    0x27F3,
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
    0x2B16,
    0x2B25,
    0x2B29,
    0x2B2A,
}

BASIC_ARROWS = set(range(0x2190, 0x219A))

SET_THEORY_ADDITIONS = {
    0x2205,
    0x2208,
    0x2209,
    0x220B,
    0x220C,
    0x2229,
    0x222A,
    0x2282,
    0x2283,
    0x2284,
    0x2285,
    0x2286,
    0x2287,
}


class GlyphBuilderTests(unittest.TestCase):
    def build(self, codepoint: int):
        pen = TTGlyphPen(None)
        patch_claudaco._planned_builders()[codepoint](None, pen, 1229, -512, 2048)
        return pen.glyph()

    def test_opencode_additions_are_explicit_and_planned(self) -> None:
        self.assertEqual(len(OPENCODE_ADDITIONS), 47)
        self.assertTrue(OPENCODE_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(OPENCODE_ADDITIONS <= patch_claudaco._planned_builders().keys())
        self.assertEqual(len(patch_claudaco._planned_builders()), 198)

    def test_basic_arrows_are_explicit_and_visible(self) -> None:
        self.assertTrue(BASIC_ARROWS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(BASIC_ARROWS <= patch_claudaco._planned_builders().keys())
        for codepoint in BASIC_ARROWS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_upwards_white_arrow_is_outlined(self) -> None:
        self.assertIn(0x21E7, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x21E7).numberOfContours, 2)

    def test_set_theory_additions_are_explicit_and_visible(self) -> None:
        self.assertTrue(SET_THEORY_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(SET_THEORY_ADDITIONS <= patch_claudaco._planned_builders().keys())
        for codepoint in SET_THEORY_ADDITIONS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_visible_opencode_additions_have_outlines(self) -> None:
        for codepoint in OPENCODE_ADDITIONS - {0x2800}:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_blank_glyphs_have_no_ink(self) -> None:
        for codepoint in (0x2003, 0x202F, 0x2800):
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertEqual(self.build(codepoint).numberOfContours, 0)

    def test_vertical_ellipsis_has_three_dots(self) -> None:
        self.assertIn(0x22EE, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x22EE).numberOfContours, 3)

    def test_private_use_bullet_is_visible(self) -> None:
        self.assertIn(0xF0B7, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0xF0B7).numberOfContours, 1)

    def test_white_medium_square_is_outlined(self) -> None:
        self.assertIn(0x25FB, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x25FB).numberOfContours, 2)

    def test_prompt_heavy_verticals_share_horizontal_bounds(self) -> None:
        glyphs = []
        for codepoint in (0x2503, 0x2579):
            glyph = self.build(codepoint)
            glyph.recalcBounds({})
            glyphs.append(glyph)
        self.assertEqual(
            (glyphs[0].xMin, glyphs[0].xMax),
            (glyphs[1].xMin, glyphs[1].xMax),
        )

    def test_default_build_identity_is_versioned(self) -> None:
        self.assertEqual(
            patch_claudaco._resolve_build_identity("1.211", None, None),
            ("Claudaco 1.211", Path("Claudaco-1.211-Regular.ttf")),
        )

    def test_build_identity_allows_explicit_overrides(self) -> None:
        self.assertEqual(
            patch_claudaco._resolve_build_identity(
                "1.211", "Claudaco Custom", Path("custom.ttf")
            ),
            ("Claudaco Custom", Path("custom.ttf")),
        )


if __name__ == "__main__":
    unittest.main()
