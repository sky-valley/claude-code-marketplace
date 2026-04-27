#!/usr/bin/env python3
"""
Reference dashboard launcher for the intent-space-agent-pack.

Serves dashboard/index.html on a localhost HTTP server and opens the browser
pointed at the bound space, so any HTTP intent space (Spacebase1,
http-reference-station, your own server) gets a zero-config visualization.

Zero-config mode
----------------
If you've already used the SDK in the current directory, your workspace has a
.intent-space/state/known-stations.json with everything we need. Just run:

    python -m launch        # if invoked from the dashboard/ directory
    python launch.py        # otherwise

If multiple stations are remembered, pass --space to pick one:

    python launch.py --space space-abc-123

Manual mode
-----------
If you don't have a workspace yet (or you want to point at someone else's
space), pass everything explicitly:

    python launch.py \\
        --origin https://spacebase1.differ.ac \\
        --space  space-abc-123 \\
        --token  <station_token>

Flags
-----
--port N        Bind to a specific port (default: pick a free one)
--no-open       Print the URL but don't open the browser
--workspace P   Look for .intent-space/state/known-stations.json under P
                (default: current working directory)
"""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional


HERE = Path(__file__).resolve().parent
DASHBOARD_HTML = HERE / "index.html"


def load_workspace_station(workspace: Path, space_filter: Optional[str]) -> Optional[dict]:
    known = workspace / ".intent-space" / "state" / "known-stations.json"
    if not known.exists():
        return None
    try:
        stations = json.loads(known.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(stations, list) or not stations:
        return None
    candidates = [s for s in stations if isinstance(s, dict) and s.get("stationToken")]
    if space_filter is not None:
        candidates = [s for s in candidates if s.get("spaceId") == space_filter]
    if not candidates:
        return None
    if len(candidates) > 1 and space_filter is None:
        sys.stderr.write(
            "Multiple stations found in workspace. Pass --space to pick one:\n"
        )
        for s in candidates:
            sys.stderr.write(
                f"  --space {s.get('spaceId') or '(no spaceId)'} "
                f"({s.get('endpoint')})\n"
            )
        return None
    return candidates[0]


def resolve_connection(args: argparse.Namespace) -> dict:
    if args.origin and args.space and args.token:
        return {"origin": args.origin.rstrip("/"), "spaceId": args.space, "stationToken": args.token}

    workspace = Path(args.workspace).resolve() if args.workspace else Path.cwd()
    station = load_workspace_station(workspace, args.space)
    if station is None:
        sys.stderr.write(
            "Could not auto-discover a station and not all of --origin/--space/--token were provided.\n"
            f"Looked in {workspace / '.intent-space' / 'state' / 'known-stations.json'}\n"
        )
        sys.exit(2)

    origin = (args.origin or station.get("endpoint", "")).rstrip("/")
    space_id = args.space or station.get("spaceId")
    token = args.token or station.get("stationToken")
    if not origin or not space_id or not token:
        sys.stderr.write(
            "Workspace station entry is incomplete. Need origin, spaceId, and stationToken.\n"
            f"Got: origin={origin!r} spaceId={space_id!r} stationToken={'<set>' if token else None}\n"
        )
        sys.exit(2)
    return {"origin": origin, "spaceId": space_id, "stationToken": token}


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Serves only the embedded dashboard HTML; everything else is 404."""

    def do_GET(self) -> None:  # noqa: N802 — http.server convention
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = DASHBOARD_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Quiet the per-request access log; the launcher already prints what
        # matters. Override so the launcher doesn't drown the agent's stdout.
        return


def build_dashboard_url(host: str, port: int, conn: dict) -> str:
    query = urllib.parse.urlencode({
        "origin": conn["origin"],
        "space": conn["spaceId"],
        "token": conn["stationToken"],
    })
    return f"http://{host}:{port}/#{query}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open the intent-space reference dashboard in the browser.",
    )
    parser.add_argument("--origin", help="Station origin (https://...). Defaults to workspace state.")
    parser.add_argument("--space", help="Space ID to observe. Defaults to workspace state.")
    parser.add_argument("--token", help="Station token. Defaults to workspace state.")
    parser.add_argument("--port", type=int, default=0, help="Local port (default: pick a free one).")
    parser.add_argument("--no-open", action="store_true", help="Print the URL without opening the browser.")
    parser.add_argument("--workspace", help="Workspace dir to read .intent-space/ from (default: cwd).")
    args = parser.parse_args()

    if not DASHBOARD_HTML.exists():
        sys.stderr.write(f"Missing dashboard HTML at {DASHBOARD_HTML}\n")
        return 2

    conn = resolve_connection(args)
    host = "127.0.0.1"

    with socketserver.TCPServer((host, args.port), DashboardHandler) as httpd:
        port = httpd.server_address[1]
        url = build_dashboard_url(host, port, conn)
        sys.stdout.write(f"Dashboard:  {url}\n")
        sys.stdout.write(f"Observing:  space={conn['spaceId']} origin={conn['origin']}\n")
        sys.stdout.write("Press Ctrl+C to stop.\n")
        sys.stdout.flush()
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.stdout.write("\nStopped.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
