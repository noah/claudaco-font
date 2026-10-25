#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import os
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
WAVE_ZIGZAG_ARROWS = {0x219C, 0x219D, 0x21AD, 0x21AF}
BENT_CORNER_HOOK_ARROWS = {0x21A9, 0x21AA, *range(0x21B0, 0x21B6)}
ANGLE_BRACKETS = set(range(0x276C, 0x2772)) | {0x27E8, 0x27E9}

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
GREEK_CAPITALS = set(range(0x0391, 0x03A2)) | set(range(0x03A3, 0x03AA))
GEOMETRIC_GREEK_CAPITALS = GREEK_CAPITALS - patch_claudaco.GREEK_CAPITAL_ASCII.keys()
LATIN_LIGATURES = set(patch_claudaco.LATIN_EXTENDED_D_LIGATURES) | set(
    patch_claudaco.PRESENTATION_LIGATURES
)
HEBREW_ADDITIONS = set(range(0x05D0, 0x05EB)) | {
    0x05BE,
    0x05C0,
    0x05C3,
    0x05F3,
    0x05F4,
    0x20AA,
}
SURVEYED_GEOMETRIC_SHAPES = set(range(0x25B2, 0x25C6)) | {
    0x25C7,
    0x25CC,
    0x25CE,
    0x25E2,
    0x25E3,
    0x25E4,
    0x25E5,
}
ADJACENT_SQUARE_FAMILY = set(range(0x25A0, 0x25B0))
SMALL_CIRCLE_ADDITIONS = {0x2218, 0x25E6, 0x26AC}


class GlyphBuilderTests(unittest.TestCase):
    def build(self, codepoint: int):
        pen = TTGlyphPen(None)
        patch_claudaco._planned_builders()[codepoint](None, pen, 1229, -512, 2048)
        return pen.glyph()

    def contour_areas(self, codepoint: int) -> list[float]:
        recording = RecordingPen()
        self.build(codepoint).draw(recording, {})
        areas = []
        area_pen = AreaPen(None)
        for operator, operands in recording.value:
            getattr(area_pen, operator)(*operands)
            if operator in ("closePath", "endPath"):
                areas.append(area_pen.value)
                area_pen = AreaPen(None)
        return areas

    def build_source_font(self, path: Path) -> None:
        characters = "-?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        cmap = {ord(character): f"uni{ord(character):04X}" for character in characters}
        cmap.update(
            {
                0x00B7: "periodcentered",
                0x03C0: "pi",
                0xE0B0: "uniE0B0",
                0xE0B2: "uniE0B2",
                0xFB01: "fi.source",
                0xFB02: "fl.source",
            }
        )
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
        builder.setupHorizontalMetrics(
            {name: (1229, 0 if name == ".notdef" else 180) for name in glyph_order}
        )
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
        self.assertEqual(len(patch_claudaco._planned_builders()), 370)

    def test_basic_arrows_are_explicit_and_visible(self) -> None:
        self.assertTrue(BASIC_ARROWS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(BASIC_ARROWS <= patch_claudaco._planned_builders().keys())
        for codepoint in BASIC_ARROWS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_wave_and_zigzag_arrows_are_explicit_and_visible(self) -> None:
        self.assertTrue(WAVE_ZIGZAG_ARROWS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(WAVE_ZIGZAG_ARROWS <= patch_claudaco._planned_builders().keys())
        for codepoint in WAVE_ZIGZAG_ARROWS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_bent_corner_and_hook_arrows_have_valid_distinct_outlines(self) -> None:
        self.assertTrue(BENT_CORNER_HOOK_ARROWS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        outlines = set()
        for codepoint in BENT_CORNER_HOOK_ARROWS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                glyph = self.build(codepoint)
                self.assertGreater(glyph.numberOfContours, 0)
                glyph.recalcBounds({})
                self.assertGreaterEqual(glyph.xMin, 0)
                self.assertLessEqual(glyph.xMax, 1229)
                self.assertGreaterEqual(glyph.yMin, -512)
                self.assertLessEqual(glyph.yMax, 2048)
                self.assertTrue(all(area < 0 for area in self.contour_areas(codepoint)))
                outlines.add(frozenset(glyph.coordinates))
        self.assertEqual(len(outlines), len(BENT_CORNER_HOOK_ARROWS))

    def test_angle_bracket_family_is_explicit_and_visible(self) -> None:
        self.assertTrue(ANGLE_BRACKETS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(ANGLE_BRACKETS <= patch_claudaco._planned_builders().keys())
        for codepoint in ANGLE_BRACKETS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)
        for left_codepoint, right_codepoint in (
            (0x276C, 0x276D),
            (0x276E, 0x276F),
            (0x2770, 0x2771),
            (0x27E8, 0x27E9),
        ):
            left = self.build(left_codepoint)
            right = self.build(right_codepoint)
            left.recalcBounds({})
            right.recalcBounds({})
            self.assertEqual(
                (left.xMin, left.xMax),
                (1229 - right.xMax, 1229 - right.xMin),
            )

    def test_core_hebrew_is_explicit_and_visible(self) -> None:
        self.assertTrue(HEBREW_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(HEBREW_ADDITIONS <= patch_claudaco._planned_builders().keys())
        for codepoint in HEBREW_ADDITIONS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)
        for codepoint in (0x05DA, 0x05DF, 0x05E3, 0x05E5):
            glyph = self.build(codepoint)
            glyph.recalcBounds({})
            self.assertLess(glyph.yMin, 0)

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

    def test_greek_capital_sigma_has_four_strokes(self) -> None:
        self.assertIn(0x03A3, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x03A3).numberOfContours, 4)

    def test_geometric_greek_capitals_are_explicit_and_visible(self) -> None:
        self.assertTrue(GREEK_CAPITALS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(GREEK_CAPITALS <= patch_claudaco._planned_builders().keys())
        for codepoint in GEOMETRIC_GREEK_CAPITALS:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_geometric_greek_capital_winding_is_valid(self) -> None:
        for codepoint in GEOMETRIC_GREEK_CAPITALS:
            areas = self.contour_areas(codepoint)
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertTrue(areas)
                if codepoint == 0x0394:
                    self.assertLess(areas[0], 0)
                    self.assertGreater(areas[1], 0)
                else:
                    self.assertTrue(all(area < 0 for area in areas), areas)

    def test_greek_contours_use_consistent_winding(self) -> None:
        for codepoint in GREEK_ADDITIONS:
            areas = self.contour_areas(codepoint)
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
            source_ligatures = {
                codepoint: list(
                    source["glyf"][source.getBestCmap()[codepoint]].getCoordinates(
                        source["glyf"]
                    )[0]
                )
                for codepoint in (0xFB01, 0xFB02)
            }
            added, skipped, missing = patch_claudaco.patch_font(
                source_path,
                output_path,
                family="Claudaco 1.228",
                version="1.228",
                replace_existing=False,
            )
            self.assertEqual(added, 367)
            self.assertEqual(skipped, [0x03C0, 0xFB01, 0xFB02])
            self.assertEqual(missing, [])

            output = TTFont(output_path)
            cmap = output.getBestCmap()
            self.assertTrue(SMALL_CIRCLE_ADDITIONS <= cmap.keys())
            for codepoint in SMALL_CIRCLE_ADDITIONS:
                with self.subTest(codepoint=f"U+{codepoint:04X}"):
                    name = cmap[codepoint]
                    self.assertEqual(output["glyf"][name].numberOfContours, 2)
                    self.assertEqual(output["hmtx"].metrics[name][0], 1229)
            self.assertTrue(BENT_CORNER_HOOK_ARROWS <= cmap.keys())
            for codepoint in BENT_CORNER_HOOK_ARROWS:
                with self.subTest(codepoint=f"U+{codepoint:04X}"):
                    name = cmap[codepoint]
                    self.assertGreater(output["glyf"][name].numberOfContours, 0)
                    self.assertEqual(output["hmtx"].metrics[name][0], 1229)
            self.assertTrue((GREEK_CAPITALS | GREEK_ADDITIONS) <= cmap.keys())
            self.assertNotIn(0x03A2, cmap)
            self.assertEqual(
                {
                    output["hmtx"].metrics[cmap[codepoint]][0]
                    for codepoint in GREEK_CAPITALS | GREEK_ADDITIONS
                },
                {1229},
            )
            for codepoint in GREEK_CAPITALS:
                self.assertGreater(output["glyf"][cmap[codepoint]].numberOfContours, 0)
            self.assertGreater(output["glyf"][cmap[0x2139]].numberOfContours, 0)
            self.assertGreater(output["glyf"][cmap[0xFFFD]].numberOfContours, 0)
            self.assertTrue(LATIN_LIGATURES <= cmap.keys())
            self.assertEqual(
                {
                    output["hmtx"].metrics[cmap[codepoint]][0]
                    for codepoint in LATIN_LIGATURES
                },
                {1229},
            )
            for codepoint in LATIN_LIGATURES:
                self.assertGreater(output["glyf"][cmap[codepoint]].numberOfContours, 0)
            tz = output["glyf"][cmap[0xA728]]
            self.assertGreater(tz.xMax - tz.xMin, 1100)
            self.assertTrue(HEBREW_ADDITIONS <= cmap.keys())
            for codepoint in HEBREW_ADDITIONS:
                self.assertGreater(output["glyf"][cmap[codepoint]].numberOfContours, 0)
            self.assertTrue(SURVEYED_GEOMETRIC_SHAPES <= cmap.keys())
            for codepoint in SURVEYED_GEOMETRIC_SHAPES:
                self.assertGreater(output["glyf"][cmap[codepoint]].numberOfContours, 0)
            self.assertTrue(ADJACENT_SQUARE_FAMILY <= cmap.keys())
            for codepoint in ADJACENT_SQUARE_FAMILY:
                self.assertGreater(output["glyf"][cmap[codepoint]].numberOfContours, 0)
            for codepoint, coordinates in source_ligatures.items():
                self.assertEqual(
                    list(
                        output["glyf"][cmap[codepoint]].getCoordinates(output["glyf"])[0]
                    ),
                    coordinates,
                )
            source_cmap = source.getBestCmap()
            generated_sequences = {
                **{
                    codepoint: sequence
                    for codepoint, (sequence, _barred) in patch_claudaco.LATIN_EXTENDED_D_LIGATURES.items()
                },
                **patch_claudaco.PRESENTATION_LIGATURES,
            }
            for codepoint, sequence in generated_sequences.items():
                if codepoint in (0xFB01, 0xFB02, 0xFB05):
                    continue
                source_bounds = [
                    source["glyf"][source_cmap[ord(character)]] for character in sequence
                ]
                glyph = output["glyf"][cmap[codepoint]]
                self.assertEqual(glyph.yMin, min(item.yMin for item in source_bounds))
                self.assertEqual(glyph.yMax, max(item.yMax for item in source_bounds))
            self.assertEqual(patch_claudaco.PRESENTATION_LIGATURES[0xFB05], "ſt")
            self.assertNotEqual(
                list(output["glyf"][cmap[0xFB05]].getCoordinates(output["glyf"])[0]),
                list(output["glyf"][cmap[0xFB06]].getCoordinates(output["glyf"])[0]),
            )
            for codepoint, character in patch_claudaco.GREEK_CAPITAL_ASCII.items():
                self.assertEqual(
                    list(
                        output["glyf"][cmap[codepoint]].getCoordinates(output["glyf"])[0]
                    ),
                    list(
                        source["glyf"][source_cmap[ord(character)]].getCoordinates(
                            source["glyf"]
                        )[0]
                    ),
                )
            self.assertEqual(
                list(
                    output["glyf"][cmap[0x2011]].getCoordinates(output["glyf"])[0]
                ),
                list(
                    source["glyf"][source_cmap[ord("-")]].getCoordinates(
                        source["glyf"]
                    )[0]
                ),
            )
            self.assertEqual(output["name"].getDebugName(1), "Claudaco 1.228")
            self.assertEqual(
                list(output["glyf"]["pi"].getCoordinates(output["glyf"])[0]), source_pi
            )

            patch_claudaco.patch_font(
                source_path,
                replacement_path,
                family="Claudaco 1.228",
                version="1.228",
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
        for codepoint in (0x2003, 0x200A, 0x202F, 0x2800):
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertEqual(self.build(codepoint).numberOfContours, 0)

    def test_vertical_ellipsis_has_three_dots(self) -> None:
        self.assertIn(0x22EE, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x22EE).numberOfContours, 3)

    def test_private_use_bullet_is_visible(self) -> None:
        self.assertIn(0xF0B7, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0xF0B7).numberOfContours, 1)

    def test_small_circle_symbols_are_hollow_and_distinct(self) -> None:
        self.assertTrue(SMALL_CIRCLE_ADDITIONS <= patch_claudaco.EXPLICIT_CODEPOINTS)
        sizes = []
        for codepoint in (0x2218, 0x25E6, 0x26AC, 0x25CB):
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                glyph = self.build(codepoint)
                glyph.recalcBounds({})
                self.assertEqual(glyph.numberOfContours, 2)
                outer_area, inner_area = self.contour_areas(codepoint)
                self.assertLess(outer_area, 0)
                self.assertGreater(inner_area, 0)
                self.assertLess(inner_area, -outer_area)
                self.assertGreater(glyph.xMin, 0)
                self.assertLess(glyph.xMax, 1229)
                self.assertGreater(glyph.yMin, -512)
                self.assertLess(glyph.yMax, 2048)
                diameter = glyph.xMax - glyph.xMin
                self.assertAlmostEqual(diameter, glyph.yMax - glyph.yMin, delta=1)
                self.assertAlmostEqual((glyph.xMin + glyph.xMax) / 2, 1229 / 2, delta=1)
                reference = self.build(0xF0B7 if codepoint == 0x25E6 else 0x25CB)
                reference.recalcBounds({})
                self.assertAlmostEqual(
                    (glyph.yMin + glyph.yMax) / 2,
                    (reference.yMin + reference.yMax) / 2,
                    delta=1,
                )
                sizes.append(diameter)
        self.assertTrue(all(left < right for left, right in zip(sizes, sizes[1:])))

    def test_private_use_square_bullet_is_visible(self) -> None:
        self.assertIn(0xF0A7, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0xF0A7).numberOfContours, 1)

    def test_latest_symlink_is_relative_and_retargeted(self) -> None:
        with TemporaryDirectory() as directory:
            parent = Path(directory)
            first = parent / "Claudaco-1.215-Regular.ttf"
            second = parent / "Claudaco-1.216-Regular.ttf"
            first.touch()
            second.touch()
            latest = patch_claudaco._update_latest_symlink(first)
            self.assertTrue(latest.is_symlink())
            self.assertEqual(os.readlink(latest), first.name)
            self.assertEqual(latest.resolve(), first)
            patch_claudaco._update_latest_symlink(second)
            self.assertEqual(os.readlink(latest), second.name)
            self.assertEqual(latest.resolve(), second)

    def test_white_medium_square_is_outlined(self) -> None:
        self.assertIn(0x25FB, patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertEqual(self.build(0x25FB).numberOfContours, 2)

    def test_surveyed_geometric_shapes_are_explicit_and_visible(self) -> None:
        self.assertTrue(SURVEYED_GEOMETRIC_SHAPES <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(
            SURVEYED_GEOMETRIC_SHAPES <= patch_claudaco._planned_builders().keys()
        )
        for codepoint in SURVEYED_GEOMETRIC_SHAPES:
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertGreater(self.build(codepoint).numberOfContours, 0)

    def test_geometric_shape_contour_construction(self) -> None:
        for codepoint in range(0x25B2, 0x25C6):
            outlined = codepoint in {
                0x25B3,
                0x25B5,
                0x25B7,
                0x25B9,
                0x25BB,
                0x25BD,
                0x25BF,
                0x25C1,
                0x25C3,
                0x25C5,
            }
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertEqual(
                    self.build(codepoint).numberOfContours, 2 if outlined else 1
                )
        self.assertEqual(self.build(0x25C7).numberOfContours, 2)
        self.assertEqual(self.build(0x25CC).numberOfContours, 12)
        self.assertEqual(self.build(0x25CE).numberOfContours, 4)
        for codepoint in range(0x25E2, 0x25E6):
            self.assertEqual(self.build(codepoint).numberOfContours, 1)

    def test_adjacent_square_family_is_complete_and_visible(self) -> None:
        self.assertTrue(ADJACENT_SQUARE_FAMILY <= patch_claudaco.EXPLICIT_CODEPOINTS)
        self.assertTrue(
            ADJACENT_SQUARE_FAMILY <= patch_claudaco._planned_builders().keys()
        )
        expected_contours = {
            0x25A0: 1,
            0x25A1: 2,
            0x25A2: 2,
            0x25A3: 3,
            0x25A4: 5,
            0x25A5: 5,
            0x25A6: 8,
            0x25A7: 5,
            0x25A8: 5,
            0x25A9: 8,
            0x25AA: 1,
            0x25AB: 2,
            0x25AC: 1,
            0x25AD: 2,
            0x25AE: 1,
            0x25AF: 2,
        }
        for codepoint, contours in expected_contours.items():
            with self.subTest(codepoint=f"U+{codepoint:04X}"):
                self.assertEqual(self.build(codepoint).numberOfContours, contours)

    def test_double_horizontal_has_two_overdrawn_rules(self) -> None:
        glyph = self.build(0x2550)
        glyph.recalcBounds({})
        self.assertEqual(glyph.numberOfContours, 2)
        self.assertLess(glyph.xMin, 0)
        self.assertGreater(glyph.xMax, 1229)

    def test_double_vertical_has_two_overdrawn_rules(self) -> None:
        glyph = self.build(0x2551)
        glyph.recalcBounds({})
        self.assertEqual(glyph.numberOfContours, 2)
        self.assertLess(glyph.yMin, -512)
        self.assertGreater(glyph.yMax, 2048)

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
            patch_claudaco._resolve_build_identity("1.228", None, None),
            ("Claudaco 1.228", Path("Claudaco-1.228-Regular.ttf")),
        )

    def test_build_identity_allows_explicit_overrides(self) -> None:
        self.assertEqual(
            patch_claudaco._resolve_build_identity(
                "1.228", "Claudaco Custom", Path("custom.ttf")
            ),
            ("Claudaco Custom", Path("custom.ttf")),
        )


if __name__ == "__main__":
    unittest.main()
