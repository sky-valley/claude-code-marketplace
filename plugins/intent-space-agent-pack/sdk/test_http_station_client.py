#!/usr/bin/env python3
from __future__ import annotations

import unittest

from http_station_client import HttpStationClient


class FakeLocalState:
    def __init__(self, enrollment: dict[str, str] | None = None) -> None:
        self._enrollment = enrollment
        self.saved_cursors = None
        self.transcript: list[tuple[str, object]] = []

    def load_cursors(self) -> dict[str, int]:
        return {}

    def save_cursors(self, cursors: dict[str, int]) -> None:
        self.saved_cursors = dict(cursors)

    def load_enrollment(self) -> dict[str, str] | None:
        return self._enrollment

    def append_transcript(self, direction: str, payload: object) -> None:
        self.transcript.append((direction, payload))


class RecordingHttpStationClient(HttpStationClient):
    def __init__(self, endpoint: str, local_state: FakeLocalState) -> None:
        super().__init__(endpoint, local_state)  # type: ignore[arg-type]
        self.scanned_space_ids: list[str] = []

    def scan_from(self, space_id: str, *, since: int, persist_cursor: bool = True):  # type: ignore[override]
        self.scanned_space_ids.append(space_id)
        return {
            "type": "SCAN_RESULT",
            "spaceId": space_id,
            "messages": [],
            "latestSeq": 0,
        }


class HttpStationClientAuthenticateTests(unittest.TestCase):
    def test_authenticate_prefers_target_shared_space_over_stale_enrollment_space(self) -> None:
        local_state = FakeLocalState({
            "space_id": "space-home",
            "station_endpoint": "http://127.0.0.1:8814/spaces/space-home/itp",
        })
        client = RecordingHttpStationClient(
            "http://127.0.0.1:8814/spaces/space-shared/itp",
            local_state,
        )

        result = client.authenticate(
            sender_id="prn-agent",
            station_token="tok-shared",
            audience="intent-space://spacebase1/space/space-shared",
            local_state=local_state,  # type: ignore[arg-type]
        )

        self.assertEqual(client.scanned_space_ids, ["space-shared"])
        self.assertEqual(result["spaceId"], "space-shared")
        self.assertIsNotNone(client.auth)
        self.assertEqual(client.auth["spaceId"], "space-shared")  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
