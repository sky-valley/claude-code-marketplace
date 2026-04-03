#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen

from intent_space_sdk import (
    JsonDict,
    LocalState,
    _frame_from_message,
    _message_from_frame,
    _parse_frames,
    _serialize_frame,
    make_id,
    normalize_http_endpoint,
    now_s,
    sha256_b64url,
)


def build_http_dpop_proof(
    local_state: LocalState,
    *,
    method: str,
    url: str,
    station_token: str,
) -> str:
    return local_state.sign_jwt(
        {"typ": "dpop+jwt", "alg": "RS256", "jwk": local_state.public_jwk()},
        {
            "jti": make_id("dpop"),
            "htm": method.upper(),
            "htu": url,
            "iat": now_s(),
            "ath": sha256_b64url(station_token),
        },
    )


class HttpStationClient:
    def __init__(self, endpoint: str, local_state: LocalState) -> None:
        surface = normalize_http_endpoint(endpoint)
        self.endpoint = surface["origin"]
        self.surface = surface
        self.local_state = local_state
        self.cursors = local_state.load_cursors()
        self.auth: Optional[Dict[str, Any]] = None

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def _authorized_headers(self, method: str, url: str) -> Dict[str, str]:
        if not self.auth:
            raise RuntimeError("client is not authenticated")
        return {
            "authorization": f"DPoP {self.auth['stationToken']}",
            "DPoP": build_http_dpop_proof(
                self.auth["localState"],
                method=method,
                url=url,
                station_token=self.auth["stationToken"],
            ),
        }

    def _post_frame(self, url: str, message: JsonDict) -> JsonDict:
        verb, headers, body = _frame_from_message(message)
        payload = _serialize_frame(verb=verb, headers=headers, body=body)
        request = Request(
            url,
            data=payload,
            headers={
                "content-type": "application/itp",
                **self._authorized_headers("POST", url),
            },
            method="POST",
        )
        with urlopen(request) as response:
            raw = response.read()
        parsed, remainder = _parse_frames(raw)
        if remainder or len(parsed) != 1:
            raise RuntimeError("expected exactly one framed HTTP response")
        reply = _message_from_frame(*parsed[0])
        self.local_state.append_transcript("out", message)
        self.local_state.append_transcript("in", reply)
        return reply

    def authenticate(self, *, sender_id: str, station_token: str, audience: str, local_state: LocalState) -> JsonDict:
        self.auth = {
            "senderId": sender_id,
            "principalId": sender_id,
            "stationToken": station_token,
            "audience": audience,
            "localState": local_state,
            "spaceId": "root",
        }
        scan_result = self.scan_from("root", since=0, persist_cursor=False)
        return {
            "type": "AUTH_RESULT",
            "senderId": sender_id,
            "principalId": sender_id,
            "spaceId": scan_result.get("spaceId", "root"),
        }

    def send_station(self, message: JsonDict) -> None:
        if message.get("type") == "SCAN":
            self._post_frame(self.surface["scan"], message)
            return
        self._post_frame(self.surface["itp"], message)

    def scan(self, space_id: str) -> JsonDict:
        since = self.cursors.get(space_id, 0)
        return self.scan_from(space_id, since=since, persist_cursor=True)

    def scan_from(self, space_id: str, *, since: int, persist_cursor: bool = True) -> JsonDict:
        result = self._post_frame(self.surface["scan"], {"type": "SCAN", "spaceId": space_id, "since": since})
        if result.get("type") == "ERROR":
            raise RuntimeError(str(result.get("message")))
        if result.get("type") != "SCAN_RESULT":
            raise RuntimeError(f"expected SCAN_RESULT, got {result.get('type')}")
        if persist_cursor and isinstance(result.get("latestSeq"), int):
            self.cursors[space_id] = int(result["latestSeq"])
            self.local_state.save_cursors(self.cursors)
        return result

    def post(self, message: JsonDict) -> None:
        result = self._post_frame(self.surface["itp"], message)
        if result.get("type") == "ERROR":
            raise RuntimeError(str(result.get("message")))

    def read_available(self, total_timeout: float = 0.5, *, update_cursors: bool = True) -> List[JsonDict]:
        deadline = time.time() + total_timeout
        messages: List[JsonDict] = []
        spaces: List[str] = []
        for candidate in self.cursors.keys():
            if isinstance(candidate, str) and candidate not in spaces:
                spaces.append(candidate)
        if self.auth and isinstance(self.auth.get("spaceId"), str) and self.auth["spaceId"] not in spaces:
            spaces.insert(0, self.auth["spaceId"])
        if "root" not in spaces:
            spaces.insert(0, "root")

        while time.time() < deadline:
            found_any = False
            for space_id in spaces:
                since = self.cursors.get(space_id, 0)
                result = self.scan_from(space_id, since=since, persist_cursor=update_cursors)
                batch = result.get("messages", [])
                if isinstance(batch, list) and batch:
                    found_any = True
                    messages.extend(batch)
            if found_any:
                break
            time.sleep(0.1)
        return messages

    def wait_for(self, predicate: Callable[[JsonDict], bool], timeout: float = 10.0) -> JsonDict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for message in self.read_available(total_timeout=0.8):
                if predicate(message):
                    return message
        raise TimeoutError("timed out waiting for matching message")

    def stream_space(
        self,
        *,
        space_id: str,
        since: Optional[int] = None,
        timeout: float = 10.0,
        max_events: Optional[int] = None,
    ) -> List[JsonDict]:
        if not self.auth:
            raise RuntimeError("client is not authenticated")
        cursor = self.cursors.get(space_id, 0) if since is None else since
        stream_url = f"{self.surface['stream']}?space={space_id}&since={cursor}"
        request = Request(stream_url, headers=self._authorized_headers("GET", stream_url))
        events: List[JsonDict] = []
        with urlopen(request, timeout=timeout) as response:
            buffer: List[str] = []
            deadline = time.time() + timeout
            while time.time() < deadline:
                line = response.readline().decode("utf-8")
                if not line:
                    break
                stripped = line.rstrip("\n")
                if stripped.startswith("data: "):
                    buffer.append(stripped[6:])
                    continue
                if stripped == "":
                    if buffer:
                        payload = "\n".join(buffer).encode("utf-8")
                        parsed, remainder = _parse_frames(payload)
                        if not remainder and parsed:
                            message = _message_from_frame(*parsed[0])
                            self.local_state.append_transcript("in", message)
                            events.append(message)
                            if max_events is not None and len(events) >= max_events:
                                break
                        buffer = []
                    continue
        return events
