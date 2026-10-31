# Dawn State Brand Kit

## Warm Precision · profile 1.0

Dawn State expresses **Warm Precision**: make the important obvious, the complex understandable, and the next step clear. Favor warm editorial minimalism, high contrast, precise hierarchy, and evidence-led language across graphics, diagrams, charts, figures, memos, presentations, and interfaces.

The personal philosophy lives in [design-system/PHILOSOPHY.md](design-system/PHILOSOPHY.md). Exact profile values live in [tokens.json](design-system/profiles/dawn-state/tokens.json); medium-specific application lives in [adapters/](design-system/adapters/). The marked reference below is generated from those tokens. Rebuild it with `python3 design-system/scripts/build.py --embed-fonts --write-brand`.

## 1. Palette and typography

<!-- dawn-state-tokens:start -->
| Color | Exact value | Role |
| --- | --- | --- |
| Ivory | `#FFFFF0` | Canvas and open space |
| Onyx | `#0F0F0F` | Primary text |
| Blue Slate | `#2C3E50` | Structure, links, essential marks |
| Golden Orange | `#F39C12` | Scarce editorial emphasis |
| Sage Green | `#87A96B` | Positive or secondary cue |
| Slate Deep | `#1E3447` | Secondary text, darker structure |
| Copper Deep | `#96590A` | Kickers and small accent text |
| Sage Deep | `#5F7F4A` | Text-safe positive cue |
| Parchment | `#F5EEDC` | Detail wells, never a second canvas |

| Typography | Family | Weight |
| --- | --- | --- |
| Display | Newsreader | 500 |
| Body | Inter | 400 |
| Heading | Inter | 600 |
| Kicker | ui-monospace | 500 |
| Code | ui-monospace | 400 |

| Medium | Body / primary labels | Supporting text |
| --- | --- | --- |
| Web | 18 px | 14 px |
| Document | 11 pt | 9 pt |
| Slide | 32 px | 24 px |
| Diagram | 16 px | 14 px |
| Chart | 16 px | 14 px |

Digital container radii: 8–12 px. Digital structural/emphasis strokes: 2/3 px. Decorative rules: 1 px at 30% Blue Slate.
<!-- dawn-state-tokens:end -->

### Color roles and emphasis

Ivory is the warm canvas; Onyx is primary text; Blue Slate provides structure, supporting text, links, primary data, and focus. Golden Orange isolates editorial emphasis. Sage Green supports positive outcomes or a secondary data series.

Use the 60–30–10 rule as a compositional guide: a predominantly open canvas, a clear dark information hierarchy, and no more than 10% combined accent area. It is not a pixel-count quota, and dense operational interfaces need appropriate information density. Use spacing, scale, and weight before adding color.

Keep the nine exact palette values. Slate Deep carries secondary text; Copper Deep carries kickers and small accent text (both clear 4.5:1 on Ivory, unlike Golden Orange and Sage, which stay fill-only). Parchment is a detail well, never a second canvas. Do not introduce gradients or decorative tints. A publishing/accessibility requirement may justify a scoped extension; record its purpose and destination rather than silently changing the identity.

### Background-aware contrast

Measure every role against its actual background. Normal text needs at least 4.5:1; large text and essential non-text marks need at least 3:1. Onyx and Blue Slate both clear normal-text requirements on Ivory. Ivory clears them on Blue Slate.

Golden Orange and Sage Green do **not** clear 3:1 on Ivory. Use them as highlights with Onyx labels, or provide a dark essential outline, symbol, or line pattern. Do not use either as body text or the sole essential chart/connector/control mark on Ivory. A legend cannot repair an invisible mark.

Never place Onyx text on Blue Slate or Blue Slate text on Onyx. Translucent Blue Slate borders are decorative separation only; full-strength structural strokes carry essential boundaries and relationships.

## 2. Type hierarchy

Newsreader 500 (optical) belongs to top-level display moments. Inter 600 handles headings; Inter 400 handles prose. Platform monospace handles kickers, data labels, and actual code — uppercase with wide tracking for kickers, tabular numerals for data. Do not apply monospace to prose as a technical costume.

Use a small, repeatable scale with a real middle: kicker, lede, section heading, page heading, display — each with a fixed ratio to body, not a shout-or-mumble jump. Keep titles concise, line lengths controlled, and hierarchy clear through weight and spacing. Uppercase is reserved for meaningful short labels: kickers, table headers, and qualifications. Balance long headings only on display surfaces.

The former universal 14 pt floor becomes destination-specific type ramps. Web reading, printed memos, diagrams, and projected slides have different viewing conditions. Use the generated medium defaults and verify at the final size; simplify content before making it unreadable. Preserve semantic headings and selectable text.

## 3. Layout and form

Maintain generous boundary whitespace and a consistent underlying grid. A roughly 10% editorial margin is a useful starting point for standalone assets; web gutters, print margins, and slide safe areas use their adapters. Necessary density in tables and tools is appropriate.

Prefer one clear argument or task per frame. Split overloaded compositions into overview and detail. Use proximity before containers; boxes should group meaningful content. Prominent containers have restrained rounded corners. Avoid heavy pills except compact badges, decorative textures, ornamental frames, and complex shadows.

Use separate stroke roles: quiet decorative rules, dark essential structure, and selective emphasis. The former universal 2–3 px rule applies to structural digital strokes, not every print rule or subtle divider. Use medium-appropriate units.

## 4. Diagrams and data

Choose the visual by meaning. Quantities belong in charts; relationships belong in diagrams; attributes often belong in a table. Use flat or monoline icons with consistent stroke weights and a coherent icon vocabulary.

Default diagram routes and primary chart marks are Blue Slate. Reserve accents for one or two focal elements, with sufficient contrast and redundant labels or shape cues. Direct-label data when practical. Avoid gradients, 3D effects, decorative chart furniture, and heavy legends.

State estimands, units, denominators, sample sizes, confidence levels, exclusions, and relevant limitations. Preserve counterexamples and uncertainty. Do not manufacture a causal account to fill a diagram. When simplifying a source, report meaningful content merged, omitted, or moved to detail.

## 5. Editorial voice

- Precise, evidence-led, and direct.
- Scientifically credible without unnecessary jargon.
- Confident without hype or unsupported superlatives.
- Warm, useful, and concise.

For explanatory work, lead with the claim or outcome, then mechanism (when known), evidence, and implication. Prefer concrete nouns, active verbs, and measurable statements. Keep one primary message per section or slide.

Public work may be curious and personal; scientific work remains neutral and precise. Both share the same facts. Separate registered findings, descriptive summaries, exploratory accounts, hypotheses, and illustrations. Avoid inflated claims, walls of copy, vague categories, decorative punctuation, and competing CTAs.

An action-oriented artifact ends with a clear next step. Research may end with an implication or next question; it need not have a marketing CTA.

## 6. Production review

- Purpose and primary takeaway/task are immediately clear.
- Profile values come from the normative token source.
- Accent use is scarce and its meaning is consistent.
- Actual text, control, and data-mark pairings clear the relevant contrast threshold.
- Final-size typography, spacing, and media units are appropriate.
- Essential relationships and uncertainty survive simplification.
- Charts and figures trace to source files; meaningful exclusions are visible.
- Interfaces have relevant states, keyboard support, visible focus, and useful labels.
- Exported content is readable, correctly sized, and unclipped; fonts and fallbacks are verified.

Use [REVIEW_RECEIPT.md](design-system/templates/REVIEW_RECEIPT.md) for consequential outputs. Inspect the rendered artifact; passing a mechanical check is not a substitute for editorial judgment.
