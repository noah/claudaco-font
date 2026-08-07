#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

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

GREEK_ADDITIONS = set(range(0x03B1, 0x03CA))


class GlyphBuilderTests(unittest.TestCase):
    def build(self, codepoint: int):
        pen = TTGlyphPen(None)
        patch_claudaco._planned_builders()[codepoint](None, pen, 1229, -512, 2048)
        return pen.glyph()

    def build_source_font(self, path: Path) -> None:
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        cmap = {ord(character): f"uni{ord(character):04X}" for character in characters}
        cmap.update({0x00B7: "periodcentered", 0x03C0: "pi", 0xE0B0: "uniE0B0", 0xE0B2: "uniE0B2"})
        glyph_order = [".notdef", *cmap.values()]
        glyphs = {}
        for glyph_name in glyph_order:
            pen = TTGlyphPen(None)
            if glyph_name != ".notdef":
                patch_claudaco._rect(pen, 180, 0, 1049, 1100)
            glyphs[glyph_name] = pen.glyph()

        builder = FontBuilder(2048, isTTF=True)
        builder.setupGlyphOrder(glyph_order)
        builder.setupCharacterMap(cmap)
        builder.setupGlyf(glyphs)
        builder.setupHorizontalMetrics({name: (1229, 0) for name in glyph_order})
        builder.setupHorizontalHeader(ascent=2048, descent=-512)
        builder.setupNameTable(
            {
                "familyName": "Claudaco Test Source",
                "styleName": "Regular",
                "uniqueFontIdentifier": "Claudaco Test Source Regular",
                "fullName": "Claudaco Test Source Regular",
                "psName": "ClaudacoTestSource-Regular",
                "version": "Version 1.000",
            }
        )
        builder.setupPost(isFixedPitch=1)
        builder.setupMaxp()
        builder.save(path)

    def test_opencode_additions_are_explicit_and_planned(self) -> None:
        self.assertEqual(len(OPENCODE_ADDITIONS), 47)
        self.assertTrue(OPENCODE_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(OPENCODE_ADDITIONS <= patch_claudaco._planned_builders().keys())
        self.assertEqual(len(patch_claudaco._planned_builders()), 224)

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

    def test_greek_additions_are_explicit_and_visible(self) -> None:
        self.assertTrue(GREEK_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(GREEK_ADDITIONS <= patch_claudaco._planned_builders().keys())
        for codepoint in GREEK_ADDITIONS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_greek_contours_use_consistent_winding(self) -> None:
        for codepoint in GREEK_ADDITIONS:
            glyph = self.build(codepoint)
            recording = RecordingPen()
            glyph.draw(recording, {})
            areas = []
            area_pen = AreaPen(None)
            for operator, operands in recording.value:
                getattr(area_pen, operator)(*operands)
                if operator in ("closePath", "endPath"):
                    areas.append(area_pen.value)
                    area_pen = AreaPen(None)
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertTrue(areas)
                self.assertTrue(all(area < 0 for area in areas), areas)

    def test_patch_serializes_complete_greek_and_preserves_pi(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.ttf"
            output_path = Path(directory) / "output.ttf"
            replacement_path = Path(directory) / "replacement.ttf"
            self.build_source_font(source_path)

            source = TTFont(source_path)
            source_pi = list(source["glyf"]["pi"].getCoordinates(source["glyf"])[0])
            added, skipped, missing = patch_claudaco.patch_font(
                source_path,
                output_path,
                family="Claudaco 1.212",
                version="1.212",
                replace_existing=False,
            )
            self.assertEqual(added, 223)
            self.assertEqual(skipped, [0x03C0])
            self.assertEqual(missing, [])

            output = TTFont(output_path)
            cmap = output.getBestCmap()
            self.assertTrue(GREEK_ADDITIONS <= cmap.keys())
            self.assertEqual(
                {output["hmtx"].metrics[cmap[codepoint]][0] for codepoint in GREEK_ADDITIONS},
                {1229},
            )
            self.assertEqual(output["name"].getDebugName(1), "Claudaco 1.212")
            self.assertEqual(
                list(output["glyf"]["pi"].getCoordinates(output["glyf"])[0]), source_pi
            )

            patch_claudaco.patch_font(
                source_path,
                replacement_path,
                family="Claudaco 1.212",
                version="1.212",
                replace_existing=True,
            )
            replacement = TTFont(replacement_path)
            self.assertNotEqual(
                list(replacement["glyf"]["pi"].getCoordinates(replacement["glyf"])[0]),
                source_pi,
            )

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

    def test_telephone_recorder_has_ring_and_stem(self) -> None:
        self.assertIn(0x2315, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x2315).numberOfContours, 3)

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
            patch_claudaco._resolve_build_identity("1.212", None, None),
            ("Claudaco 1.212", Path("Claudaco-1.212-Regular.ttf")),
        )

    def test_build_identity_allows_explicit_overrides(self) -> None:
        self.assertEqual(
            patch_claudaco._resolve_build_identity(
                "1.212", "Claudaco Custom", Path("custom.ttf")
            ),
            ("Claudaco Custom", Path("custom.ttf")),
        )


if __name__ == "__main__":
    unittest.main()
