"""Serve the conflation review page with decisions saved to a file on disk.

Run this instead of opening the HTML directly and the review becomes durable
outside any browser: every edit autosaves to a JSON file you can commit, diff,
hand to a colleague, and feed back into ``conflate.py``, whose ``--decisions`` overlay keeps every manual call
on a re-run.

    python utilities/trucks/trucks_2026_update/analysis/review/serve.py

Opened straight from disk instead, the same page still works -- it just falls
back to browser storage and says so in the header, where Export is the only
durable copy.

The server binds to localhost only and serves exactly two paths: the page
itself and the decisions endpoint.  It is a review aid for one person on one
machine, not a shared service, so it has no authentication and should not be
exposed beyond the loopback interface.
"""

import argparse
import json
import os
import tempfile
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from build_page import build, paths

MAX_UPLOAD = 32 * 1024 * 1024  # a decisions payload is far smaller than this


def write_atomically(path: Path, text: str) -> None:
    """Replace a file's contents without leaving a truncated file behind.

    Decisions are the only irreplaceable artefact here -- the page and the
    matches can always be rebuilt -- so a crash mid-write must not destroy
    the previous good copy.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def make_handler(page_path: Path, decisions_path: Path) -> type[BaseHTTPRequestHandler]:
    """Build a handler bound to one page and one decisions file."""

    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "TruckConflationReview/1.0"

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's interface
            path = self.path.split("?", 1)[0]
            if path in {"/", "/index.html"}:
                if not page_path.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"Page not built", "text/plain")
                    return
                self._send(
                    HTTPStatus.OK, page_path.read_bytes(), "text/html; charset=utf-8"
                )
            elif path == "/api/decisions":
                if decisions_path.is_file():
                    saved = json.loads(decisions_path.read_text(encoding="utf-8"))
                else:
                    saved = {"picks": {}, "decisions": {}}
                saved["path"] = decisions_path.name
                self._send(
                    HTTPStatus.OK,
                    json.dumps(saved).encode("utf-8"),
                    "application/json",
                )
            else:
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's interface
            if self.path.split("?", 1)[0] != "/api/decisions":
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_UPLOAD:
                self._send(HTTPStatus.BAD_REQUEST, b"Bad payload size", "text/plain")
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TypeError("payload is not an object")
            except (ValueError, TypeError) as error:
                self._send(
                    HTTPStatus.BAD_REQUEST, f"Bad JSON: {error}".encode(), "text/plain"
                )
                return
            write_atomically(decisions_path, json.dumps(payload, indent=2, sort_keys=True))
            decided = len(payload.get("decisions") or {})
            self._send(
                HTTPStatus.OK,
                json.dumps({"saved": decided, "path": decisions_path.name}).encode("utf-8"),
                "application/json",
            )

        def log_message(self, fmt: str, *args) -> None:
            """Keep the console to saves, not every asset fetch."""
            if self.command == "POST":
                print(f"  saved -> {decisions_path.name}")

    return ReviewHandler


def serve(page: Path, decisions: Path, port: int, open_browser: bool) -> None:
    """Run the review server until interrupted.

    A busy port is reported rather than worked around: silently moving to
    another one invites talking to a stale server still holding the old port,
    which is confusing precisely when the page looks wrong.
    """
    if not page.is_file():
        msg = f"No review page at {page}; build it before serving"
        raise SystemExit(msg)
    handler = make_handler(page, decisions)

    # http.server defaults allow_reuse_address on, which on Windows maps to
    # SO_REUSEADDR and lets a second server bind a port another process is
    # already listening on. Requests then reach either one, so a stale reviewer
    # can answer with old data and an old decisions file while the new one looks
    # broken. Refuse the bind instead.
    class ExclusiveServer(ThreadingHTTPServer):
        allow_reuse_address = False

    try:
        server = ExclusiveServer(("127.0.0.1", port), handler)
    except OSError as error:
        msg = (
            f"Cannot bind 127.0.0.1:{port} ({error.strerror or error}).\n"
            f"Something is already listening there -- most likely an earlier "
            f"reviewer still running. Stop it, or pass --port 0 for a free port."
        )
        raise SystemExit(msg) from error
    with server as httpd:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/"
        # Flushed because serve_forever blocks: without this the banner sits in
        # the buffer whenever output is redirected to a file.
        print(f"review page : {page}", flush=True)
        print(f"decisions   : {decisions}", flush=True)
        print(f"serving     : {url}   (Ctrl+C to stop)", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped; decisions are on disk")


def main() -> None:
    """Parse arguments, build the page if needed, and start the review server."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conflation", type=Path, default=paths.OUT)
    parser.add_argument("--network", type=Path, default=paths.NETWORK)
    parser.add_argument("--page", type=Path, default=None)
    parser.add_argument("--decisions", type=Path, default=None)
    parser.add_argument("--port", type=int, default=8765, help="0 picks a free port")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--rebuild", action="store_true", help="rebuild the page even if current")
    args = parser.parse_args()

    conflation = args.conflation.resolve()
    page = (args.page or conflation / "review.html").resolve()
    decisions = (args.decisions or conflation / "decisions.json").resolve()
    payload = conflation / "review.json"
    if not payload.is_file():
        msg = f"No conflation output at {payload}; run conflate.py first"
        raise SystemExit(msg)

    # Build the page here rather than making it a separate command to remember.
    # Stale is worse than slow: a page older than the conflation would show
    # matches that no longer exist.
    stale = not page.is_file() or page.stat().st_mtime < payload.stat().st_mtime
    if args.rebuild or stale:
        why = "rebuilding" if page.is_file() else "building"
        print(f"{why} review page from {payload.name}", flush=True)
        build(conflation, args.network.resolve(), page)

    serve(page, decisions, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
