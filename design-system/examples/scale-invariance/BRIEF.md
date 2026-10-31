# Calibration brief: the same bargain at a millionfold scale

## Purpose

Help a scientifically curious reader understand that the closing split's response to scale is model-dependent in the Study 2 setup, so they avoid generalising one model's behavior to all negotiating agents.

- Profile: Dawn State 1.0.0; philosophy: Warm Precision.
- Memo: Read; one-page A4 explanation with evidence and implication.
- Deck: Explain; five 16:9 frames (question, design, result, qualification, implication).
- Web section: Read/Explain; readable desktop and phone with optional evidence detail.
- Figure: Explain; interval plot with accessible text and a companion data table.

## Evidence

The selected calibration slice is **Study 2's two completed open-weight models**, not a summary of all later studies. Sources are the two `primary.json` files, `derived/cross_model/summary.json`, the original and Study 2 registrations, fixture configuration, and the corresponding `STORY.md` §8 claims.

The generator captures exact values and source SHA-256 digests in `evidence.json`. A portable build uses that snapshot. Refresh is explicit and reads the original analyses without rerunning them.

- Primary estimand: fixture mean of seller-share change, $100M minus $100, averaged over opening orders with defined agreement pairs. Seller share is `(P − F)/(C − F)`.
- Gemma 4 31B: approximately −25.6 percentage points, 30 analysed fixtures, 180 scored games; 29 of 30 fixture changes negative.
- Qwen3.8 27B FP8: approximately +0.9 percentage points, 29 analysed fixtures from 30, 180 scored games.
- Both 90% and 95% bootstrap intervals are preserved. Registered equivalence uses 90% interval containment within ±10 percentage points.
- Qwen's upper 90% bound is approximately +9.90 pp, barely inside the margin. Its 95% interval extends beyond it.
- Agreement at $100/$100M: Gemma 60/60 and 60/60; Qwen 59/60 and 55/60. Seller share conditions on agreement. F20 is excluded from Qwen's primary paired contrast; some other fixtures use one opener only.
- Cross-model differences are descriptive: model families, precisions, and sampling settings differ. The comparison does not establish a cause or a population rate of failure.

## Composition and fidelity

One primary takeaway: **the closing response depends on the model in this setup**. Gemma is the editorial focal row, but both rows have equally readable intervals and labels. Orange is an optional nonessential dot cue on a dark outline, never the only carrier of the finding.

The five-slide deck preserves the qualifications as a separate visible slide, not hidden notes. The web uses an evidence disclosure and a readable local-scrolling chart. The memo includes the agreement caveat. Every numeric expression comes from the snapshot.

The overview omits Study 1, later API experiments, Study 3, and mechanistic work by explicit scope; it makes no claim about them. The $100K arm is disclosed in the design but not plotted because the selected primary contrast is $100M − $100. No component, relationship, or cause is invented to fill a layout.
