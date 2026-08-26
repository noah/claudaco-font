# Susan Kare and the origins of Monaco

[![Norman Seeff portrait of Susan Kare at Apple beside Kare's Happy Macintosh print](https://www.typeroom.eu/assets/original/2022/06/06/susan%20kare%20icons%20exhibition%20lyon%200.png)](https://www.typeroom.eu/icons-by-susan-kare-iconography-exhibition-france)

*Norman Seeff, **Portrait of Susan Kare at her office at Apple** (1983), shown alongside Susan Kare, **Happy Macintosh on Orange Gradient** (2019). Image and caption via [Typeroom](https://www.typeroom.eu/icons-by-susan-kare-iconography-exhibition-france).*

Susan Kare created the original Macintosh icons and bitmap typefaces, including Monaco. The English booklet for the Lyon Museum of Printing and Graphic Communication's 2022 exhibition, [*icônes / icons by Susan Kare*](https://www.imprimerie.lyon.fr/sites/micg/files/2022-05/livret_anglais_print.pdf), recounts how the fonts received their city names:

> “Steve Jobs however found these names too ‘American’ and suggested instead using names of international capitals, hence Monaco, Geneva, San Francisco, Toronto, London, New York and Chicago.”

The booklet explains that Kare had initially proposed names from the Philadelphia suburbs she knew as a child. [Typeroom's exhibition article](https://www.typeroom.eu/icons-by-susan-kare-iconography-exhibition-france) provides additional context on Kare's work for the Macintosh and her influence on digital iconography and type design.

## Kare's breakthrough at Apple

[![Susan Kare at Apple in 1983](https://images.nymag.com/news/features/beginnings/11-beginnings-susan-kare-560.jpg)](https://nymag.com/news/features/beginnings/susan-kare/index.html)

*Susan Kare at Apple, 1983. Photograph by Norman Seeff; image via [New York Magazine](https://nymag.com/news/features/beginnings/susan-kare/index.html).*

In New York Magazine's 2016 [“Susan Kare, Designer”](https://nymag.com/news/features/beginnings/susan-kare/index.html), Kare recalls arriving at Apple in 1982 from a fine-arts background, designing the bold system font that became Chicago on a seven-by-nine grid, and discovering an affinity for the constraints of pixel-based work. She describes how the team's Philadelphia commuter-stop font names gave way to international cities:

> “If they’re going to be cities, they need to be world-class cities.”
>
> — Susan Kare, recalling Steve Jobs, [New York Magazine, January 12, 2016](https://nymag.com/news/features/beginnings/susan-kare/index.html)

> **Full article text — editorial placeholder**
>
> _Paste the reviewed New York Magazine article text here._

---

# Claudaco

**Claudaco** is a Monaco-derived monospaced terminal font patched with the Unicode and Powerline-style symbols used by Claude Code and other terminal user interfaces.

This repository distributes the patcher, not a font binary. You must supply your own copy of [`Monaco for Powerline.ttf`](https://gist.github.com/lujiacn/32b598b1a6a43c996cbd93d42d466466/5be6ef0e44a3427fdb8343b4dacc29716449c59e#file-monaco-for-powerline-ttf) and build Claudaco locally.

Claudaco exists for a specific reason: Monaco has a compact, highly readable programming face, but the available `Monaco for Powerline` TTF lacks many of the symbols emitted by modern command-line applications. On Windows, those missing characters appear as empty squares, and terminal font fallback is not always reliable—especially for Powerline characters in Unicode’s Private Use Area. Claudaco places the needed glyphs directly into the same fixed-width font.

```text
╭─────────────────────────────────────────────────────────────────────╮
│  ⓘ Claude Code · ⏸  ▾  ❯  ⏵⏵  ↳  ⎿  ⧉  ⬝⬝⬝⬝                    │
╰─────────────────────────────────────────────────────────────────────╯
╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
▐▛███▜▌  ▝▜█████▛▘  ▘▘  ▝▝   ◐  ▣     
```

## What Claudaco is

Claudaco 1.226 is built from a user-supplied copy of **Monaco for Powerline 2.0**. The patch adds 357 glyphs while preserving Monaco’s original character metrics and the Powerline separators already present in the source font.

The added symbols are not copied from a second donor font. `patch_claudaco.py` constructs them from geometric TrueType outlines. Circled letters and digits reuse the source font’s own alphanumeric forms inside newly drawn circles. This keeps the additions visually related to the underlying Monaco face and avoids mixing unrelated font designs.

Every glyph has the same 1,229-unit advance width. The resulting font is therefore strictly monospaced and suitable for terminals, editors, source code, tables, and text-based interfaces.

## What Claudaco is not

Claudaco is **not** the historical bitmap-strike version of Monaco. The supplied `Monaco for Powerline.ttf` contains no embedded `EBDT/EBLC`, `CBDT/CBLC`, or `sbix` bitmap tables, so Claudaco is an outline-only TrueType font. It may look crisp under DirectWrite at suitable sizes, but it does not recreate the hand-tuned pixel glyphs from older Mac systems.

Claudaco is also not a complete Nerd Font. It deliberately adds a focused terminal repertoire instead of thousands of unrelated icons. It is an unofficial personal patch, not a release by Anthropic, Apple, the Powerline project, or any other font vendor.

## Included glyph coverage

### Claude Code and terminal symbols

```text
U+2139  ℹ  INFORMATION SOURCE
U+2190–U+2199  ← ↑ → ↓ ↔ ↕ ↖ ↗ ↘ ↙  BASIC ARROWS
U+219C U+219D U+21AD U+21AF  ↜ ↝ ↭ ↯  WAVE AND ZIGZAG ARROWS
U+21B3  ↳  DOWNWARDS ARROW WITH TIP RIGHTWARDS
U+21BB  ↻  CLOCKWISE OPEN CIRCLE ARROW
U+21C6  ⇆  LEFTWARDS ARROW OVER RIGHTWARDS ARROW
U+21E7  ⇧  UPWARDS WHITE ARROW
U+2299  ⊙  CIRCLED DOT OPERATOR
U+22EE  ⋮  VERTICAL ELLIPSIS
U+22EF  ⋯  MIDLINE HORIZONTAL ELLIPSIS
U+2315  ⌕  TELEPHONE RECORDER
U+23BF  ⎿  DENTISTRY SYMBOL LIGHT VERTICAL AND BOTTOM RIGHT
U+23F5  ⏵  BLACK MEDIUM RIGHT-POINTING TRIANGLE
U+23F8  ⏸  DOUBLE VERTICAL BAR
U+25A0–U+25AF  ■ □ ▢ ▣ ▤ ▥ ▦ ▧ ▨ ▩ ▪ ▫ ▬ ▭ ▮ ▯  SQUARE AND RECTANGLE FAMILY
U+25B0  ▰  BLACK PARALLELOGRAM
U+25B1  ▱  WHITE PARALLELOGRAM
U+25B2–U+25C5  ▲ △ ▴ ▵ ▶ ▷ ▸ ▹ ► ▻ ▼ ▽ ▾ ▿ ◀ ◁ ◂ ◃ ◄ ◅  DIRECTIONAL TRIANGLES AND POINTERS
U+25C6  ◆  BLACK DIAMOND
U+25C7  ◇  WHITE DIAMOND
U+25C8  ◈  WHITE DIAMOND CONTAINING BLACK SMALL DIAMOND
U+25C9  ◉  FISHEYE
U+25CB  ○  WHITE CIRCLE
U+25CC  ◌  DOTTED CIRCLE
U+25CD  ◍  CIRCLE WITH VERTICAL FILL
U+25CE  ◎  BULLSEYE
U+25CF  ●  BLACK CIRCLE
U+25D0  ◐  CIRCLE WITH LEFT HALF BLACK
U+25D4  ◔  CIRCLE WITH UPPER RIGHT QUADRANT BLACK
U+25E2–U+25E5  ◢ ◣ ◤ ◥  CORNER TRIANGLES
U+25FB  ◻  WHITE MEDIUM SQUARE
U+2699  ⚙  GEAR
U+26A0  ⚠  WARNING SIGN
U+2731  ✱  HEAVY ASTERISK
U+276C–U+2771  ❬ ❭ ❮ ❯ ❰ ❱  ANGLE BRACKET ORNAMENTS
U+27E8–U+27E9  ⟨ ⟩  MATHEMATICAL ANGLE BRACKETS
U+27F3  ⟳  CLOCKWISE GAPPED CIRCLE ARROW
U+29C9  ⧉  TWO JOINED SQUARES
U+2B16  ⬖  DIAMOND WITH LEFT HALF BLACK
U+2B1D  ⬝  BLACK VERY SMALL SQUARE
U+2B25  ⬥  BLACK MEDIUM DIAMOND
U+2B29  ⬩  BLACK SMALL DIAMOND
U+2B2A  ⬪  BLACK SMALL LOZENGE
U+F0A7    PRIVATE-USE SQUARE BULLET
U+F0B7    PRIVATE-USE BULLET
U+FFFD  �  REPLACEMENT CHARACTER
```

`U+23BF` has an unusual formal Unicode name, but Claude Code uses it visually as an indented branch or continuation marker.

`U+F0A7` and `U+F0B7` are common private-use mappings for square and round bullets. Claudaco renders the round bullet with the same proportions as Monaco's `U+2022 BULLET`.

`U+FFFD` uses the conventional outlined-diamond form with Monaco's own question mark fitted inside.

### Latin ligatures

Claudaco includes paired-letter forms from Latin Extended-D and the common typographic presentation ligatures. They preserve Monaco's native cap height, x-height, ascenders, descenders, and baseline while fitting broader, modestly overlapping letterforms into one fixed-width cell:

```text
U+A728–U+A729  Ꜩ ꜩ  TZ
U+A732–U+A73D  Ꜳ ꜳ Ꜵ ꜵ Ꜷ ꜷ Ꜹ ꜹ Ꜻ ꜻ Ꜽ ꜽ  AA AO AU AV barred-AV AY
U+A74E–U+A74F  Ꝏ ꝏ  OO
U+A760–U+A761  Ꝡ ꝡ  VY
U+FB00–U+FB06  ﬀ ﬁ ﬂ ﬃ ﬄ ﬅ ﬆ
```

Monaco already supplies `U+FB01` and `U+FB02`; Claudaco preserves those source glyphs and constructs the other 23 mappings.

### Hebrew

Claudaco includes the 27 unpointed Hebrew letters, including the five final forms, plus common modern punctuation, two biblical separators, and the new sheqel sign. Bidirectional ordering is handled by the terminal or application.

```text
U+05D0–U+05EA  א ב ג ד ה ו ז ח ט י ך כ ל ם מ ן נ ס ע ף פ ץ צ ק ר ש ת
U+05BE  ־  HEBREW PUNCTUATION MAQAF
U+05C0  ׀  HEBREW PUNCTUATION PASEQ
U+05C3  ׃  HEBREW PUNCTUATION SOF PASUQ
U+05F3  ׳  HEBREW PUNCTUATION GERESH
U+05F4  ״  HEBREW PUNCTUATION GERSHAYIM
U+20AA  ₪  NEW SHEQEL SIGN
```

### Greek letters

```text
U+0391–U+03A1,
U+03A3–U+03A9  Α Β Γ Δ Ε Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π Ρ Σ Τ Υ Φ Χ Ψ Ω
U+03B1–U+03C9  α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ ς σ τ υ φ χ ψ ω
```

This covers the complete modern Greek uppercase and lowercase alphabets, including `U+03C2 GREEK SMALL LETTER FINAL SIGMA`. `U+03A2` is unassigned by Unicode. Capitals shared with Latin reuse Monaco's own outlines, Monaco's existing `π` mapping is preserved, and the distinct Greek forms use Claudaco's geometric outlines.

### Set theory

Claudaco includes the basic membership, union, intersection, subset, and superset operators, including negated forms and the subset-or-equal and superset-or-equal variants:

```text
U+2205  ∅  EMPTY SET
U+2208  ∈  ELEMENT OF
U+2209  ∉  NOT AN ELEMENT OF
U+220B  ∋  CONTAINS AS MEMBER
U+220C  ∌  DOES NOT CONTAIN AS MEMBER
U+2229  ∩  INTERSECTION
U+222A  ∪  UNION
U+2282  ⊂  SUBSET OF
U+2283  ⊃  SUPERSET OF
U+2284  ⊄  NOT A SUBSET OF
U+2285  ⊅  NOT A SUPERSET OF
U+2286  ⊆  SUBSET OF OR EQUAL TO
U+2287  ⊇  SUPERSET OF OR EQUAL TO
```

### Whitespace

`U+2003 EM SPACE`, `U+200A HAIR SPACE`, and `U+202F NARROW NO-BREAK SPACE` are included as outline-free glyphs with the font's standard fixed-cell advance width.

`U+2011 NON-BREAKING HYPHEN` uses Monaco's existing hyphen outline while retaining its non-breaking Unicode semantics.

### Circled alphanumerics

Claudaco adds:

- Circled digits `0–9`
- Circled uppercase letters `A–Z`
- Circled lowercase letters `a–z`

This includes the symbols first observed in Claude Code output:

```text
ⓘ  ⓛ  ⓦ
```

### Box drawing

Claudaco includes the light rules and junctions used by OpenCode tables and trees, dashed and double horizontal/vertical rules, rounded corners, and the light/heavy half-line set used by terminal layouts:

```text
─  │  ┃  ┌  ┐  └  ┘  ├  ┤  ┬  ┴  ╌  ═  ║  ╭  ╮  ╯  ╰  ╹
```

Specifically, the patch provides:

```text
U+2500
U+2502
U+2503
U+250C, U+2510, U+2514, U+2518
U+251C, U+2524, U+252C, U+2534
U+254C
U+2550–U+2551
U+256D–U+2570
U+2574–U+257F
```

### Braille spinner cells

The blank Braille cell and every frame in OpenCode's classic spinner are included:

```text
⠀  ⠋  ⠙  ⠹  ⠸  ⠼  ⠴  ⠦  ⠧  ⠇  ⠏
```

### Block elements

The complete Unicode **Block Elements** range is included:

```text
U+2580–U+259F
```

That range covers full, half, fractional, shaded, and quadrant blocks, including:

```text
▀  ▄  █  ▌  ▐  ▘  ▛  ▜  ▝
```

The block outlines slightly overdraw cell boundaries and overlap adjoining regions. This is intentional: it reduces one-pixel seams that some DirectWrite and FreeType rasterization paths otherwise expose between neighboring block glyphs.

### Existing source-font characters preserved

The source font already supplied the middle dot and basic Powerline hard dividers, which remain unchanged:

```text
U+00B7  ·
U+E0B0  
U+E0B2  
```

The `E0xx` assignments are Private Use Area conventions rather than standardized Unicode characters, which is one reason ordinary fallback fonts may not render them correctly.

## Font metadata

```text
Family name:       Claudaco 1.226
Style:             Regular
Full name:         Claudaco 1.226 Regular
PostScript name:   Claudaco1226-Regular
Version:           1.226
Format:            TrueType outlines
Glyph count:       750
Unicode mappings:  737
Advance width:     1229 units for every glyph
Embedded bitmaps:  None
```

## Build

Requirements:

- Python 3.10 or later
- [`fonttools`](https://github.com/fonttools/fonttools)

Clone the repository, put your `Monaco for Powerline.ttf` beside the patcher, and run:

```shell
python -m pip install -r requirements.txt
python patch_claudaco.py "Monaco for Powerline.ttf"
```

The generated `Claudaco-1.226-Regular.ttf` remains on your machine and is ignored by Git. Both its filename and installed family include the version so Windows treats future releases as separate fonts instead of reusing a cached family. After each successful default CLI build, `Claudaco-Regular.ttf` is atomically updated as a relative symlink to the generated versioned file; an explicit `--output` leaves that pointer unchanged.

### Audit OpenCode coverage

After building the font, compare it with any OpenCode checkout:

```shell
python audit_opencode_glyphs.py /path/to/opencode Claudaco-1.226-Regular.ttf
```

The audit conservatively scans every non-ASCII code point in OpenCode's terminal-owned UI and CLI source directories, reports uncovered mappings or empty visible outlines with source locations, and exits unsuccessfully on a gap. The intentional CJK text in OpenCode's terminal demo is excluded only while it remains confined to that demo because it should use normal font fallback.

On Windows, `py` can be used instead of `python`:

```powershell
py -m pip install -r requirements.txt
py .\patch_claudaco.py ".\Monaco for Powerline.ttf"
```

## Install on Windows

1. Right-click `Claudaco-1.226-Regular.ttf` and select **Install for all users**.
2. Select **Claudaco 1.226** as the font face in the terminal or editor.
3. Fully close and reopen the application so Windows loads the new font family.

If an application still shows squares, verify that it is actually using Claudaco rather than a similarly named Monaco font. Some applications also keep their own font caches until every window and background process has exited.

### Versioned families avoid stale installations

Claudaco defaults to a unique family for every release. The standard build command for version 1.226 is equivalent to:

```powershell
py .\patch_claudaco.py ".\Monaco for Powerline.ttf" `
  -o ".\Claudaco-1.226-Regular.ttf" `
  --family "Claudaco 1.226" `
  --version "1.226"
```

This creates a separate family with these identifiers:

```text
Family name:      Claudaco 1.226
Full name:        Claudaco 1.226 Regular
PostScript name:  Claudaco1226-Regular
```

For Windows Terminal, the corresponding profile setting is:

```json
"font": {
  "face": "Claudaco 1.226"
}
```

An older **Claudaco** entry can remain installed or hidden; it does not conflict with **Claudaco 1.226**. A **Hide**-only entry is commonly a system-wide installation that the current user cannot remove through Settings. If removal is still desirable, close every application using the font and open the legacy Fonts control panel with `shell:fonts`; an administrator may be able to delete it there. Per-user fonts live under `%LOCALAPPDATA%\Microsoft\Windows\Fonts`, while all-user fonts live under `C:\Windows\Fonts`. Leaving the old family alone is safer than manually deleting font files or registry entries.

## Patcher options

Run `python patch_claudaco.py --help` for the complete command reference. The main options are:

```text
--family NAME          Override the default "Claudaco VERSION" family
--version VERSION      Set the font version and default family/filename
--replace-existing     Replace mappings already present in the source font
```

By default, the patcher preserves any source-font mapping that already exists. It also:

- verifies that the input uses TrueType `glyf` outlines;
- refuses a source font that is not strictly monospaced;
- generates the terminal symbols and Unicode ranges described above;
- gives every added glyph the source font’s normal advance width;
- renames the output family and PostScript records;
- marks the result as fixed-pitch;
- recalculates relevant Unicode and metric metadata; and
- reopens the saved font to confirm that all explicitly required characters survived serialization.

The patcher does not contain or download Monaco. It expects the user to provide the base TTF.

## Adding more glyphs

New symbols can be added in three steps:

1. Add the Unicode code point to `EXPLICIT_CODEPOINTS` when it is a required test character.
2. Add a geometric builder for the glyph, or map it to an existing reusable builder.
3. Register the code point in `_planned_builders()` and rebuild the font.

Keeping the additions geometric is useful for block elements, separators, progress indicators, and interface icons because their cell alignment matters more than typographic detail. More complex symbols may be better imported from an appropriately licensed monospaced donor font, with their scale, baseline, side bearings, and advance width normalized to Claudaco.

## Known limitations

- Claudaco currently has only a Regular face. Applications may synthesize bold or italic styles.
- It does not contain the complete Box Drawing, Dingbats, Geometric Shapes, Nerd Fonts, or icon-font repertoires.
- It has no embedded bitmap strikes or handcrafted small-size hinting for the added glyphs.
- Rendering can vary among DirectWrite, FreeType, CoreText, browser canvases, and GPU terminal renderers.
- Very aggressive clipping by a renderer can defeat the deliberate overdraw used to hide seams between block cells.
- Private Use Area characters depend on convention; another application could assign a different meaning to the same code point.

## Provenance and redistribution

The source font's internal metadata identifies the underlying Monaco outlines as:

```text
© 1990–97 Apple Computer Inc.
© 1990–97 Type Solutions Inc.
© 1990–97 The Font Bureau Inc.
```

Claudaco is a derivative generated from a user-supplied font. The MIT license in this repository applies only to the original patcher and documentation. It does not grant any rights to Monaco, `Monaco for Powerline.ttf`, or a generated Claudaco font.

Do not commit or redistribute input or generated font binaries unless you have separately confirmed that the applicable font licenses permit it. This repository intentionally ignores all `.ttf` files.

The Claudaco name and patch are unofficial and are not endorsed by or affiliated with Anthropic or Apple.

## Package contents

```text
patch_claudaco.py      Reproducible TrueType patcher
audit_opencode_glyphs.py  OpenCode source-to-cmap coverage audit
test_claudaco.py        Source-font-independent builder regression tests
requirements.txt       Python dependency
README.md              Documentation and glyph reference
LICENSE                MIT license for the patcher and documentation
.gitignore             Excludes local input and generated fonts
.github/workflows/     GitHub Actions checks
```

## License

The original patcher and documentation are available under the [MIT License](LICENSE). This license does not cover Monaco, the source font, or generated font binaries. See [Provenance and redistribution](#provenance-and-redistribution).
