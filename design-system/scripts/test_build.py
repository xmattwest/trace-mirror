"""Meaningful failure checks and a clean-room portable-package build."""

import copy
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("warm_precision_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class DocumentStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.text = []
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs["href"])
        if tag not in {"input", "br"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        self.assert_balanced(tag)

    def assert_balanced(self, tag):
        assert self.stack and self.stack.pop() == tag, f"Unbalanced document tag: {tag}"

    def handle_data(self, data):
        if data.strip():
            self.text.append((data.strip(), tuple(self.stack)))


class MarkdownDocuments(unittest.TestCase):
    def test_nested_release_steps_preserve_list_relationships(self):
        text = "1. Publish research.\n2. Explain it:\n   - Share a figure.\n   - Link the evidence.\n3. Invite replication."
        structure = DocumentStructure()
        structure.feed(build.markdown(text, build.PROJECT / "example.md", {}))
        self.assertEqual([value for value, _ in structure.text],
                         ["Publish research.", "Explain it:", "Share a figure.", "Link the evidence.", "Invite replication."])
        self.assertIn(("Share a figure.", ("ol", "li", "ul", "li", "p")), structure.text)
        self.assertIn(("Invite replication.", ("ol", "li", "p")), structure.text)
        self.assertEqual(structure.stack, [])

    def test_quoted_requirements_checklists_and_literal_html_survive(self):
        text = '> Preserve search access.\n\n- [ ] Verify indexing.\n- [x] Read the plan.\n\n<https://example.com/work>\n\n<script>alert("unsafe")</script>'
        rendered = build.markdown(text, build.PROJECT / "example.md", {})
        structure = DocumentStructure()
        structure.feed(rendered)
        self.assertIn(("Preserve search access.", ("blockquote", "p")), structure.text)
        self.assertEqual(rendered.count('type="checkbox"'), 2)
        self.assertIn("disabled checked", rendered)
        self.assertIn("https://example.com/work", structure.links)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_navigation_has_unique_heading_targets_and_a_source_download(self):
        path = build.PROJECT / "example.md"
        text = "# Example guide\n\n## Same section\n\nFirst.\n\n## Same section\n\nSecond."
        rendered = build.workspace_document(text, path, {})
        structure = DocumentStructure()
        structure.feed(rendered)
        self.assertEqual(len(structure.ids), len(set(structure.ids)))
        for link in structure.links:
            if link.startswith("#"):
                self.assertIn(link[1:], structure.ids)
        self.assertIn("example.md", structure.links)
        self.assertIn('download="example.md"', rendered)
        self.assertLess(rendered.index("Example guide"), rendered.index("On this page"))


class EvidenceAndPortability(unittest.TestCase):
    def setUp(self):
        self.evidence = build.read_json(build.EXAMPLE / "evidence.json")
        self.profile = build.read_json(build.PROFILE)

    def test_mean_tampering_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["rows"][0]["mean_d"] += .01
        with self.assertRaises(AssertionError):
            build.validate_evidence(evidence)

    def test_non_significance_cannot_replace_equivalence(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["rows"][1]["ci90"][1] = .11
        evidence["rows"][1]["equivalent"] = True
        with self.assertRaises(AssertionError):
            build.validate_evidence(evidence)

    def test_unsafe_accent_text_is_rejected(self):
        profile = copy.deepcopy(self.profile)
        profile["roles"]["text-primary"] = "golden-orange"
        with self.assertRaises(AssertionError):
            build.validate_profile(profile)

    def test_agreement_denominator_mismatch_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["rows"][0]["terminals_by_scale"]["x1e8"]["AGREEMENT"] -= 1
        with self.assertRaises(AssertionError):
            build.validate_evidence(evidence)

    def test_package_builds_without_original_project_or_data(self):
        with tempfile.TemporaryDirectory(prefix="warm-precision-") as directory:
            root = Path(directory)
            # Assemble the exact public bundle; no copied private derived/ or data/.
            build.bundle(root)
            import zipfile
            with zipfile.ZipFile(root / "warm-precision-kit.zip") as archive:
                archive.extractall(root / "clean-room")
            clean = root / "clean-room"
            result = subprocess.run([sys.executable, "design-system/scripts/build.py", "--out", "preview"],
                                    cwd=clean, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("6 snapshot-only", result.stdout)
            self.assertTrue((clean / "preview/index.html").exists())
            for path in build.WORKSPACE_DOCS:
                slug = build.doc_slug(path)
                self.assertEqual((clean / path.name).read_text(), path.read_text())
                self.assertTrue((clean / "preview/handbook" / slug).exists())
                self.assertEqual((clean / "preview/handbook" / slug.replace(".html", ".md")).read_text(), path.read_text())
                if path.name == "DISCOVERABILITY_PLAN.md":
                    self.assertTrue((clean / "preview/handbook/discoverability-plan-reference.html").exists())
                    self.assertIn("Make your work", (clean / "preview/handbook" / slug).read_text())
                if path.name == "OPENCODE_INSIGHTS.md":
                    self.assertTrue((clean / "preview/handbook/opencode-insights-reference.html").exists())
                    self.assertTrue((clean / "preview/handbook/opencode-insights-evidence.json").exists())
                    self.assertTrue((clean / "preview/handbook/opencode-monthly-project-tokens.json").exists())
                    self.assertIn("Many projects.", (clean / "preview/handbook" / slug).read_text())
            self.assertFalse((clean / "derived").exists())

    def test_mirror_download_runs_and_exports_outside_the_workspace(self):
        import sqlite3
        import zipfile
        with tempfile.TemporaryDirectory(prefix="mirror-portable-") as directory:
            root = Path(directory)
            build.mirror_bundle(root, self.profile, "/* offline font test */")
            with zipfile.ZipFile(root / "opencode-mirror.zip") as archive:
                self.assertFalse(any(name.endswith((".db", ".pyc", ".json")) for name in archive.namelist()))
                self.assertIn("opencode-mirror/FONT_LICENSES.txt", archive.namelist())
                archive.extractall(root / "clean-room")
            database = root / "empty.db"
            connection = sqlite3.connect(database)
            connection.executescript("CREATE TABLE session(id TEXT); CREATE TABLE message(id TEXT,session_id TEXT,data TEXT); CREATE TABLE part(id TEXT,message_id TEXT,data TEXT);")
            connection.close()
            output = root / "export.html"
            result = subprocess.run([sys.executable, "mirror.py", "--db", str(database), "--export", str(output)],
                                    cwd=root / "clean-room/opencode-mirror", text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rendered = output.read_text()
            self.assertIn('"shared": true', rendered)
            self.assertIn("An Early Sketch", rendered)
            self.assertIn(self.profile["colors"]["ivory"], rendered)
            self.assertNotIn("{{theme}}", rendered)
            self.assertNotIn("{{data}}", rendered)

    def test_public_bundle_excludes_local_reports_and_builds_in_isolation(self):
        import zipfile
        from unittest.mock import patch
        docs = [path for path in build.WORKSPACE_DOCS if path.name in build.PUBLIC_DOCS]
        public_docs = [path for path in build.DOCS if path not in build.WORKSPACE_DOCS or path in docs]
        with tempfile.TemporaryDirectory(prefix="warm-precision-public-") as directory:
            root = Path(directory)
            with patch.object(build, "PUBLIC", True), patch.object(build, "WORKSPACE_DOCS", docs), patch.object(build, "DOCS", public_docs):
                build.bundle(root)
            with zipfile.ZipFile(root / "warm-precision-kit.zip") as archive:
                for forbidden in ("OPENCODE_INSIGHTS", "OPENCODE_DATABASE", "PERSONAL_COLLABORATION", "DISCOVERABILITY_PLAN", "local_documents", "trace_token_snapshot", "design-system/documents/", "tools/opencode-mirror/BRIEF", "tools/opencode-mirror/REVIEW", "explore.py", "explore.js"):
                    self.assertFalse(any(forbidden in name for name in archive.namelist()), forbidden)
                archive.extractall(root / "source")
            clean = root / "source"
            result = subprocess.run([sys.executable, "design-system/scripts/build.py", "--public", "--out", "preview"], cwd=clean, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((clean / "preview/handbook/opencode-mirror.html").exists())
            self.assertFalse((clean / "preview/handbook/opencode-insights.html").exists())


if __name__ == "__main__":
    unittest.main()
