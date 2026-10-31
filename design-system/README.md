# Warm Precision

**Make the important obvious, the complex understandable, and the next step clear.**

A portable personal design system for research, documents, diagrams, presentations, and software. Dawn State is its default visual profile. Version 1.0, established 23 October 2026.

## Start here

1. Read `PHILOSOPHY.md` for the six principles.
2. Select the brand in `profiles/` and the relevant medium in `adapters/`.
3. Fill in `templates/ARTIFACT_BRIEF.md` using real project evidence.
4. Compose, distill, inspect at the final size, and record any meaningful exception.

For this checkout, build the browsable handbook and calibration examples:

```sh
python3 design-system/scripts/build.py --embed-fonts
python3 -m http.server 8080 --bind 127.0.0.1 --directory handbook
```

Open **http://127.0.0.1:8080/** or `handbook/index.html`. The handbook, memo, deck, web example, and figure also open directly as files. With `--embed-fonts`, the output carries the actual brand fonts and works offline; without it, HTML requests Google Fonts and discloses system fallbacks. Browser print produces a one-page memo and five landscape slides.

Informational Markdown documents at the project root are also registered in the handbook with Markdown downloads. Compose their web editions as distilled explanations, using a visual overview and linked detail where appropriate. The builder excludes root `README.md` and `AGENTS.md`, and handles `BRAND_KIT.md` separately. Use `--public` to build only the reusable handbook and Mirror guide. Source documents and visual compositions travel with the downloadable kit.

## Authority and ownership

- `PHILOSOPHY.md` owns cross-project principles.
- `profiles/dawn-state/tokens.json` owns exact colors, type families, scales, and semantic bindings. Its `contract` owns minimum contrast and accent limits.
- `../BRAND_KIT.md` explains the Dawn State identity. Its marked tables are generated from the profile.
- `adapters/` own medium-specific expression; templates and examples demonstrate it.
- Project context owns audience, facts, terminology, and evidence. An artifact brief owns its immediate purpose, mode, detail, and composition.

Precedence: evidence fidelity, accessibility, and required publishing conventions; explicit artifact constraints; selected profile and medium adapter; philosophy defaults; vendor defaults. An exception must state the reason and scope. A venue's white paper requirement changes that export, not every project.

## Portable use

Copy this entire `design-system/` directory into another project, or maintain one shared checkout and reference it by path. Run `scripts/build.py` directly from either arrangement; it resolves its own package location. Add a scoped pointer to that project's agent instructions using `templates/AGENT_INSTRUCTIONS.md`.

Each project records its selected profile locally. Do not switch a shared global style guide when working across brands. A different identity gets a new profile; audience and product facts stay in the project. Generated output belongs in the project's ignored build directory.

The Study 2 example has a portable evidence snapshot and does not require private run data to build. Its source paths and SHA-256 receipts identify the original analyses. To refresh it from this standalone workspace, explicitly select the research checkout:

```sh
python3 design-system/scripts/build.py --refresh-evidence --evidence-root ../scale-invariance --embed-fonts
python3 design-system/scripts/build.py --check
python3 design-system/scripts/test_build.py
```

Refreshing never reruns analysis. `--check` checks token-derived output, source receipts when available, and the statistical summary independently from fixture values. Use `--evidence-root ../scale-invariance` with `--check` to verify the original source hashes. Missing original sources are reported as snapshot-only, rather than preventing portable builds.

## Reusable vocabulary

**Brief → structure → compose → distill → review → publish.**

- Critique: assess purpose, hierarchy, coherence, and fit.
- Audit: check correctness, accessibility, states, and output behavior.
- Distill: remove redundancy while preserving meaning.
- Adapt: recompose for a destination.
- Polish: reconcile the last details with the chosen system.

Use Impeccable for frontend craft and Diagram Design for publication diagrams where available. These words also work as ordinary requests; neither tool is required to use this package.

## Contents

- `PHILOSOPHY.md`: personal doctrine and practical decision rules.
- `profiles/dawn-state/`: normative tokens and integration notes.
- `adapters/`: web, documents, slides, diagrams, and charts.
- `patterns/`: six cross-medium information structures.
- `templates/`: project context, artifact brief, agent pointer, review receipt.
- `examples/scale-invariance/`: actual Study 2 evidence and calibration brief.
- `scripts/build.py`: standard-library generator and validation.
- `assets/layout.css`: shared presentation geometry; colors and profile scales are generated.
- `SOURCES.md`: influences and adaptation decisions.
