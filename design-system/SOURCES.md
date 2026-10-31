# Influences and adaptation decisions

Reviewed 23 October 2026. These are influences, not runtime dependencies. Repository defaults may change; record an installed version when integrating a vendor tool.

## Dawn State

Source: `BRAND_KIT.md` and its evidence-led editorial voice. The current profile uses Newsreader for display and Inter for headings and prose, with flat surfaces, scarce accents and a warm canvas. Mirror uses Plus Jakarta Sans for its working-persona display.

Version 1 of Warm Precision makes distribution and margins compositional defaults, makes typography/strokes destination-specific, and adds background-aware contrast rules. It separates personal doctrine from brand profile and project context. The original brand kit is refined in place; this package records the adaptation rationale.

## Impeccable

- https://github.com/pbakaus/impeccable
- https://github.com/pbakaus/impeccable/blob/main/skill/SKILL.src.md
- https://github.com/pbakaus/impeccable/blob/main/skill/reference/init.md
- https://github.com/pbakaus/impeccable/blob/main/skill/reference/document.md
- https://github.com/pbakaus/impeccable/blob/main/skill/reference/operate.md
- https://github.com/pbakaus/impeccable/blob/main/skill/reference/critique.md

Adopt durable product context separate from visual direction, surface-specific modes, pinned-brief precedence, appropriate familiarity in tools, and rendered review. Use critique/audit/distill/adapt/polish as a reusable working vocabulary. Warm Precision adds Explain for analytical artifacts; this is a local extension, not an Impeccable command or mode claim.

## Diagram Design

- https://github.com/cathrynlavery/diagram-design
- https://github.com/cathrynlavery/diagram-design/blob/main/skills/diagram-design/SKILL.md
- https://github.com/cathrynlavery/diagram-design/blob/main/skills/diagram-design/references/style-guide.md
- https://github.com/cathrynlavery/diagram-design/blob/main/skills/diagram-design/references/profiles.md

Adopt semantic selection, deliberate subtraction, constrained focal emphasis, structural grid discipline, portable profile selection, accessible SVG, and fidelity ledgers. Adapt serif typography, small label defaults, hairline geometry, and tinted fills to Dawn State and each destination. Split accent fill/text/stroke roles because raw Dawn State orange does not meet the vendor's all-role contrast requirement on Ivory.

## Contrast and accessibility

- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html

Measure WCAG 2.x relative luminance against the actual background; composite translucent colors first. Normal text needs at least 4.5:1, large text 3:1, and essential marks 3:1. Supporting labels/shape cues also preserve meaning without color. Automated results do not certify the whole artifact's accessibility.

## Fonts

Fonts are distributed under the SIL Open Font License:

- [Inter license](https://github.com/rsms/inter/blob/master/LICENSE.txt)
- [Newsreader license](https://github.com/google/fonts/blob/main/ofl/newsreader/OFL.txt)
- [Plus Jakarta Sans license](https://github.com/tokotype/PlusJakartaSans/blob/master/OFL.txt)
