#!/usr/bin/env python3
"""Build Warm Precision's portable handbook and evidence-backed calibration.

Standard library only. No analysis, infrastructure calls, or installed skills.
"""

import argparse
import base64
from datetime import date
from fractions import Fraction
import hashlib
import html
import json
import math
from pathlib import Path
import re
import statistics
import sys
import urllib.request
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
PROJECT = PACKAGE.parent
PROFILE = PACKAGE / "profiles/dawn-state/tokens.json"
EXAMPLE = PACKAGE / "examples/scale-invariance"
FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&display=swap"
RUNS = (
    ("Gemma 4 · 31B", "s2-gemma-4-31b-it-20261004T012932Z"),
    ("Qwen3.8 · 27B FP8", "s2-qwen3.8-27b-fp8-20261003T223042Z"),
)
DOCS = [PACKAGE / "README.md", PACKAGE / "PHILOSOPHY.md",
        PACKAGE / "profiles/dawn-state/INTEGRATION.md",
         *(PACKAGE / "adapters" / f"{name}.md" for name in ("web", "documents", "slides", "diagrams", "charts", "motion")),
        PACKAGE / "patterns/README.md",
        *(PACKAGE / "templates" / f"{name}.md" for name in
          ("ARTIFACT_BRIEF", "PROJECT_CONTEXT", "AGENT_INSTRUCTIONS", "REVIEW_RECEIPT")),
        EXAMPLE / "BRIEF.md", EXAMPLE / "REVIEW.md", PACKAGE / "SOURCES.md"]
if (PROJECT / "BRAND_KIT.md").exists():
    DOCS.insert(2, PROJECT / "BRAND_KIT.md")
WORKSPACE_DOCS = sorted(path for path in PROJECT.glob("*.md")
                        if path.name not in {"README.md", "AGENTS.md", "BRAND_KIT.md"})
DOCS.extend(WORKSPACE_DOCS)
PUBLIC = False
PUBLIC_DOCS = {"OPENCODE_MIRROR.md"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def rgb(hex_value):
    return [int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def luminance(channels):
    return sum(weight * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
               for weight, v in zip((.2126, .7152, .0722), channels))


def contrast(foreground, background):
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + .05) / (a + .05)


def resolved(profile):
    return {role: profile["colors"][name] for role, name in profile["roles"].items()}


def validate_profile(profile):
    assert profile["schema"] == "warm-precision-profile/1"
    assert all(re.fullmatch(r"#[0-9A-F]{6}", value) for value in profile["colors"].values())
    assert set(profile["roles"].values()) <= set(profile["colors"])
    assert profile["spacing"]["scale"] == sorted(set(profile["spacing"]["scale"]))
    assert all(n % profile["spacing"]["base"] == 0 for n in profile["spacing"]["scale"])
    roles = resolved(profile)
    required = [("text-primary", "canvas"), ("text-secondary", "canvas"), ("link", "canvas"),
                ("on-structure", "structure"), ("on-emphasis", "emphasis"), ("on-positive", "outcome-positive")]
    for fg, bg in required:
        assert contrast(rgb(roles[fg]), rgb(roles[bg])) >= profile["contract"]["textContrast"], (fg, bg)
    for role in ("structure", "focus", "series-primary"):
        assert contrast(rgb(roles[role]), rgb(roles["canvas"])) >= profile["contract"]["essentialMarkContrast"]


def contrast_receipt(profile):
    roles = resolved(profile)
    pairs = [("text-primary", "canvas"), ("text-secondary", "canvas"), ("kicker", "canvas"),
               ("structure", "canvas"), ("emphasis", "canvas"), ("outcome-positive", "canvas"),
               ("on-emphasis", "emphasis"), ("on-positive", "outcome-positive")]
    receipt = [{"foreground": a, "background": b, "ratio": round(contrast(rgb(roles[a]), rgb(roles[b])), 4)}
               for a, b in pairs]
    opacity = profile["stroke"]["decorativeOpacity"]
    fg, bg = rgb(roles["structure"]), rgb(roles["canvas"])
    receipt.append({"foreground": "decorative-rule", "background": "canvas", "opacity": opacity,
                    "ratio": round(contrast([opacity * a + (1 - opacity) * b for a, b in zip(fg, bg)], bg), 4),
                    "essential": False})
    return {"schema": "warm-precision-contrast/1", "profile": profile["version"], "pairs": receipt,
            "note": "Orange/sage on Ivory require dark essential support. Decorative opacity is not a structural role."}


def tokens_css(profile):
    values = {**profile["colors"], **resolved(profile)}
    for role, data in profile["typography"].items():
        values[f"font-{role}"] = f'"{data["family"]}", {data["fallback"]}'
        values[f"weight-{role}"] = str(data["weight"])
    values.update({f"space-{n}": f"{n}px" for n in profile["spacing"]["scale"]})
    for group in ("radius", "stroke"):
        for key, value in profile[group].items():
            if key != "unit":
                values[f"{group}-{key}"] = str(value) if key == "decorativeOpacity" else f"{value}{profile[group]['unit']}"
    for medium, data in profile["media"].items():
        for key, value in data.items():
            if key == "unit":
                continue
            suffix = "" if key == "lineHeight" else "ch" if key == "measureCh" else "mm" if key == "marginMm" else data["unit"]
            values[f"{medium}-{key}"] = f"{value}{suffix}"
    values["motion-duration"] = f"{profile['motion']['durationMs']}ms"
    values["motion-easing"] = profile["motion"]["easing"]
    rule = rgb(resolved(profile)["structure"])
    values["rule-decorative"] = f"rgb({' '.join(str(round(c * 255)) for c in rule)} / {profile['stroke']['decorativeOpacity']})"
    return "/* Generated from profiles/dawn-state/tokens.json. */\n:root {\n" + "".join(
        f"  --{key}: {value};\n" for key, value in values.items()) + "}\n"


def brand_reference(profile):
    meanings = {"ivory": "Canvas and open space", "onyx": "Primary text", "blue-slate": "Structure, links, essential marks",
                "golden-orange": "Scarce editorial emphasis", "sage-green": "Positive or secondary cue",
                "slate-deep": "Secondary text, darker structure", "copper-deep": "Kickers and small accent text",
                "sage-deep": "Text-safe positive cue", "parchment": "Detail wells, never a second canvas"}
    lines = ["| Color | Exact value | Role |", "| --- | --- | --- |"]
    lines += [f"| {name.replace('-', ' ').title()} | `{value}` | {meanings[name]} |" for name, value in profile["colors"].items()]
    lines += ["", "| Typography | Family | Weight |", "| --- | --- | --- |"]
    lines += [f"| {name.title()} | {data['family']} | {data['weight']} |" for name, data in profile["typography"].items()]
    lines += ["", "| Medium | Body / primary labels | Supporting text |", "| --- | --- | --- |"]
    for name, data in profile["media"].items():
        main = data.get("body", data.get("label"))
        lines.append(f"| {name.title()} | {main} {data['unit']} | {data['caption']} {data['unit']} |")
    lines += ["", f"Digital container radii: {profile['radius']['small']}–{profile['radius']['container']} px. "
              f"Digital structural/emphasis strokes: {profile['stroke']['structural']}/{profile['stroke']['emphasis']} px. "
              f"Decorative rules: {profile['stroke']['decorative']} px at {profile['stroke']['decorativeOpacity']:.0%} Blue Slate."]
    return "\n".join(lines)


def update_brand(profile):
    path = PROJECT / "BRAND_KIT.md"
    text = path.read_text(encoding="utf-8")
    pattern = r"(<!-- dawn-state-tokens:start -->\n).*?(\n<!-- dawn-state-tokens:end -->)"
    changed, count = re.subn(pattern, lambda m: m[1] + brand_reference(profile) + m[2], text, flags=re.S)
    assert count == 1, "BRAND_KIT.md must have exactly one generated reference block"
    write(path, changed)


def refresh_evidence(evidence_root=PROJECT):
    summary_path = evidence_root / "derived/cross_model/summary.json"
    summary = read_json(summary_path)
    sources = [summary_path, evidence_root / "prereg/PREREGISTRATION.md",
               evidence_root / "prereg/study2/PREREGISTRATION.md", evidence_root / "config/fixtures.json"]
    rows = []
    for label, run in RUNS:
        path = evidence_root / f"derived/{run}/primary.json"
        p = read_json(path)
        sources.append(path)
        rows.append({"label": label, "model": p["model"], "run_id": run, "source": str(path.relative_to(evidence_root)),
                     "mean_d": p["mean_d"], "ci90": p["bootstrap"]["ci90_mean"], "ci95": p["bootstrap"]["ci95_mean"],
                     "fixtures_total": p["fixtures"], "fixtures_in_test": p["fixtures_in_test"],
                     "fixtures_using_both_openers": p["fixtures_using_both_openers"], "games_scored": p["games_scored"],
                     "equivalent": p["H2_equivalent_within_0.10"], "p_holm": summary["families"]["study2_H1"]["p_holm"][p["model"]],
                     "d_i": p["d_i"], "terminals_by_scale": p["terminals_by_scale"],
                     "bootstrap_resamples": p["bootstrap"]["resamples"]})
    evidence = {"schema": "warm-precision-evidence/1", "scope": "Study 2 completed open-weight models only",
                "status": "registered primary analyses; cross-model comparison descriptive", "snapshot_date": date.today().isoformat(),
                "contrast": "$100M minus $100", "unit": "seller-share fraction", "margin": .10,
                "reference_values": [100, 100000, 100000000], "rows": rows,
                "source_receipts": [{"path": str(p.relative_to(evidence_root)), "sha256": digest(p)} for p in sources]}
    validate_evidence(evidence)
    write(EXAMPLE / "evidence.json", json_text(evidence))


def validate_evidence(evidence):
    assert evidence["schema"] == "warm-precision-evidence/1"
    for row in evidence["rows"]:
        # Recompute the mean from exact rational fixture values, independently of displayed labels.
        values = [float(Fraction(v["num"], v["den"])) for v in row["d_i"].values()]
        assert len(values) == row["fixtures_in_test"]
        assert math.isclose(statistics.mean(values), row["mean_d"], abs_tol=1e-12)
        for interval in (row["ci90"], row["ci95"]):
            assert len(interval) == 2 and interval[0] <= row["mean_d"] <= interval[1]
        assert row["ci95"][0] <= row["ci90"][0] <= row["ci90"][1] <= row["ci95"][1]
        margin = evidence["margin"]
        assert row["equivalent"] == (-margin < row["ci90"][0] and row["ci90"][1] < margin)
        assert sum(sum(v.values()) for v in row["terminals_by_scale"].values()) == row["games_scored"]
        assert 0 <= row["p_holm"] <= 1


def font_assets(out, embed):
    if not embed:
        return f'@import url("{FONT_URL}");\n', {"mode": "web", "stylesheet": FONT_URL,
                 "fallback": "Inter/Plus Jakarta Sans unavailable: profile system stacks; verify before publishing"}
    css_path, receipt_path = out / "fonts.css", out / "font-receipt.json"
    if css_path.exists() and receipt_path.exists():
        receipt = read_json(receipt_path)
        if receipt.get("mode") == "embedded" and receipt.get("stylesheet") == FONT_URL:
            text = css_path.read_text(encoding="utf-8")
            if hashlib.sha256(text.encode()).hexdigest() == receipt.get("css_sha256"):
                return text, receipt
    request = urllib.request.Request(FONT_URL, headers={"User-Agent": "WarmPrecision/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        css = response.read().decode()
    assets = []
    for url in dict.fromkeys(re.findall(r"url\((https://[^)]+)\)", css)):
        if not url.startswith("https://fonts.gstatic.com/"):
            raise ValueError(f"Unexpected font asset host: {url}")
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
            mime = response.headers.get_content_type()
        css = css.replace(url, f"data:{mime};base64,{base64.b64encode(data).decode()}")
        assets.append({"url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    assert assets and "@font-face" in css
    return css, {"mode": "embedded", "stylesheet": FONT_URL, "assets": assets,
                 "css_sha256": hashlib.sha256(css.encode()).hexdigest(),
                  "families": {"Inter": [400, 500, 600], "Newsreader": [400, 500, 600]},
                 "note": "Public Google Fonts, embedded for offline viewing. See font-license links on the handbook."}


def pp(value, digits=1):
    return f"{value * 100:+.{digits}f}".replace("-", "−")


def interval_text(values, digits=1):
    return f"{pp(values[0], digits)} to {pp(values[1], digits)}"


def result_table(evidence):
    rows = []
    for r in evidence["rows"]:
        status = "Meets ±10 pp margin, narrowly" if r["equivalent"] else "Negative shift; not equivalent"
        rows.append(f'<tr><th scope="row">{html.escape(r["label"])}</th><td>{pp(r["mean_d"])} pp</td>'
                    f'<td>{interval_text(r["ci90"])} pp</td><td>{interval_text(r["ci95"])} pp</td>'
                    f'<td>{r["fixtures_in_test"]}/{r["fixtures_total"]}</td><td>{status}</td></tr>')
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Result table, scroll horizontally if needed"><table><caption>Study 2 · registered primary closing-share contrast</caption><thead><tr><th scope="col">Model</th><th scope="col">Mean change</th><th scope="col">90% CI</th><th scope="col">95% CI</th><th scope="col">Fixtures</th><th scope="col">Interpretation</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'


def figure_svg(profile, evidence, font_css, slug="seller-share", slide=False):
    colors = resolved(profile)
    ink, structure = colors["text-primary"], colors["structure"]
    label = 36 if slide else 24
    small = 28 if slide else 22
    x = lambda v: 392 + (v + .4) / .6 * 536
    text = lambda value, xx, yy, size=label, **attrs: '<text ' + " ".join(
        f'{key.replace("_", "-")}="{html.escape(str(val), quote=True)}"' for key, val in
        {"x": xx, "y": yy, "font_size": size, **attrs}.items()) + '>' + html.escape(value) + '</text>'
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" class="interval-plot" viewBox="0 0 1280 520" role="img" aria-labelledby="{slug}-title {slug}-desc">',
              f'<title id="{slug}-title">Seller-share response differs between the two Study 2 models</title>',
              f'<desc id="{slug}-desc">Change is $100 million minus $100. Gemma mean {pp(evidence["rows"][0]["mean_d"])} percentage points, Qwen {pp(evidence["rows"][1]["mean_d"])}. Thick intervals are 90 percent and thin intervals are 95 percent. Dashed references mark the registered plus or minus ten point equivalence margin. See the adjacent table for exact intervals and sample sizes.</desc>',
              '<defs><style><![CDATA[' + font_css + f' text {{font-family:"{profile["typography"]["body"]["family"]}",Arial,sans-serif;fill:{ink};}}' + ']]></style></defs>',
              f'<rect width="1280" height="520" fill="{colors["canvas"]}"/>',
              text("Closing seller share · $100M − $100", 32, 48, 32, font_weight=600)]
    for tick in (-.4, -.3, -.2, -.1, 0, .1, .2):
        if tick in (-.1, 0, .1):
            dash = ' stroke-dasharray="8 8"' if tick else ""
            pieces.append(f'<line x1="{x(tick):.3f}" x2="{x(tick):.3f}" y1="88" y2="340" stroke="{structure}" stroke-width="2"{dash}/>')
        pieces.append(text(f"{tick * 100:+.0f}".replace("-", "−") if tick else "0", x(tick), 382, small, text_anchor="middle"))
    for i, row in enumerate(evidence["rows"]):
        y = 164 + i * 136
        pieces += [text(row["label"], 32, y - 6, label, font_weight=600),
                   text(f'{row["fixtures_in_test"]} fixtures · {row["games_scored"]} games', 32, y + 30, small)]
        for ci, width in ((row["ci95"], 2), (row["ci90"], 7)):
            pieces.append(f'<line x1="{x(ci[0]):.3f}" x2="{x(ci[1]):.3f}" y1="{y}" y2="{y}" stroke="{structure}" stroke-width="{width}"/>')
        if i == 0:
            pieces.append(f'<circle cx="{x(row["mean_d"]):.3f}" cy="{y}" r="9" fill="{colors["emphasis"]}" stroke="{structure}" stroke-width="3"/>')
        else:
            pieces.append(f'<rect x="{x(row["mean_d"]) - 9:.3f}" y="{y - 9}" width="18" height="18" fill="{colors["outcome-positive"]}" stroke="{structure}" stroke-width="3"/>')
        pieces += [text(f'{pp(row["mean_d"])} pp', 976, y, 36, font_weight=600),
                   text(f'90%: {interval_text(row["ci90"])}', 976, y + 34, small)]
    pieces += [text("Seller-share change · percentage points", 660, 424, small, text_anchor="middle"),
               text("Thick: 90% CI · thin: 95% CI · dashed: ±10 pp margin", 32, 474, small),
               text("Fixture-bootstrap intervals; comparison across models is descriptive.", 32, 506, 20)]
    return "\n".join(pieces) + "\n</svg>"


def page(title, body, kind="", prefix="", font_mode="embedded", styles=()):
    page_title = title if title == "Warm Precision" else f"{title} · Warm Precision"
    extra_styles = "".join(f'<link rel="stylesheet" href="{prefix}{html.escape(name, quote=True)}">' for name in styles)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(page_title)}</title><meta name="description" content="A design handbook for research, documents, diagrams and software."><meta property="og:title" content="{html.escape(page_title, quote=True)}"><meta property="og:description" content="A design handbook for research, documents, diagrams and software."><meta property="og:type" content="website"><meta name="twitter:card" content="summary"><link rel="icon" href="{prefix}favicon.svg"><link rel="stylesheet" href="{prefix}tokens.css"><link rel="stylesheet" href="{prefix}fonts.css"><link rel="stylesheet" href="{prefix}layout.css">{extra_styles}</head>
<body class="{kind}"><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><a href="{prefix}index.html" class="wordmark">Warm Precision</a><nav aria-label="Primary"><a href="{prefix}index.html#handbook">Handbook</a><a href="{prefix}index.html#calibration">Examples</a><a href="https://github.com/xmattwest/trace-mirror">GitHub</a></nav></header>
<main id="main">{body}</main><footer class="site-footer"><p>Dawn State profile</p><a href="{prefix}warm-precision-kit.zip">Download source</a><a href="{prefix}handbook/SOURCES.html">Sources</a></footer></body></html>'''


def doc_slug(path):
    if path.parent == PROJECT:
        return path.stem.lower().replace("_", "-") + ".html"
    return "-".join(path.relative_to(PACKAGE).with_suffix("").parts) + ".html"


def markdown(text, source, doc_map, headings=None):
    """Render the package's deliberately small Markdown vocabulary, escaping HTML."""
    headings = [] if headings is None else headings
    heading_ids = set()
    def inline(value):
        slots = []
        def stash(body):
            slots.append(body)
            return f"\x00{len(slots) - 1}\x00"
        value = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{html.escape(m[1])}</code>"), value)
        def link(match):
            label, target = match.groups()
            if target.startswith(("https://", "http://", "#")):
                url = target
            else:
                target, separator, fragment = target.partition("#")
                candidate = (source.parent / target).resolve()
                if candidate in doc_map:
                    url = doc_map[candidate] + (separator + fragment if separator else "")
                elif candidate.is_dir():
                    url = "../index.html#handbook"
                else:
                    return stash(html.escape(label))
            return stash(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, value)
        value = re.sub(r"<((?:https?://|mailto:)[^<>\s]+)>",
                       lambda m: stash(f'<a href="{html.escape(m[1], quote=True)}">{html.escape(m[1])}</a>'), value)
        value = html.escape(value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        return re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m[1])], value)
    lines = text.splitlines()
    output, paragraph = [], []
    def flush():
        if paragraph:
            body = "".join(inline(line.strip()) + ("<br>" if line.endswith("  ") else " ")
                           for line in paragraph).strip()
            output.append("<p>" + body + "</p>")
            paragraph.clear()
    list_pattern = r"^(\s*)([-+*]|\d+\.)\s+(.*)$"
    def render_list(start):
        first = re.match(list_pattern, lines[start])
        indent = len(first[1])
        kind = "ol" if first[2][0].isdigit() else "ul"
        attrs = f' start="{int(first[2][:-1])}"' if kind == "ol" and first[2] != "1." else ""
        items = [f"<{kind}{attrs}>"]
        index = start
        while index < len(lines):
            match = re.match(list_pattern, lines[index])
            if not match or len(match[1]) != indent or ("ol" if match[2][0].isdigit() else "ul") != kind:
                break
            content_indent = len(match[1]) + len(match[2]) + 1
            item = [match[3]]
            index += 1
            while index < len(lines):
                line = lines[index]
                if line.strip() and len(line) - len(line.lstrip()) < content_indent:
                    break
                item.append(line[content_indent:] if line.strip() else "")
                index += 1
            task = re.match(r"^\[([ xX])\]\s+(.*)$", item[0])
            if task:
                item[0] = task[2]
                checked = " checked" if task[1].lower() == "x" else ""
                control = f'<input type="checkbox" disabled{checked} aria-label="{html.escape(task[2], quote=True)}">'
                items.append('<li class="task-item">' + control + markdown("\n".join(item), source, doc_map) + '</li>')
            else:
                items.append("<li>" + markdown("\n".join(item), source, doc_map) + "</li>")
        items.append(f"</{kind}>")
        return "\n".join(items), index
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i]); i += 1
            output.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
        elif re.match(r"^#{1,6} ", line):
            flush()
            level = len(line.split(" ", 1)[0])
            title = line[level + 1:]
            plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title).replace("`", "").replace("*", "")
            base = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or "section"
            anchor, suffix = base, 2
            while anchor in heading_ids:
                anchor = f"{base}-{suffix}"; suffix += 1
            heading_ids.add(anchor)
            headings.append((level, plain, anchor))
            output.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            output.append('<div class="table-scroll" tabindex="0" role="region" aria-label="Reference table"><table>')
            output.append("<thead><tr>" + "".join(f'<th scope="col">{inline(c)}</th>' for c in rows[0]) + "</tr></thead><tbody>")
            for row in rows[1:]:
                output.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            output.append("</tbody></table></div>")
            continue
        elif re.match(list_pattern, line):
            flush()
            rendered, i = render_list(i)
            output.append(rendered)
            continue
        elif line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(re.sub(r"^> ?", "", lines[i])); i += 1
            output.append("<blockquote>" + markdown("\n".join(quote), source, doc_map) + "</blockquote>")
            continue
        elif not line.strip() or line == "---":
            flush()
        elif line.startswith("<!--"):
            pass
        else:
            paragraph.append(line)
        i += 1
    flush()
    return "\n".join(output)


def workspace_document(text, path, doc_map):
    headings = []
    content = markdown(text, path, doc_map, headings)
    first_section = re.search(r"<h2\b", content)
    intro = content[:first_section.start()] if first_section else content
    content = content[first_section.start():] if first_section else ""
    links = "".join(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>'
                    for level, title, anchor in headings if level == 2)
    navigation = f'<aside class="document-outline"><nav aria-label="On this page"><p class="context">On this page</p><ol>{links}</ol></nav></aside>' if links else ""
    source = doc_slug(path).replace(".html", ".md")
    header = f'<header class="wrap document document-intro">{intro}<p class="document-tools"><a href="{source}" download="{html.escape(path.name, quote=True)}">Download Markdown source</a></p></header>'
    return header + (f'<div class="wrap document-layout">{navigation}<article class="document document-content">{content}</article></div>' if content else "")


def discoverability_map(profile, variant, font_css=""):
    graph = read_json(PACKAGE / "documents/discoverability/source-map.json")
    layout = graph["layouts"][variant]
    roles = resolved(profile)
    structure, canvas = roles["structure"], roles["canvas"]
    slug = f"source-map-{variant}"
    mobile = variant == "mobile"
    title_size, detail_size, line_height = (22, 20, 28) if mobile else (20, 16, 24)
    stroke = profile["stroke"]["structural"]
    font = profile["typography"]["body"]["family"]
    padding = profile["spacing"]["base"] if mobile else 0
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert set(layout["positions"]) == set(nodes), "Diagram layout must preserve every node"
    assert set(layout["routes"]) == {edge["id"] for edge in graph["edges"]}, "Diagram layout must preserve every relationship"
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" class="map-{variant}" viewBox="{-padding} 0 {layout["width"] + padding * 2} {layout["height"]}" role="img" aria-labelledby="{slug}-title {slug}-description">',
              f'<title id="{slug}-title">{html.escape(graph["title"])}</title>',
              f'<desc id="{slug}-description">{html.escape(graph["description"])}</desc>',
              '<defs><style><![CDATA[' + font_css + f' text {{ font-family: "{font}", Arial, sans-serif; }}' + ']]></style>',
              f'<marker id="{slug}-arrow" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0 0 L8 4 L0 8 Z" fill="{structure}"/></marker></defs>']
    labels = []
    for edge in graph["edges"]:
        assert edge["from"] in nodes and edge["to"] in nodes
        route = layout["routes"][edge["id"]]
        start = f' marker-start="url(#{slug}-arrow)"' if edge.get("bidirectional") else ""
        dash = ' stroke-dasharray="6 5"' if edge.get("retrieval") else ""
        pieces.append(f'<path d="{route["path"]}" fill="none" stroke="{structure}" stroke-width="{stroke}"{dash}{start} marker-end="url(#{slug}-arrow)"><title>{html.escape(edge["relationship"])}</title></path>')
        if "label" in route:
            x, y = route["labelAt"]
            size = 20 if mobile else 16
            labels.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" fill="{structure}">{html.escape(route["label"])}</text>')
    for node in graph["nodes"]:
        x, y, width, height = layout["positions"][node["id"]]
        assert 0 <= x <= x + width <= layout["width"] and 0 <= y <= y + height <= layout["height"], "Diagram node exceeds its canvas"
        focal = node.get("focal")
        title = node.get("mobileTitle", node["title"]) if mobile else node["title"]
        details = node.get("mobileDetail", node["detail"]) if mobile else node["detail"]
        fill, ink = (structure, roles["on-structure"]) if focal else (canvas, structure)
        size = 24 if focal and not mobile else title_size
        if mobile and width < 200:
            size = 20
        if not mobile and width < 248:
            size = 18
        pieces.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{profile["radius"]["container"]}" fill="{fill}" stroke="{structure}" stroke-width="{stroke}"/>')
        baseline = y + height / 2 - len(details) * line_height / 2 + 7
        pieces.append(f'<text x="{x + width / 2}" y="{baseline}" text-anchor="middle" font-size="{size}" font-weight="{profile["typography"]["heading"]["weight"]}" fill="{ink}">{html.escape(title)}</text>')
        for index, detail in enumerate(details, 1):
            pieces.append(f'<text x="{x + width / 2}" y="{baseline + index * line_height}" text-anchor="middle" font-size="{detail_size}" fill="{ink}">{html.escape(detail)}</text>')
    return "\n".join(pieces + labels + ["</svg>"])


def discoverability_overview(profile):
    template = (PACKAGE / "documents/discoverability/overview.html").read_text(encoding="utf-8")
    assert template.count("{{source_map}}") == 1
    diagrams = discoverability_map(profile, "desktop") + discoverability_map(profile, "mobile")
    return template.replace("{{source_map}}", diagrams)


if Path(__file__).with_name("local_documents.py").exists():
    sys.path.insert(0, str(Path(__file__).parent))
    from local_documents import (opencode_database_overview, opencode_overview,
                                 validate_monthly_tokens, validate_trace_evidence)


def calibration_pages(profile, evidence, font_css, mode):
    gemma, qwen = evidence["rows"]
    count = sum(v["float"] < 0 for v in gemma["d_i"].values())
    lead = f'Gemma’s seller share fell by {abs(gemma["mean_d"]) * 100:.1f} percentage points. Qwen’s mean changed by {pp(qwen["mean_d"])} points and narrowly met the registered equivalence margin.'
    method = 'Two copies of each model negotiate with private seller floors and buyer ceilings. Thirty fixed fixtures are played at $100, $100K, and $100M, with both opening orders: 180 games per model. Study 2 removes the public appraisal and its limit ranges. Seeds and non-numeric prompt templates are held fixed across scales; conversations can diverge.'
    caveat = f'Seller share is defined only for agreements. Gemma agreed in 60/60 games at both extreme scales; Qwen in 59/60 at $100 and 55/60 at $100M. Qwen’s paired contrast uses {qwen["fixtures_in_test"]}/30 fixtures (F20 excluded), and only {qwen["fixtures_using_both_openers"]} use both openers. Its upper 90% bound is {pp(qwen["ci90"][1], 2)} pp, barely inside +10; its 95% interval crosses that margin.'
    scope = 'This is the two-model Study 2 slice, not all later project evidence. Cross-model comparisons are descriptive because model families, precision, and sampling differ. These results do not identify a mechanism or a failure rate for LLMs generally.'
    caption = f'Change in fixture-mean seller share, $100M − $100. Thick intervals: 90% CI; thin: 95% CI. Dashed lines: registered ±10 pp equivalence margin. Gemma n = {gemma["fixtures_in_test"]}; Qwen n = {qwen["fixtures_in_test"]}. Each model has 180 scored games.'
    source = '<p class="source">Sources: Study 2 primary analyses, cross-model Holm summary, and prospective registrations. <a href="evidence.json">Inspect the exact snapshot and source hashes</a>.</p>'
    plot = figure_svg(profile, evidence, font_css)
    figure = f'<figure><div class="chart-scroll" tabindex="0" role="region" aria-label="Interval plot, scroll horizontally on narrow screens">{plot}</div><figcaption>{caption}</figcaption></figure>'
    web = f'''<section class="web-section wrap"><p class="context">Study 2 · registered primary contrast</p><h1>The closing response depends on the model.</h1><p class="lead">{lead}</p>{figure}<p class="mobile-hint">The chart scrolls horizontally on narrow screens. Both results and intervals are also in the table below.</p><div class="reading"><h2>Same geometry, larger numbers</h2><p>{method}</p><p>Seller share = (deal price − seller floor) / (buyer ceiling − seller floor). The reported effect averages paired changes over fixtures and available opening orders.</p><h2>Equivalence needs its own evidence</h2><p>The registered rule asks whether the entire 90% interval lies inside ±10 pp. Qwen meets that rule narrowly; a non-significant shift alone would not suffice.</p><details open><summary>Inspect the evidence and qualifications</summary>{result_table(evidence)}<p>{caveat}</p><p>{scope}</p>{source}</details><h2>Test agents where they will operate</h2><p>Evaluation at one numerical scale does not establish robustness at another. Check both opening behavior and final outcomes, with disagreement and uncertainty visible.</p></div></section>'''
    memo_rows = "".join(f'<tr><th scope="row">{html.escape(r["label"])}</th><td>{pp(r["mean_d"])} pp</td><td>{interval_text(r["ci90"])} pp</td><td>{interval_text(r["ci95"])} pp</td></tr>' for r in evidence["rows"])
    memo = f'''<article class="memo-sheet"><p class="context">Dawn State research · Study 2 · 23 October 2026</p><h1>Same bargain. Different response to scale.</h1><p class="lead">{lead}</p><h2>What was tested</h2><p>{method}</p><p>Seller share is (price − floor)/(ceiling − floor). The primary contrast is $100M − $100, averaged over paired fixtures and available opening orders.</p><h2>What the evidence says</h2><table class="memo-table"><caption>Registered closing-share contrast · percentage points</caption><thead><tr><th scope="col">Model</th><th scope="col">Mean</th><th scope="col">90% CI</th><th scope="col">95% CI</th></tr></thead><tbody>{memo_rows}</tbody></table><p>Gemma: {gemma["fixtures_in_test"]} analysed fixtures; {count}/30 changes negative. Qwen: {qwen["fixtures_in_test"]}/30 analysed fixtures. Each model: 180 scored games. Gemma fails equivalence; Qwen meets it narrowly.</p><h2>What this does not establish</h2><p>{caveat}</p><p>{scope}</p><h2>Implication</h2><p>Evaluate negotiating agents at the numerical scales where they will operate. Preserve uncertainty and agreement outcomes; do not infer general robustness from one model or one setting.</p>{source}</article>'''
    slide_plot = figure_svg(profile, evidence, font_css, slug="slide-result", slide=True)
    slides = [
        ("Should a millionfold rescaling change a bargain?", '<p class="slide-lead">The relative bargaining geometry stays the same.</p><div class="scale-strip"><strong>$100</strong><span>× 1,000,000</span><strong>$100M</strong></div><p>The question is whether the agent’s relative behavior stays the same too.</p>', 'Study 2 · fixed geometry · no public appraisal'),
        ("Change the numbers. Keep the design fixed.", '<div class="slide-columns"><div><h2>Same fixtures</h2><p>30 private-limit bargains<br>Both opening orders<br>180 games per model</p></div><div><h2>Three scales</h2><p>$100 · $100K · $100M<br>Same non-numeric templates<br>Shared seeds across scales</p></div></div><p>Each side knows only its own limit; conversations can diverge.</p>', 'Gemma 4 31B / Qwen3.8 27B FP8 · cross-model comparisons descriptive'),
        ("The split depends on the model.", f'<div class="slide-chart">{slide_plot}</div>', f'Registered primary contrast · $100M − $100 · 180 games/model · Gemma n={gemma["fixtures_in_test"]}, Qwen n={qwen["fixtures_in_test"]}'),
        ("Qwen meets the margin narrowly.", f'<p class="slide-lead">Upper 90% bound: {pp(qwen["ci90"][1], 2)} pp.<br>Registered boundary: +10 pp.</p><div class="slide-columns"><p>Qwen: 29/30 paired fixtures; 25 use both openers.<br>Agreements: 59/60 → 55/60.</p><p>Gemma: 30/30 paired fixtures.<br>Agreements: 60/60 → 60/60.</p></div><p>Seller share conditions on agreement. Qwen’s 95% interval crosses the margin; non-significance alone is not equivalence.</p>', 'Compare $100 with $100M · F20 excluded for Qwen · no population-level claim'),
        ("Test agents at the scales where they will operate.", '<p class="slide-lead">One scale does not certify another.</p><p>Measure openings and final splits.<br>Keep disagreement and uncertainty visible.<br>Separate observed effects from mechanism hypotheses.</p><p class="slide-scope">Calibration scope: two completed Study 2 models. Later studies and exploratory mechanisms are outside this example.</p>', 'Source files, exact intervals, and SHA-256 receipts: evidence.json'),
    ]
    deck = '<nav class="deck-nav" aria-label="Slide navigation">' + "".join(f'<a href="#slide-{i}">Slide {i}</a>' for i in range(1, 6)) + '</nav>'
    deck += "".join(f'<section class="slide{ " slide-result" if i == 3 else " slide-qualification" if i == 4 else ""}" id="slide-{i}" aria-labelledby="slide-{i}-heading"><div class="slide-content"><h1 id="slide-{i}-heading">{title}</h1>{body}</div><footer class="slide-footer"><span>{foot}</span><span>{i} / 5</span></footer></section>' for i, (title, body, foot) in enumerate(slides, 1))
    figure_page = f'<article class="wrap figure-page"><h1>The closing response depends on the model.</h1>{figure}<p class="lead">{lead}</p>{result_table(evidence)}<p>{caveat}</p><p>{scope}</p><p><a class="button" href="seller-share.svg" download>Download editable SVG</a> <a href="seller-share-slide.svg" download>Slide-sized labels</a></p>{source}</article>'
    memo_md = f'# Same bargain. Different response to scale.\n\n{lead}\n\n## Design\n\n{method}\n\n## Results\n\n'
    for r in evidence["rows"]:
        memo_md += f'- {r["label"]}: {pp(r["mean_d"])} pp; 90% CI {interval_text(r["ci90"])}; 95% CI {interval_text(r["ci95"])}; n={r["fixtures_in_test"]}, {r["games_scored"]} games.\n'
    memo_md += f'\n## Qualifications\n\n{caveat}\n\n{scope}\n\n## Implication\n\nEvaluate agents at their operating scales; preserve uncertainty and agreement outcomes.\n\nSource: evidence.json (exact fixture values and source SHA-256 receipts).\n'
    deck_md = '# Study 2 · five-slide explanation\n\n' + "\n\n---\n\n".join(f'## {i}. {title}\n\n' + re.sub(r'<[^>]+>', ' ', body).strip() + f'\n\nSource note: {foot}' for i, (title, body, foot) in enumerate(slides, 1))
    # SVG markup/font payloads do not belong in the editable textual deck companion.
    deck_md = deck_md[:deck_md.find("## 3.")] + f'## 3. {slides[2][0]}\n\n{lead}\n\n{caption}\n\nSource: evidence.json; seller-share-slide.svg.\n\n---\n\n' + "\n\n---\n\n".join(f'## {i}. {title}\n\n' + re.sub(r'<[^>]+>', ' ', body).strip() + f'\n\nSource note: {foot}' for i, (title, body, foot) in enumerate(slides[3:], 4))
    return {"web.html": page("Study 2 · web explanation", web, font_mode=mode),
            "memo.html": page("Study 2 · one-page memo", memo, "memo", font_mode=mode),
            "slides.html": page("Study 2 · five-slide deck", deck, "deck", font_mode=mode),
            "figure.html": page("Study 2 · interval figure", figure_page, font_mode=mode),
            "seller-share.svg": plot, "seller-share-slide.svg": slide_plot,
            "memo.md": memo_md, "slides.md": deck_md}


def overlay(profile):
    roles = resolved(profile)
    mappings = {"paper / paper-2": "canvas", "ink / ink-strong": "text-primary", "muted / soft / link": "structure",
                "focal fill": "emphasis", "focal text": "on-emphasis", "essential connector / outline": "structure"}
    text = '# Generated Dawn State → Diagram Design overlay\n\nThis is adaptation guidance, not a complete vendor profile. See profiles/dawn-state/INTEGRATION.md.\n\n| Vendor role/use | Dawn State role | Value |\n| --- | --- | --- |\n'
    text += "".join(f'| {vendor} | {role} | `{roles[role]}` |\n' for vendor, role in mappings.items())
    text += f'\nTitle: {profile["typography"]["display"]["family"]} {profile["typography"]["display"]["weight"]}. Names, prose, and callouts: {profile["typography"]["body"]["family"]}. Kickers: {profile["typography"]["kicker"]["family"]} {profile["typography"]["kicker"]["weight"]}, uppercase with wide tracking, in the kicker role.\n'
    text += '\nSplit accent roles explicitly: orange fill with dark text and essential outline. Orange cannot serve as the vendor’s universal text/stroke accent on Ivory. Use canvas rather than decorative accent tints. Resolve type sizes and geometry from the destination adapter.\n'
    return text


def artifacts(profile, evidence, fonts, mode):
    outputs = calibration_pages(profile, evidence, fonts, mode)
    colors = resolved(profile)
    outputs["favicon.svg"] = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="{colors["canvas"]}"/><path d="M5 7 L10 25 L16 13 L22 25 L27 7" fill="none" stroke="{colors["structure"]}" stroke-width="3" stroke-linejoin="round"/></svg>'
    outputs.update({"tokens.css": tokens_css(profile), "tokens.resolved.json": json_text({"profile": profile, "resolvedRoles": resolved(profile)}),
                    "contrast.json": json_text(contrast_receipt(profile)), "evidence.json": json_text(evidence),
                     "layout.css": (PACKAGE / "assets/layout.css").read_text(encoding="utf-8"),
                     "motion.css": (PACKAGE / "assets/motion.css").read_text(encoding="utf-8"),
                     "motion.js": (PACKAGE / "assets/motion.js").read_text(encoding="utf-8"),
                    "diagram-design-overlay.md": overlay(profile)})
    doc_map = {path.resolve(): doc_slug(path) for path in DOCS}
    assert len(set(doc_map.values())) == len(doc_map), "Document filenames produce duplicate page URLs"
    links = {"Foundations": [], "Media": [], "Practice": [], "Local notes": []}
    for path in DOCS:
        text = path.read_text(encoding="utf-8")
        title = next(line[2:] for line in text.splitlines() if line.startswith("# "))
        slug = doc_slug(path)
        styles = ()
        if path in WORKSPACE_DOCS:
            outputs[f"handbook/{slug.replace('.html', '.md')}"] = text
            if path.name == "DISCOVERABILITY_PLAN.md":
                body = discoverability_overview(profile)
                styles = ("discoverability.css",)
                outputs["discoverability.css"] = (PACKAGE / "assets/discoverability.css").read_text(encoding="utf-8")
                outputs["handbook/discoverability-source-map.svg"] = discoverability_map(profile, "desktop", fonts)
                outputs["handbook/discoverability-plan-reference.html"] = page(
                    title + " · implementation reference",
                    '<nav class="wrap" aria-label="Overview"><a href="discoverability-plan.html">← Back to the visual plan</a></nav>' + workspace_document(text, path, doc_map),
                    prefix="../", font_mode=mode)
            elif path.name == "OPENCODE_INSIGHTS.md":
                body = opencode_overview()
                styles = ("opencode-insights.css",)
                outputs["opencode-insights.css"] = (PACKAGE / "assets/opencode-insights.css").read_text(encoding="utf-8")
                outputs["handbook/opencode-insights-evidence.json"] = (PACKAGE / "documents/opencode-insights/evidence.json").read_text(encoding="utf-8")
                outputs["handbook/opencode-monthly-project-tokens.json"] = (PACKAGE / "documents/opencode-insights/monthly-tokens.json").read_text(encoding="utf-8")
                outputs["handbook/opencode-insights-reference.html"] = page(
                    title + " · evidence and methods",
                    '<nav class="wrap" aria-label="Overview"><a href="opencode-insights.html">← Back to the visual report</a></nav>' + workspace_document(text, path, doc_map),
                    prefix="../", font_mode=mode)
            elif path.name == "OPENCODE_DATABASE.md":
                body = opencode_database_overview()
                styles = ("opencode-insights.css",)
                outputs["opencode-insights.css"] = (PACKAGE / "assets/opencode-insights.css").read_text(encoding="utf-8")
                outputs["handbook/opencode-database-inventory.json"] = (PACKAGE / "documents/opencode-insights/database-inventory.json").read_text(encoding="utf-8")
                outputs["handbook/opencode-database-reference.html"] = page(
                    title + " · fields and methods",
                    '<nav class="wrap" aria-label="Overview"><a href="opencode-database.html">← Back to contents and analysis opportunities</a></nav>' + workspace_document(text, path, doc_map),
                    prefix="../", font_mode=mode)
            elif path.name == "OPENCODE_MIRROR.md":
                body = (PACKAGE / "tools/opencode-mirror/handbook.html").read_text(encoding="utf-8")
                styles = ("mirror.css",)
                outputs["mirror.css"] = (PACKAGE / "assets/mirror.css").read_text(encoding="utf-8")
            else:
                body = workspace_document(text, path, doc_map)
        else:
            body = '<article class="wrap document">' + markdown(text, path, doc_map) + '</article>'
        outputs[f"handbook/{slug}"] = page(title, body, prefix="../", font_mode=mode, styles=styles)
        if path.name == "OPENCODE_MIRROR.md" or path.parent == EXAMPLE:
            continue
        group = ("Local notes" if path in WORKSPACE_DOCS else "Media" if path.parent.name == "adapters"
                 else "Practice" if path.parent.name in {"patterns", "templates"} else "Foundations")
        label = {PACKAGE / "README.md": "Getting started", PACKAGE / "PHILOSOPHY.md": "Principles",
                 PROJECT / "BRAND_KIT.md": "Dawn State profile", PACKAGE / "profiles/dawn-state/INTEGRATION.md": "Integration",
                 PACKAGE / "SOURCES.md": "Sources", PACKAGE / "patterns/README.md": "Patterns"}.get(path, title)
        links[group].append(f'<li><a href="handbook/{slug}">{html.escape(label)}</a></li>')
    contents = ''.join(f'<div><h3>{name}</h3><ul>{"".join(rows)}</ul></div>' for name, rows in links.items() if rows)
    index = (PACKAGE / "assets/handbook.html").read_text(encoding="utf-8").replace("{{contents}}", contents)
    outputs["index.html"] = page("Warm Precision", index, font_mode=mode)
    return outputs


def check(profile, evidence, out, evidence_root=PROJECT):
    validate_profile(profile)
    validate_evidence(evidence)
    fonts = (out / "fonts.css").read_text(encoding="utf-8")
    receipt = read_json(out / "font-receipt.json")
    if receipt["mode"] == "embedded":
        assert hashlib.sha256(fonts.encode()).hexdigest() == receipt["css_sha256"]
        assert not re.search(r'url\(["\']?https?://', fonts)
    expected = artifacts(profile, evidence, fonts, receipt["mode"])
    for name, content in expected.items():
        assert (out / name).read_text(encoding="utf-8") == content, f"Stale generated output: {name}"
    matched, missing = [], []
    for source in evidence["source_receipts"]:
        path = evidence_root / source["path"]
        if path.exists():
            assert digest(path) == source["sha256"], f"Evidence changed: {source['path']}; refresh explicitly"
            matched.append(source["path"])
        else:
            missing.append(source["path"])
    # Check all generated relative links, including handbook navigation and downloads.
    for name, content in expected.items():
        if not name.endswith(".html"):
            continue
        for link in re.findall(r'(?:href|src)="([^"]+)"', content):
            if link.startswith(("https://", "http://", "data:", "#")):
                continue
            target = (out / name).parent / link.split("#", 1)[0]
            assert target.exists(), f"Broken link: {name} → {link}"
    brand = PROJECT / "BRAND_KIT.md"
    if brand.exists() and "<!-- dawn-state-tokens:start -->" in brand.read_text():
        assert brand_reference(profile) in brand.read_text(), "Stale brand reference; use --write-brand"
    print(f"OK: profile contrast/roles, exact fixture means, CI nesting/equivalence, {len(expected)} generated artifacts, local links.")
    print(f"Evidence receipts: {len(matched)} matched; {len(missing)} snapshot-only (original files unavailable).")


def bundle(out):
    directories = ("profiles", "adapters", "patterns", "templates", "examples", "documents", "scripts", "assets", "tools")
    paths = [PACKAGE / name for name in ("README.md", "PHILOSOPHY.md", "SOURCES.md")]
    for directory in directories:
        paths.extend(p for p in (PACKAGE / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith(".")
                     and (not PUBLIC or public_source(p)))
    with zipfile.ZipFile(out / "warm-precision-kit.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, "design-system/" + str(path.relative_to(PACKAGE)))
        brand = PROJECT / "BRAND_KIT.md"
        if brand.exists():
            archive.write(brand, "BRAND_KIT.md")
        for path in WORKSPACE_DOCS:
            archive.write(path, path.name)


def mirror_bundle(out, profile, fonts):
    source = PACKAGE / "tools/opencode-mirror"
    if not source.exists():
        return
    with zipfile.ZipFile(out / "opencode-mirror.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc" and not path.name.startswith(".") and path.name not in {"BRIEF.md", "REVIEW.md"}:
                archive.write(path, "opencode-mirror/" + str(path.relative_to(source)))
        archive.writestr("opencode-mirror/assets/theme.css", tokens_css(profile))
        archive.writestr("opencode-mirror/assets/fonts.css", fonts)


def public_source(path):
    relative = path.relative_to(PACKAGE)
    return (relative.parts[0] != "documents"
            and path.name not in {"local_documents.py", "test_local_documents.py", "trace_token_snapshot.py", "discoverability.css", "opencode-insights.css"}
            and not (relative.parts[:2] == ("tools", "opencode-mirror") and path.name in {"BRIEF.md", "REVIEW.md"}))


def main():
    global PUBLIC, DOCS, WORKSPACE_DOCS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PROJECT / "handbook")
    parser.add_argument("--evidence-root", type=Path, default=PROJECT, help="Original research checkout for source-hash checks or explicit snapshot refresh")
    parser.add_argument("--embed-fonts", action="store_true", help="Fetch once and embed the actual brand fonts; reuse verified output cache")
    parser.add_argument("--refresh-evidence", action="store_true", help="Explicitly update the portable Study 2 snapshot from original analyses")
    parser.add_argument("--write-brand", action="store_true", help="Refresh only the marked generated brand reference")
    parser.add_argument("--check", action="store_true", help="Validate existing output without regenerating it")
    parser.add_argument("--public", action="store_true", help="Build only the reusable handbook and Mirror guide")
    args = parser.parse_args()
    PUBLIC = args.public
    if PUBLIC:
        DOCS = [path for path in DOCS if path not in WORKSPACE_DOCS or path.name in PUBLIC_DOCS]
        WORKSPACE_DOCS = [path for path in WORKSPACE_DOCS if path.name in PUBLIC_DOCS]
    profile = read_json(PROFILE)
    validate_profile(profile)
    if args.check:
        if args.refresh_evidence or args.write_brand:
            parser.error("--check is read-only; use mutation flags in a separate build")
        check(profile, read_json(EXAMPLE / "evidence.json"), args.out, args.evidence_root)
        return
    if args.refresh_evidence:
        refresh_evidence(args.evidence_root)
    evidence = read_json(EXAMPLE / "evidence.json")
    validate_evidence(evidence)
    if args.write_brand:
        update_brand(profile)
    args.out.mkdir(parents=True, exist_ok=True)
    fonts, receipt = font_assets(args.out, args.embed_fonts)
    write(args.out / "fonts.css", fonts)
    write(args.out / "font-receipt.json", json_text(receipt))
    for name, content in artifacts(profile, evidence, fonts, receipt["mode"]).items():
        write(args.out / name, content)
    mirror_bundle(args.out, profile, fonts)
    bundle(args.out)
    check(profile, evidence, args.out, args.evidence_root)
    print(f"Built: {args.out.resolve() / 'index.html'}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, OSError) as exc:
        print(f"Build/validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
