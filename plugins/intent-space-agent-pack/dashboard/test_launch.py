"""
Unit tests for the dashboard launcher's auto-discovery logic.

Run from the plugin root:

    python -m unittest plugins.intent-space-agent-pack.dashboard.test_launch

Or directly:

    python plugins/intent-space-agent-pack/dashboard/test_launch.py

The launcher's two interesting behaviors are:

1. Reading a workspace's `.intent-space/state/known-stations.json` and picking
   the right entry (zero-config when there's exactly one, error when there
   are multiple and `--space` wasn't given).
2. Falling back to explicit CLI args when no workspace state is present.

Anything web-server-shaped is left to the smoke test.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

# Allow running this file directly without installing the pack.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import launch  # noqa: E402


def write_workspace(root: Path, stations: list[dict]) -> None:
    state = root / ".intent-space" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "known-stations.json").write_text(json.dumps(stations))


def make_args(**overrides: object) -> argparse.Namespace:
    defaults: dict = {
        "origin": None,
        "space": None,
        "token": None,
        "workspace": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class LoadWorkspaceStationTests(unittest.TestCase):
    def test_returns_none_when_workspace_state_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(launch.load_workspace_station(Path(tmp), None))

    def test_returns_the_only_entry_when_unambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {
                    "endpoint": "https://example.test",
                    "spaceId": "space-only",
                    "stationToken": "tok-1",
                },
            ])
            station = launch.load_workspace_station(root, None)
            assert station is not None
            self.assertEqual(station["spaceId"], "space-only")
            self.assertEqual(station["stationToken"], "tok-1")

    def test_filters_by_space_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {"endpoint": "https://a.test", "spaceId": "space-a", "stationToken": "tok-a"},
                {"endpoint": "https://b.test", "spaceId": "space-b", "stationToken": "tok-b"},
            ])
            station = launch.load_workspace_station(root, "space-b")
            assert station is not None
            self.assertEqual(station["endpoint"], "https://b.test")
            self.assertEqual(station["stationToken"], "tok-b")

    def test_returns_none_and_warns_when_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {"endpoint": "https://a.test", "spaceId": "space-a", "stationToken": "tok-a"},
                {"endpoint": "https://b.test", "spaceId": "space-b", "stationToken": "tok-b"},
            ])
            err = io.StringIO()
            with redirect_stderr(err):
                station = launch.load_workspace_station(root, None)
            self.assertIsNone(station)
            self.assertIn("Multiple stations", err.getvalue())
            self.assertIn("space-a", err.getvalue())
            self.assertIn("space-b", err.getvalue())

    def test_skips_entries_missing_a_station_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {"endpoint": "https://no-token.test", "spaceId": "space-x"},  # incomplete
            ])
            self.assertIsNone(launch.load_workspace_station(root, None))


class ResolveConnectionTests(unittest.TestCase):
    def test_prefers_explicit_cli_args_over_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {"endpoint": "https://workspace.test", "spaceId": "space-from-ws", "stationToken": "tok-ws"},
            ])
            args = make_args(
                origin="https://cli.test/",  # trailing slash should be stripped
                space="space-from-cli",
                token="tok-cli",
                workspace=str(root),
            )
            conn = launch.resolve_connection(args)
            self.assertEqual(conn, {
                "origin": "https://cli.test",
                "spaceId": "space-from-cli",
                "stationToken": "tok-cli",
            })

    def test_zero_config_from_workspace_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root, [
                {"endpoint": "https://example.test/", "spaceId": "space-only", "stationToken": "tok-1"},
            ])
            args = make_args(workspace=str(root))
            conn = launch.resolve_connection(args)
            self.assertEqual(conn["origin"], "https://example.test")
            self.assertEqual(conn["spaceId"], "space-only")
            self.assertEqual(conn["stationToken"], "tok-1")

    def test_exits_when_workspace_missing_and_args_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = make_args(workspace=tmp, space="space-x")  # no token, no origin
            err = io.StringIO()
            with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
                launch.resolve_connection(args)
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("Could not auto-discover", err.getvalue())


class BuildDashboardUrlTests(unittest.TestCase):
    def test_url_encodes_origin_space_and_token_into_hash(self) -> None:
        url = launch.build_dashboard_url("127.0.0.1", 4317, {
            "origin": "https://example.test",
            "spaceId": "space-abc-123",
            "stationToken": "tok+with/special=chars",
        })
        self.assertTrue(url.startswith("http://127.0.0.1:4317/#"))
        self.assertIn("origin=https%3A%2F%2Fexample.test", url)
        self.assertIn("space=space-abc-123", url)
        # tokens with reserved characters must be percent-encoded so the dashboard
        # can split the hash on '&' without mis-parsing.
        self.assertIn("token=tok%2Bwith%2Fspecial%3Dchars", url)


if __name__ == "__main__":
    unittest.main()
