#!/usr/bin/env python3
"""Run OpenCode Mirror locally. Python 3.10+, no third-party packages."""
import argparse
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse
import webbrowser

from analyze import ArchiveError, VERSION, analyze, local_timezone, share_report

HERE = Path(__file__).resolve().parent


def theme_assets():
    assets = HERE / "assets"
    theme = (assets / "theme.css").read_text(encoding="utf-8")
    fonts = assets / "fonts.css"
    font_css = fonts.read_text(encoding="utf-8") if fonts.exists() else ""
    # Report exports must remain offline.
    if "@import" in font_css or "url(https:" in font_css:
        font_css = ""
    notice = HERE / "FONT_LICENSES.txt"
    if font_css and notice.exists():
        font_css = "/*\n" + notice.read_text(encoding="utf-8") + "\n*/\n" + font_css
    return theme, font_css


def render_page(report=None, timezone_auto=False):
    theme, fonts = theme_assets()
    assets = HERE / "assets"
    template = (assets / "index.html").read_text(encoding="utf-8")
    serialized = json.dumps(report, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    settings = {"timezoneAuto": timezone_auto}
    values = {"theme": theme, "fonts": fonts, "css": (assets / "app.css").read_text(encoding="utf-8"),
              "settings": json.dumps(settings),
              "data": serialized, "js": (assets / "app.js").read_text(encoding="utf-8")}
    for name, value in values.items():
        template = template.replace("{{" + name + "}}", value)
    return template


def export_report(output, report, database=None):
    output = Path(output).expanduser().resolve()
    if database is not None and output == Path(database).expanduser().resolve():
        raise ArchiveError("Choose an HTML output path different from the source database.")
    if not output.parent.is_dir():
        raise ArchiveError("The export's parent directory does not exist.")
    output.write_text(render_page(share_report(report)), encoding="utf-8")


class MirrorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, report, timezone_name, database=None, timezone_auto=False):
        super().__init__(address, MirrorHandler)
        self.report = report
        self.timezone_name = timezone_name
        self.database = database
        self.timezone_auto = timezone_auto
        self.analysis_lock = threading.Lock()


class MirrorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # No request bodies or database paths are written to logs.
        pass

    def send(self, status, content, kind="application/json; charset=utf-8", filename=None):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.send(200, render_page(self.server.report, self.server.timezone_auto), "text/html; charset=utf-8")
        elif path == "/api/report":
            self.send(200, json.dumps(self.server.report, allow_nan=False))
        elif path == "/export" and self.server.report is not None:
            self.send(200, render_page(share_report(self.server.report)), "text/html; charset=utf-8", "opencode-mirror.html")
        elif path == "/favicon.ico":
            self.send(204, "", "image/x-icon")
        else:
            self.send(404, json.dumps({"error": "Page not found."}))

    def do_POST(self):
        route = urlparse(self.path).path
        if route not in ("/api/analyze", "/api/timezone"):
            self.send(404, json.dumps({"error": "Page not found."}))
            return
        expected = f"http://127.0.0.1:{self.server.server_port}"
        if self.headers.get("Origin") != expected or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            self.send(403, json.dumps({"error": "Open the app from its local 127.0.0.1 address."}))
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8192:
                raise ArchiveError("Enter a database path shorter than 8 KB.")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ArchiveError("Enter a database path or timezone.")
            requested_zone = payload.get("timezone")
            if requested_zone is not None and (not isinstance(requested_zone, str) or not requested_zone.strip()):
                raise ArchiveError("Enter a valid IANA timezone.")
            with self.server.analysis_lock:
                if route == "/api/timezone":
                    if not self.server.timezone_auto:
                        raise ArchiveError("The timezone is set by the --timezone launcher option.")
                    if requested_zone is None or self.server.database is None:
                        raise ArchiveError("Open an archive and supply a timezone first.")
                    path = self.server.database
                else:
                    path = payload.get("path")
                    if not isinstance(path, str) or not path.strip():
                        raise ArchiveError("Enter the path to your opencode.db.")
                    path = Path(path.strip()).expanduser().resolve()
                zone = requested_zone.strip() if requested_zone is not None and self.server.timezone_auto else self.server.timezone_name
                report = analyze(path, zone)
                self.server.report = report
                self.server.database = path
                self.server.timezone_name = report["timezone"]
            self.send(200, json.dumps(report, allow_nan=False))
        except (ValueError, OSError) as exc:
            message = str(exc) if isinstance(exc, ArchiveError) else "That archive could not be read. Check the database path."
            self.send(400, json.dumps({"error": message}))


def default_database():
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return root / "opencode/opencode.db"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Path to opencode.db (default: OpenCode's local data directory)")
    parser.add_argument("--timezone", help="Override automatic local time with an IANA zone, e.g. America/Denver")
    parser.add_argument("--port", type=int, default=8787, help="Local web port; default 8787")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open the browser")
    parser.add_argument("--export", type=Path, help="Write an anonymized, offline HTML report and exit")
    parser.add_argument("--version", action="version", version=f"OpenCode Mirror {VERSION}")
    args = parser.parse_args()
    database = args.db or default_database()
    timezone_name = args.timezone or local_timezone()
    try:
        if args.db or database.exists() or args.export:
            print("Reading your archive locally…", flush=True)
        report = analyze(database, timezone_name) if args.db or database.exists() or args.export else None
        if args.export:
            export_report(args.export, report, database)
            print(f"Shared report: {args.export.resolve()}")
            return 0
        if not 0 <= args.port <= 65535:
            parser.error("--port must be between 0 and 65535")
        server = MirrorServer(("127.0.0.1", args.port), report, timezone_name, database if report else None,
                              timezone_auto=args.timezone is None)
    except (ArchiveError, OSError) as exc:
        message = str(exc)
        if isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE:
            message = f"Port {args.port} is already in use. Run again with --port 0 to choose a free port."
        print(f"OpenCode Mirror: {message}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"OpenCode Mirror {VERSION} · {url}", flush=True)
    print(f"Activity timezone: {timezone_name} · {'automatic local time' if args.timezone is None else 'launcher override'}", flush=True)
    print("Local, read-only analysis. Press Ctrl+C to stop.", flush=True)
    if not args.no_open:
        threading.Timer(.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
