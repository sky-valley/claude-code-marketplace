#!/usr/bin/env python3
from __future__ import annotations

import socket
import time
from typing import Any, Callable, Dict, List, Optional

from intent_space_sdk import (
    JsonDict,
    LocalState,
    PROOF_TYP,
    _frame_from_message,
    _message_from_frame,
    _parse_frames,
    _serialize_frame,
    canonical_request_bytes,
    make_id,
    now_s,
    parse_tcp_endpoint,
    sha256_b64url,
)


def build_station_proof(
    local_state: LocalState,
    *,
    sender_id: str,
    station_token: str,
    audience: str,
    action: str,
    request: JsonDict,
) -> str:
    return local_state.sign_jwt(
        {"typ": PROOF_TYP, "alg": "RS256", "jwk": local_state.public_jwk()},
        {
            "jti": make_id("itp-proof"),
            "sub": sender_id,
            "aud": audience,
            "iat": now_s(),
            "ath": sha256_b64url(station_token),
            "action": action,
            "req_hash": sha256_b64url(canonical_request_bytes(request)),
        },
    )


class TcpStationClient:
    def __init__(self, endpoint: str, local_state: LocalState) -> None:
        host, port = parse_tcp_endpoint(endpoint)
        self.endpoint = endpoint
        self.host = host
        self.port = port
        self.local_state = local_state
        self.sock: Optional[socket.socket] = None
        self.buffer = b""
        self.cursors = local_state.load_cursors()
        self.auth: Optional[Dict[str, Any]] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.settimeout(0.5)

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def send(self, message: JsonDict) -> None:
        if self.sock is None:
            raise RuntimeError("client is not connected")
        verb, headers, body = _frame_from_message(message)
        self.sock.sendall(_serialize_frame(verb=verb, headers=headers, body=body))
        self.local_state.append_transcript("out", message)

    def read_available(self, total_timeout: float = 0.5, *, update_cursors: bool = True) -> List[JsonDict]:
        if self.sock is None:
            raise RuntimeError("client is not connected")
        deadline = time.time() + total_timeout
        messages: List[JsonDict] = []
        while time.time() < deadline:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                time.sleep(0.05)
                continue
            if not chunk:
                break
            self.buffer += chunk
            parsed, self.buffer = _parse_frames(self.buffer)
            for verb, headers, body in parsed:
                message = _message_from_frame(verb, headers, body)
                self.local_state.append_transcript("in", message)
                if update_cursors and message.get("type") == "SCAN_RESULT":
                    latest_seq = message.get("latestSeq")
                    space_id = message.get("spaceId")
                    if isinstance(space_id, str) and isinstance(latest_seq, int):
                        self.cursors[space_id] = latest_seq
                        self.local_state.save_cursors(self.cursors)
                messages.append(message)
        return messages

    def authenticate(self, *, sender_id: str, station_token: str, audience: str, local_state: LocalState) -> JsonDict:
        self.auth = {
            "senderId": sender_id,
            "principalId": sender_id,
            "stationToken": station_token,
            "audience": audience,
            "localState": local_state,
        }
        request = {"type": "AUTH"}
        self.send(
            {
                "type": "AUTH",
                "stationToken": station_token,
                "proof": build_station_proof(
                    local_state,
                    sender_id=sender_id,
                    station_token=station_token,
                    audience=audience,
                    action="AUTH",
                    request={**request, "stationToken": station_token},
                ),
            }
        )
        deadline = time.time() + 5.0
        while time.time() < deadline:
            for message in self.read_available(0.8):
                if message.get("type") == "AUTH_RESULT":
                    self.auth["principalId"] = message.get("principalId", sender_id)
                    return message
                if message.get("type") == "ERROR":
                    raise RuntimeError(str(message.get("message")))
        raise TimeoutError("timed out waiting for AUTH_RESULT")

    def send_station(self, message: JsonDict) -> None:
        if not self.auth:
            self.send(message)
            return
        request = dict(message)
        request["proof"] = build_station_proof(
            self.auth["localState"],
            sender_id=self.auth["senderId"],
            station_token=self.auth["stationToken"],
            audience=self.auth["audience"],
            action="SCAN" if request.get("type") == "SCAN" else str(request.get("type")),
            request={k: v for k, v in request.items() if k != "proof"},
        )
        self.send(request)

    def scan(self, space_id: str) -> JsonDict:
        since = self.cursors.get(space_id, 0)
        return self.scan_from(space_id, since=since, persist_cursor=True)

    def scan_from(self, space_id: str, *, since: int, persist_cursor: bool = True) -> JsonDict:
        self.send_station({"type": "SCAN", "spaceId": space_id, "since": since})
        deadline = time.time() + 4.0
        while time.time() < deadline:
            for message in self.read_available(0.8, update_cursors=persist_cursor):
                if message.get("type") == "SCAN_RESULT" and message.get("spaceId") == space_id:
                    return message
                if message.get("type") == "ERROR":
                    raise RuntimeError(str(message.get("message")))
        raise TimeoutError(f"timed out waiting for SCAN_RESULT for {space_id}")

    def post(self, message: JsonDict) -> None:
        self.send_station(message)

    def wait_for(self, predicate: Callable[[JsonDict], bool], timeout: float = 10.0) -> JsonDict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for message in self.read_available(0.8):
                if predicate(message):
                    return message
        raise TimeoutError("timed out waiting for matching message")
