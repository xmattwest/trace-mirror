from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


class PortabilityTests(unittest.TestCase):
    def test_download_runs_and_exports_without_the_workspace_or_network(self):
        with tempfile.TemporaryDirectory(prefix="mirror-portable-") as directory:
            root = Path(directory)
            site = build.build(root / "site")
            with zipfile.ZipFile(site / "opencode-mirror.zip") as archive:
                self.assertTrue(all(name.startswith("opencode-mirror/") for name in archive.namelist()))
                self.assertFalse(any("design-system" in name or name.endswith((".db", ".pyc")) for name in archive.namelist()))
                archive.extractall(root / "source")
            database = root / "empty.db"
            connection = sqlite3.connect(database)
            connection.executescript("CREATE TABLE session(id TEXT); CREATE TABLE message(id TEXT,session_id TEXT,data TEXT); CREATE TABLE part(id TEXT,message_id TEXT,data TEXT);")
            connection.close()
            output = root / "mirror.html"
            result = subprocess.run([sys.executable, "mirror.py", "--db", str(database), "--export", str(output)], cwd=root / "source/opencode-mirror", text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            html = output.read_text()
            self.assertIn('"shared": true', html)
            self.assertIn("An Early Sketch", html)
            self.assertIn("data:font/woff2;base64,", html)
            self.assertNotIn("{{", html)
            self.assertNotIn("@import", html)
            self.assertNotIn("url(https:", html)

    def test_site_contains_only_the_product_handbook_and_download(self):
        with tempfile.TemporaryDirectory(prefix="mirror-site-") as directory:
            site = build.build(Path(directory))
            page = (site / "index.html").read_text()
            self.assertIn("<h1>OpenCode Mirror</h1>", page)
            self.assertIn('href="opencode-mirror.zip"', page)
            for removed in ("Warm Precision", "Dawn State", "Study 2", "Preference atlas", "Conversation score"):
                self.assertNotIn(removed, page)
            self.assertFalse((site / "warm-precision-kit.zip").exists())


if __name__ == "__main__":
    unittest.main()
