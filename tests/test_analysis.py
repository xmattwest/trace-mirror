import hashlib
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze import ArchiveError, analyze, assess, connect_archive, local_timezone, share_report
from mirror import MirrorServer, export_report, render_page

BASE = 1781226000000


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "opencode.db"
        self.db = sqlite3.connect(self.path)
        self.db.executescript("""
            CREATE TABLE session(id TEXT, parent_id TEXT, directory TEXT, time_created INTEGER);
            CREATE TABLE message(id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
            CREATE TABLE part(id TEXT, message_id TEXT, time_created INTEGER, data TEXT);
            CREATE TABLE credential(value TEXT);
            INSERT INTO credential VALUES ('SECRET_CREDENTIAL_MUST_NEVER_APPEAR');
        """)
        self.session("root", None, "/home/person/PRIVATE_PROJECT_SENTINEL", BASE)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def session(self, sid, parent=None, directory="/home/person/project", stamp=BASE):
        self.db.execute("INSERT INTO session VALUES (?,?,?,?)", (sid, parent, directory, stamp))

    def message(self, mid, sid="root", role="user", stamp=BASE, **extras):
        info = {"role": role, "time": {"created": stamp}, **extras}
        self.db.execute("INSERT INTO message VALUES (?,?,?,?)", (mid, sid, stamp, json.dumps(info)))

    def part(self, pid, mid, kind="text", **extras):
        self.db.execute("INSERT INTO part VALUES (?,?,?,?)", (pid, mid, BASE, json.dumps({"type": kind, **extras})))

    def result(self):
        self.db.commit()
        return analyze(self.path, "UTC")

    def test_automatic_denver_timezone_uses_each_dates_dst_and_calendar_day(self):
        # The same UTC hour is 23:30 the previous day in winter, 00:30 in summer.
        for mid, iso in (("winter", "2026-01-15T06:30:00+00:00"), ("summer", "2026-07-15T06:30:00+00:00")):
            self.message(mid, stamp=int(datetime.fromisoformat(iso).timestamp() * 1000))
            self.part(mid, mid, text="Build a chart.")
        self.db.commit()
        with patch.dict(os.environ, {"TZ": "America/Denver"}):
            report = analyze(self.path)
        self.assertEqual(report["timezone"], "America/Denver")
        self.assertEqual(report["coverage"], {"start": "2026-01-14", "end": "2026-07-15"})
        self.assertEqual(report["rhythm"]["heatmap"][2][23], 1)
        self.assertEqual(report["rhythm"]["heatmap"][2][0], 1)
        self.assertEqual(sum(map(sum, report["rhythm"]["heatmap"])), 2)

    def test_host_timezone_detection_and_explicit_override(self):
        with patch.dict(os.environ, {"TZ": ""}), patch("analyze.Path.resolve", return_value=Path("/private/var/db/timezone/zoneinfo/America/Denver")), patch("analyze.Path.read_text", side_effect=FileNotFoundError):
            self.assertEqual(local_timezone(), "America/Denver")
        with patch.dict(os.environ, {"TZ": "America/Denver"}):
            self.db.commit()
            self.assertEqual(analyze(self.path, "Asia/Tokyo")["timezone"], "Asia/Tokyo")
        with patch.dict(os.environ, {"TZ": "invalid/zone"}), patch("analyze.Path.resolve", return_value=Path("/etc/localtime")), patch("analyze.Path.read_text", return_value="Europe/Paris\n"):
            self.assertEqual(local_timezone(), "Europe/Paris")
        with patch.dict(os.environ, {"TZ": ""}), patch("analyze.Path.resolve", return_value=Path("/etc/localtime")), patch("analyze.Path.read_text", side_effect=FileNotFoundError):
            self.assertEqual(local_timezone(), "UTC")

    def test_root_text_filters_and_copy_dedup_preserve_new_repeated_requests(self):
        self.session("fork", stamp=BASE + 1000)
        self.session("child", "root")
        for mid, sid, stamp in (("u", "root", BASE), ("copy", "fork", BASE), ("again", "root", BASE + 2000)):
            self.message(mid, sid, stamp=stamp)
            self.part(mid, mid, text="<system-reminder>Review everything</system-reminder>Build a small chart.")
        self.message("sub", "child")
        self.part("sub", "sub", text="Why is this broken?")
        self.message("synthetic")
        self.part("synthetic", "synthetic", text="Review a secret plan", synthetic=True)
        self.message("ignored")
        self.part("ignored", "ignored", text="Review something else", ignored=True)
        self.message("reminder")
        self.part("reminder", "reminder", text="<system-reminder>Review and test")
        report = self.result()
        self.assertEqual(report["summary"]["messages"], 2)
        self.assertEqual(report["methods"]["copied_human_messages_removed"], 1)
        signals = {row["id"]: row["count"] for row in report["communication"]["signals"]}
        self.assertEqual(signals["direction"], 2)
        self.assertEqual(signals["review"], 0)

    def test_usage_components_include_children_once_and_ignore_optional_total(self):
        self.session("fork", stamp=BASE + 1000)
        self.session("child", "root", "/home/person/child-project", BASE + 2000)
        tokens = {"input": 10, "output": 2, "reasoning": 3, "cache": {"read": 30, "write": 4}, "total": 999}
        info = {"providerID": "provider", "modelID": "model", "tokens": tokens, "cost": 1,
                "time": {"created": BASE, "completed": BASE + 500}}
        self.message("a", role="assistant", **info)
        self.message("copy", "fork", "assistant", **info)
        self.message("child-a", "child", "assistant", tokens={"input": 5, "output": 1}, cost=0,
                     time={"created": BASE + 3000, "completed": BASE + 3500})
        report = self.result()
        self.assertEqual(report["summary"]["tokens"], 55)
        self.assertEqual(report["summary"]["recorded_cost"], 1)
        self.assertEqual(report["methods"]["copied_receipts_removed"], 1)
        self.assertEqual(report["resources"]["zero_cost_token_receipts"], 1)
        self.assertEqual(sum(row["tokens"] for row in report["projects"]), 55)

    def test_tool_failure_union_retries_rereads_and_copied_calls(self):
        self.session("fork", stamp=BASE + 10000)
        self.message("a", role="assistant", parentID="u")
        self.message("copy-a", "fork", "assistant", parentID="copy-u")
        failure = {"status": "completed", "input": {"command": "test-command"}, "metadata": {"exit": -9},
                   "time": {"start": BASE, "end": BASE + 1000}}
        self.part("fail", "a", "tool", tool="bash", callID="call-1", state=failure)
        self.part("copied", "copy-a", "tool", tool="bash", callID="call-1", state=failure)
        self.part("retry", "a", "tool", tool="bash", callID="call-2", state={**failure, "metadata": {"exit": 0}, "time": {"start": BASE + 2000, "end": BASE + 4000}})
        self.part("tool-error", "a", "tool", tool="bash", callID="call-3", state={**failure, "status": "error", "time": {"start": BASE + 5000, "end": BASE + 6000}})
        for i in range(2):
            self.part(f"read-{i}", "a", "tool", tool="read", callID=f"read-{i}", state={"status": "completed", "input": {"filePath": "same.md"}, "time": {"start": BASE + 7000 + i, "end": BASE + 8000 + i}})
        report = self.result()
        self.assertEqual(report["summary"]["tool_calls"], 5)
        self.assertEqual(report["methods"]["copied_tools_removed"], 1)
        self.assertEqual(report["execution"]["failure_shaped_calls"], 2)
        self.assertEqual(report["execution"]["identical_after_failure"], 1)
        self.assertEqual(report["execution"]["repeated_reads"], 1)
        bash = next(row for row in report["execution"]["tools"] if row["name"] == "bash")
        self.assertEqual(bash["median_seconds"], 1)
        self.assertEqual(bash["p90_seconds"], 1.8)

    def test_new_user_turn_is_not_counted_as_a_retry(self):
        self.message("a", role="assistant", parentID="user-1")
        self.message("b", role="assistant", parentID="user-2", stamp=BASE + 1000)
        for mid, status, timestamp in (("a", "error", BASE), ("b", "completed", BASE + 1000)):
            self.part(mid, mid, "tool", tool="bash", callID=mid, state={"status": status, "input": {"command": "same"}, "time": {"start": timestamp, "end": timestamp + 100}})
        self.assertEqual(self.result()["execution"]["identical_after_failure"], 0)

    def test_readonly_analysis_and_share_exports_do_not_leak_private_material(self):
        self.message("u")
        self.part("u", "u", text="PRIVATE_PROMPT_SENTINEL: build a chart")
        self.message("a", role="assistant", parentID="u")
        self.part("a", "a", "tool", tool="bash", callID="a", state={"status": "completed", "input": {"command": "PRIVATE_COMMAND_SENTINEL"}, "output": "PRIVATE_OUTPUT_SENTINEL", "time": {"start": BASE, "end": BASE + 10}})
        self.db.commit()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        report = analyze(self.path)
        after = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        connection, _ = connect_archive(self.path)
        with self.assertRaises(sqlite3.OperationalError):
            connection.execute("DELETE FROM message")
        connection.close()
        serialized = json.dumps(report)
        for forbidden in ("PRIVATE_PROMPT", "PRIVATE_COMMAND", "PRIVATE_OUTPUT", "SECRET_CREDENTIAL", "/home/person"):
            self.assertNotIn(forbidden, serialized)
        html = render_page(share_report(report))
        self.assertNotIn("PRIVATE_PROJECT_SENTINEL", html)
        self.assertIn("Project 01", html)
        with self.assertRaises(ArchiveError):
            export_report(self.path, report, self.path)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_empty_minimal_schema_and_malformed_records_have_honest_states(self):
        self.db.close()
        self.path.unlink()
        self.db = sqlite3.connect(self.path)
        self.db.executescript("CREATE TABLE session(id TEXT); CREATE TABLE message(id TEXT,session_id TEXT,data TEXT); CREATE TABLE part(id TEXT,message_id TEXT,data TEXT);")
        report = self.result()
        self.assertEqual(report["assessment"]["persona"], "An Early Sketch")
        self.assertEqual(report["assessment"]["communication"], "Still taking shape")
        self.assertEqual(report["summary"]["messages"], 0)
        self.assertIsNone(report["rhythm"]["peak_hour"])
        self.assertEqual(report["projects"], [])
        self.db.execute("INSERT INTO session VALUES ('s')")
        self.db.execute("INSERT INTO message VALUES ('m','s','broken JSON')")
        self.assertEqual(self.result()["methods"]["malformed_or_unlinked_records_skipped"], 1)

    def test_missing_and_unsupported_archives_are_not_created_or_modified(self):
        missing = Path(self.temp.name) / "does-not-exist.db"
        with self.assertRaises(ArchiveError):
            analyze(missing)
        self.assertFalse(missing.exists())
        other = Path(self.temp.name) / "other.db"
        connection = sqlite3.connect(other)
        connection.execute("CREATE TABLE other(id TEXT)")
        connection.close()
        with self.assertRaisesRegex(ArchiveError, "schema is not supported"):
            analyze(other)

    def test_persona_requires_evidence_and_script_data_is_escaped(self):
        for i in range(20):
            self.message(f"u-{i}", stamp=BASE + i * 1000)
            self.part(f"u-{i}", f"u-{i}", text="Build a chart.")
        self.message("a", role="assistant", modelID="</script><script>INJECTION_SENTINEL</script>")
        report = self.result()
        self.assertEqual(report["assessment"]["persona"], "The Builder")
        self.assertEqual(report["assessment"]["communication"], "Concise driver")
        self.assertNotIn("</script><script>INJECTION_SENTINEL", render_page(report))

    def test_one_long_paste_does_not_determine_communication_style(self):
        result = assess({"question": 2, "direction": 19, "review": 0, "continuity": 0, "detail": 1, "continuation": 0}, 20, 50, 0)
        self.assertEqual(result["communication"], "Concise driver")

    def test_local_archive_switch_endpoint_and_recoverable_error(self):
        import threading
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        self.message("u")
        self.part("u", "u", text="Build something useful.")
        initial = self.result()
        server = MirrorServer(("127.0.0.1", 0), initial, "UTC")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            def request(path, from_origin):
                return Request(origin + "/api/analyze", data=json.dumps({"path": str(path)}).encode(), headers={"Content-Type": "application/json", "Origin": from_origin})
            with self.assertRaises(HTTPError) as denied:
                urlopen(request(self.path, "https://unrelated.example"), timeout=5)
            self.assertEqual(denied.exception.code, 403)
            denied.exception.close()
            with self.assertRaises(HTTPError) as missing:
                urlopen(request(self.path.parent / "missing.db", origin), timeout=5)
            self.assertEqual(missing.exception.code, 400)
            missing.exception.close()
            self.assertIs(server.report, initial)
            with urlopen(request(self.path, origin), timeout=5) as response:
                report = json.load(response)
            self.assertEqual(report["summary"]["messages"], 1)
            self.assertNotIn("explorations", report)
            self.assertNotIn("archive_key", report)
            for route in ("/api/atlas", "/api/score", "/api/evidence", "/api/episode"):
                with self.assertRaises(HTTPError) as removed:
                    urlopen(origin + route, timeout=5)
                self.assertEqual(removed.exception.code, 404)
                removed.exception.close()
            with urlopen(origin + "/export", timeout=5) as response:
                html = response.read().decode()
            self.assertNotIn("PRIVATE_PROJECT_SENTINEL", html)
            self.assertIn('"shared": true', html)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_browser_timezone_reanalysis_is_readonly_recoverable_and_frozen_in_exports(self):
        import threading
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        self.message("u")
        self.part("u", "u", text="Build something useful.")
        initial = self.result()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        server = MirrorServer(("127.0.0.1", 0), initial, "UTC", self.path, timezone_auto=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            def request(zone, route="/api/timezone", from_origin=origin):
                payload = {"timezone": zone, "path": str(self.path)}
                return Request(origin + route, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Origin": from_origin})
            with urlopen(request("America/Denver"), timeout=5) as response:
                report = json.load(response)
            self.assertEqual(report["timezone"], "America/Denver")
            self.assertEqual(server.timezone_name, "America/Denver")
            saved = server.report
            for zone in ("Not/A_Zone", "", {"invalid": True}):
                with self.assertRaises(HTTPError) as invalid:
                    urlopen(request(zone), timeout=5)
                self.assertEqual(invalid.exception.code, 400)
                invalid.exception.close()
                self.assertIs(server.report, saved)
                self.assertEqual(server.timezone_name, "America/Denver")
            with self.assertRaises(HTTPError) as denied:
                urlopen(request("Europe/Paris", from_origin="https://unrelated.example"), timeout=5)
            self.assertEqual(denied.exception.code, 403)
            denied.exception.close()
            with urlopen(request("Europe/Paris", "/api/analyze"), timeout=5) as response:
                self.assertEqual(json.load(response)["timezone"], "Europe/Paris")
            with urlopen(origin + "/", timeout=5) as response:
                self.assertIn('"timezoneAuto": true', response.read().decode())
            with urlopen(origin + "/export", timeout=5) as response:
                html = response.read().decode()
            self.assertIn('"timezoneAuto": false', html)
            self.assertIn('"timezone": "Europe/Paris"', html)
            self.assertNotIn("PRIVATE_PROJECT_SENTINEL", html)
            self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_browser_timezone_cannot_override_explicit_launcher_zone(self):
        import threading
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        initial = self.result()
        server = MirrorServer(("127.0.0.1", 0), initial, "America/Denver", self.path)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            def request(route):
                return Request(origin + route, data=json.dumps({"path": str(self.path), "timezone": "Asia/Tokyo"}).encode(), headers={"Content-Type": "application/json", "Origin": origin})
            with urlopen(request("/api/analyze"), timeout=5) as response:
                self.assertEqual(json.load(response)["timezone"], "America/Denver")
            saved = server.report
            with self.assertRaises(HTTPError) as fixed:
                urlopen(request("/api/timezone"), timeout=5)
            self.assertEqual(fixed.exception.code, 400)
            fixed.exception.close()
            self.assertIs(server.report, saved)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
