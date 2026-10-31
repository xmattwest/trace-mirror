from pathlib import Path
import os
import socket
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
                self.assertIn("opencode-mirror/agent-setup.md", archive.namelist())
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
            self.assertIn('href="agent-setup.md"', page)
            self.assertEqual((site / "agent-setup.md").read_text(), (build.ROOT / "agent-setup.md").read_text())
            for removed in ("Warm Precision", "Dawn State", "Study 2", "Preference atlas", "Conversation score"):
                self.assertNotIn(removed, page)
            self.assertFalse((site / "warm-precision-kit.zip").exists())

    def test_occupied_port_has_an_actionable_error_without_creating_an_archive(self):
        with tempfile.TemporaryDirectory(prefix="mirror-first-run-") as directory, socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            env = {**os.environ, "XDG_DATA_HOME": directory}
            result = subprocess.run([sys.executable, str(build.ROOT / "mirror.py"), "--no-open", "--port", str(port)], env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"Port {port} is already in use", result.stderr)
            self.assertIn("--port 0", result.stderr)
            self.assertFalse((Path(directory) / "opencode/opencode.db").exists())


if __name__ == "__main__":
    unittest.main()
