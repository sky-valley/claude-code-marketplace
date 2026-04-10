#!/usr/bin/env python3
"""
Intent Space SDK

Shared protocol helpers for intent-space agent mechanics.

This module is intentionally transport-neutral. It holds:
- framed verb-header-body helpers
- local identity and artifact persistence
- Welcome Mat discovery and signup helpers
- shared proof and JWT material helpers

Transport-specific live participation lives in:
- `tcp_station_client.py`
- `http_station_client.py`
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

JsonDict = Dict[str, Any]
PROOF_TYP = "itp-pop+jwt"
STATION_TOKEN_TYP = "itp+jwt"
HEADER_TERMINATOR = b"\n\n"
ITP_SIGNATURE_HEADER = "itp-sig"
ITP_SIGNATURE_VERSION = "v1"


def compact_json(payload: JsonDict) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _with_optional(headers: Dict[str, Optional[str]]) -> Dict[str, str]:
    return {key: value for key, value in headers.items() if value is not None}


def _validate_verb(verb: str) -> None:
    if not verb or any(not (ch.isupper() or ch == "_") for ch in verb):
        raise ValueError(f"Invalid verb line: {verb}")


def _validate_header_name(name: str) -> None:
    if not name or any(not (ch.islower() or ch == "-") for ch in name):
        raise ValueError(f"Invalid header name: {name}")


def _validate_header_value(name: str, value: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"Invalid header value for {name}")


def _assert_signature_version(headers: Dict[str, str]) -> None:
    version = headers.get(ITP_SIGNATURE_HEADER)
    if version is not None and version != ITP_SIGNATURE_VERSION:
        raise ValueError(f"Unsupported {ITP_SIGNATURE_HEADER} value: {version}")
    if "proof" in headers and version != ITP_SIGNATURE_VERSION:
        raise ValueError(f"Signed frame requires {ITP_SIGNATURE_HEADER}: {ITP_SIGNATURE_VERSION}")


def _validate_headers(headers: Dict[str, str]) -> None:
    _assert_signature_version(headers)
    for name, value in headers.items():
        _validate_header_name(name)
        _validate_header_value(name, value)


def _serialize_frame(*, verb: str, headers: Dict[str, str], body: bytes) -> bytes:
    _validate_verb(verb)
    _validate_headers(headers)
    header_lines = [verb]
    framed_headers = dict(headers)
    framed_headers["body-length"] = str(len(body))
    for name, value in framed_headers.items():
        header_lines.append(f"{name}: {value}")
    header_blob = ("\n".join(header_lines) + "\n\n").encode("utf-8")
    return header_blob + body


def _parse_frames(buffer: bytes) -> tuple[List[tuple[str, Dict[str, str], bytes]], bytes]:
    messages: List[tuple[str, Dict[str, str], bytes]] = []
    offset = 0
    while offset < len(buffer):
        header_end = buffer.find(HEADER_TERMINATOR, offset)
        if header_end == -1:
            break
        header_blob = buffer[offset:header_end].decode("utf-8")
        lines = header_blob.split("\n")
        verb = lines[0].strip()
        if not verb:
            raise ValueError("Missing verb line")
        _validate_verb(verb)
        headers: Dict[str, str] = {}
        for raw_line in lines[1:]:
            if not raw_line:
                raise ValueError("Unexpected empty header line")
            if ": " not in raw_line:
                raise ValueError(f"Malformed header line: {raw_line}")
            name, value = raw_line.split(": ", 1)
            _validate_header_name(name)
            _validate_header_value(name, value)
            if name in headers:
                raise ValueError(f"Duplicate header: {name}")
            headers[name] = value
        _assert_signature_version(headers)
        body_length_raw = headers.get("body-length")
        if body_length_raw is None:
            raise ValueError("Missing body-length header")
        if not body_length_raw.isdigit():
            raise ValueError("body-length must be a decimal byte count")
        body_length = int(body_length_raw)
        body_start = header_end + len(HEADER_TERMINATOR)
        body_end = body_start + body_length
        if body_end > len(buffer):
            break
        messages.append((verb, headers, buffer[body_start:body_end]))
        offset = body_end
    return messages, buffer[offset:]


def _frame_from_message(message: JsonDict) -> tuple[str, Dict[str, str], bytes]:
    message_type = str(message.get("type", ""))
    if message_type == "AUTH":
        return (
            "AUTH",
            {
                "station-token": str(message.get("stationToken", "")),
                ITP_SIGNATURE_HEADER: ITP_SIGNATURE_VERSION,
                "proof": str(message.get("proof", "")),
            },
            b"",
        )
    if message_type == "SCAN":
        return (
            "SCAN",
            _with_optional(
                {
                    "space": str(message.get("spaceId", "")),
                    "since": str(message.get("since", 0)),
                    ITP_SIGNATURE_HEADER: ITP_SIGNATURE_VERSION if "proof" in message else None,
                    "proof": str(message["proof"]) if "proof" in message else None,
                }
            ),
            b"",
        )
    if message_type == "SCAN_RESULT":
        body = json.dumps(message.get("messages", []), separators=(",", ":")).encode("utf-8")
        return (
            "SCAN_RESULT",
            {
                "space": str(message.get("spaceId", "")),
                "latest-seq": str(message.get("latestSeq", 0)),
                "payload-hint": "application/json",
            },
            body,
        )
    if message_type == "AUTH_RESULT":
        return (
            "AUTH_RESULT",
            _with_optional(
                {
                    "sender": str(message.get("senderId", "")),
                    "principal": str(message.get("principalId", "")),
                    "space": str(message["spaceId"]) if "spaceId" in message else None,
                    "tutorial-space": str(message["tutorialSpaceId"]) if "tutorialSpaceId" in message else None,
                    "ritual-greeting": str(message["ritualGreeting"]) if "ritualGreeting" in message else None,
                }
            ),
            b"",
        )
    if message_type == "ERROR":
        return (
            "ERROR",
            {"payload-hint": "text/plain"},
            str(message.get("message", "")).encode("utf-8"),
        )

    body = json.dumps(message.get("payload", {}), separators=(",", ":")).encode("utf-8")
    headers = _with_optional(
        {
            "sender": str(message.get("senderId", "")),
            "parent": str(message["parentId"]) if "parentId" in message else None,
            "intent": str(message["intentId"]) if "intentId" in message else None,
            "promise": str(message["promiseId"]) if "promiseId" in message else None,
            "timestamp": str(message.get("timestamp", "")),
            ITP_SIGNATURE_HEADER: ITP_SIGNATURE_VERSION if "proof" in message else None,
            "proof": str(message["proof"]) if "proof" in message else None,
            "seq": str(message["seq"]) if "seq" in message else None,
            "payload-hint": "application/json",
        }
    )
    return message_type, headers, body


def _message_from_frame(verb: str, headers: Dict[str, str], body: bytes) -> JsonDict:
    if verb == "AUTH":
        return {
            "type": "AUTH",
            "stationToken": headers["station-token"],
            "proof": headers["proof"],
        }
    if verb == "SCAN":
        message: JsonDict = {
            "type": "SCAN",
            "spaceId": headers["space"],
            "since": int(headers.get("since", "0")),
        }
        if "proof" in headers:
            message["proof"] = headers["proof"]
        return message
    if verb == "SCAN_RESULT":
        return {
            "type": "SCAN_RESULT",
            "spaceId": headers["space"],
            "latestSeq": int(headers["latest-seq"]),
            "messages": json.loads(body.decode("utf-8")),
        }
    if verb == "AUTH_RESULT":
        message = {
            "type": "AUTH_RESULT",
            "senderId": headers["sender"],
            "principalId": headers["principal"],
        }
        if "space" in headers:
            message["spaceId"] = headers["space"]
        if "tutorial-space" in headers:
            message["tutorialSpaceId"] = headers["tutorial-space"]
        if "ritual-greeting" in headers:
            message["ritualGreeting"] = headers["ritual-greeting"]
        return message
    if verb == "ERROR":
        return {
            "type": "ERROR",
            "message": body.decode("utf-8"),
        }

    message = {
        "type": verb,
        "senderId": headers["sender"],
        "timestamp": int(headers["timestamp"]),
        "payload": json.loads(body.decode("utf-8")),
    }
    if "parent" in headers:
        message["parentId"] = headers["parent"]
    if "intent" in headers:
        message["intentId"] = headers["intent"]
    if "promise" in headers:
        message["promiseId"] = headers["promise"]
    if "proof" in headers:
        message["proof"] = headers["proof"]
    if "seq" in headers:
        message["seq"] = int(headers["seq"])
    return message


def canonical_request_bytes(value: JsonDict) -> bytes:
    verb, headers, body = _frame_from_message(value)
    return canonical_proof_bytes(verb=verb, headers=headers, body=body)


def canonical_proof_bytes(*, verb: str, headers: Dict[str, str], body: bytes) -> bytes:
    _validate_verb(verb)
    canonical_headers = dict(headers)
    canonical_headers.pop("proof", None)
    canonical_headers.pop("body-length", None)
    canonical_headers[ITP_SIGNATURE_HEADER] = ITP_SIGNATURE_VERSION
    _validate_headers(canonical_headers)
    header_lines = [verb]
    for name in sorted(canonical_headers):
        header_lines.append(f"{name}: {canonical_headers[name]}")
    header_lines.append(f"body-length: {len(body)}")
    header_blob = ("\n".join(header_lines) + "\n\n").encode("utf-8")
    return header_blob + body


def now_ms() -> int:
    return int(time.time() * 1000)


def now_s() -> int:
    return int(time.time())


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def endpoint_scheme(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme:
        raise ValueError(f"Endpoint is missing a scheme: {endpoint}")
    return parsed.scheme


def parse_tcp_endpoint(endpoint: str) -> tuple[str, int]:
    parsed = urlparse(endpoint)
    if parsed.scheme != "tcp":
        raise ValueError("TCP client requires tcp://host:port")
    if not parsed.hostname or not parsed.port:
        raise ValueError("Endpoint must include host and port, e.g. tcp://127.0.0.1:4000")
    return parsed.hostname, parsed.port


def normalize_http_endpoint(endpoint: str) -> Dict[str, str]:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("HTTP endpoint must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("HTTP endpoint must include host")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")
    base_path = path
    for suffix in ("/itp", "/scan", "/stream"):
        if base_path.endswith(suffix):
            base_path = base_path[: -len(suffix)]
            break
    if not base_path:
        base_path = ""
    base_url = f"{origin}{base_path}/"
    if path.endswith("/itp"):
        return {"origin": origin, "itp": endpoint, "scan": urljoin(base_url, "scan"), "stream": urljoin(base_url, "stream")}
    if path.endswith("/scan"):
        return {"origin": origin, "itp": urljoin(base_url, "itp"), "scan": endpoint, "stream": urljoin(base_url, "stream")}
    if path.endswith("/stream"):
        return {"origin": origin, "itp": urljoin(base_url, "itp"), "scan": urljoin(base_url, "scan"), "stream": endpoint}
    return {
        "origin": origin,
        "itp": urljoin(base_url, "itp"),
        "scan": urljoin(base_url, "scan"),
        "stream": urljoin(base_url, "stream"),
    }


def run(cmd: List[str], stdin: Optional[bytes] = None) -> bytes:
    result = subprocess.run(cmd, input=stdin, capture_output=True, check=True)
    return result.stdout


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def sha256_b64url(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return b64url_encode(hashlib.sha256(value).digest())


def fetch_text(url: str, headers: Optional[Dict[str, str]] = None) -> str:
    request = Request(url, headers=headers or {})
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def fetch_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[JsonDict] = None,
) -> JsonDict:
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"content-type": "application/json", **(headers or {})}
    request = Request(url, data=encoded, headers=request_headers, method=method)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_jwt(token: str) -> tuple[JsonDict, JsonDict, bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("JWT must have exactly three parts")
    header_raw, payload_raw, signature_raw = parts
    return (
        json.loads(b64url_decode(header_raw)),
        json.loads(b64url_decode(payload_raw)),
        f"{header_raw}.{payload_raw}".encode("utf-8"),
        b64url_decode(signature_raw),
    )


class LocalState:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.identity_dir = root / ".intent-space" / "identity"
        self.state_dir = root / ".intent-space" / "state"
        self.config_dir = root / ".intent-space" / "config"
        self.private_key = self.identity_dir / "station-private-key.pem"
        self.public_key = self.identity_dir / "station-public-key.pem"
        self.fingerprint = self.identity_dir / "station-fingerprint.txt"
        self.config = self.config_dir / "station.json"
        self.cursors = self.state_dir / "cursors.json"
        self.transcript = self.state_dir / "tutorial-transcript.jsonl"
        self.welcome = self.state_dir / "welcome-mat.json"
        self.enrollment = self.state_dir / "station-enrollment.json"
        self.known_stations = self.state_dir / "known-stations.json"

    def ensure_dirs(self) -> None:
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_cursors(self) -> Dict[str, int]:
        if not self.cursors.exists():
            return {}
        return json.loads(self.cursors.read_text())

    def save_cursors(self, cursors: Dict[str, int]) -> None:
        self.cursors.write_text(json.dumps(cursors, indent=2) + "\n")

    def load_known_stations(self) -> List[JsonDict]:
        if not self.known_stations.exists():
            return []
        return json.loads(self.known_stations.read_text())

    def save_known_stations(self, stations: List[JsonDict]) -> None:
        self.known_stations.write_text(json.dumps(stations, indent=2) + "\n")

    def remember_station(
        self,
        *,
        endpoint: str,
        audience: Optional[str] = None,
        station_token: Optional[str] = None,
        handle: Optional[str] = None,
        principal_id: Optional[str] = None,
        source: str,
        space_id: Optional[str] = None,
    ) -> JsonDict:
        self.ensure_dirs()
        stations = self.load_known_stations()
        entry: JsonDict = {
            "endpoint": endpoint,
            "source": source,
            "lastSeenAt": now_ms(),
        }
        if audience is not None:
            entry["audience"] = audience
        if station_token is not None:
            entry["stationToken"] = station_token
        if handle is not None:
            entry["handle"] = handle
        if principal_id is not None:
            entry["principalId"] = principal_id
        if space_id is not None:
            entry["spaceId"] = space_id

        updated = False
        for index, existing in enumerate(stations):
            if existing.get("endpoint") == endpoint:
                merged = dict(existing)
                merged.update(entry)
                stations[index] = merged
                entry = merged
                updated = True
                break
        if not updated:
            stations.append(entry)
        self.save_known_stations(stations)
        return entry

    def append_transcript(self, direction: str, message: JsonDict) -> None:
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(compact_json({"direction": direction, "message": message}) + "\n")

    def save_json_artifact(self, filename: str, payload: JsonDict) -> None:
        self.ensure_dirs()
        (self.state_dir / filename).write_text(json.dumps(payload, indent=2) + "\n")

    def ensure_identity(self, endpoint: str, agent_name: str) -> tuple[str, str]:
        self.ensure_dirs()
        if not self.private_key.exists():
            run(["openssl", "genrsa", "-out", str(self.private_key), "4096"])
        if not self.public_key.exists():
            public_key_pem = run(["openssl", "rsa", "-in", str(self.private_key), "-pubout"]).decode("utf-8")
            self.public_key.write_text(public_key_pem)

        public_key_pem = self.public_key.read_text()
        fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(public_key_pem.encode("utf-8")).digest()).decode("ascii")
        self.fingerprint.write_text(fingerprint + "\n")

        self.config.write_text(
            json.dumps(
                {
                    "endpoint": endpoint,
                    "publicKey": str(self.public_key.relative_to(self.root)),
                    "privateKey": str(self.private_key.relative_to(self.root)),
                    "fingerprint": fingerprint,
                    "agentName": agent_name,
                },
                indent=2,
            ) + "\n"
        )
        return public_key_pem, fingerprint

    def save_config_endpoint(self, endpoint: str, agent_name: str) -> None:
        self.ensure_identity(endpoint, agent_name)

    def public_jwk(self) -> JsonDict:
        text = run(["openssl", "rsa", "-pubin", "-in", str(self.public_key), "-text", "-noout"]).decode("utf-8")
        lines = text.splitlines()
        modulus_lines: List[str] = []
        exponent = 65537
        capture_modulus = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Modulus:"):
                capture_modulus = True
                continue
            if capture_modulus:
                if stripped.startswith("Exponent:"):
                    capture_modulus = False
                    exponent = int(stripped.split()[1])
                    continue
                modulus_lines.append(stripped.replace(":", ""))
        modulus_hex = "".join(modulus_lines)
        modulus_hex = modulus_hex[2:] if modulus_hex.startswith("00") else modulus_hex
        modulus_bytes = bytes.fromhex(modulus_hex)
        exponent_bytes = exponent.to_bytes((exponent.bit_length() + 7) // 8, "big")
        return {"kty": "RSA", "n": b64url_encode(modulus_bytes), "e": b64url_encode(exponent_bytes)}

    def jwk_thumbprint(self) -> str:
        jwk = self.public_jwk()
        canonical = json.dumps({"e": jwk["e"], "kty": "RSA", "n": jwk["n"]}, separators=(",", ":"))
        return sha256_b64url(canonical)

    def sign_rs256(self, raw_bytes: bytes) -> bytes:
        return run(["openssl", "dgst", "-sha256", "-sign", str(self.private_key)], stdin=raw_bytes)

    def sign_challenge(self, challenge: str) -> str:
        return base64.b64encode(self.sign_rs256(challenge.encode("utf-8"))).decode("ascii")

    def sign_detached_b64url(self, raw_text: str) -> str:
        return b64url_encode(self.sign_rs256(raw_text.encode("utf-8")))

    def sign_jwt(self, header: JsonDict, payload: JsonDict) -> str:
        header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = self.sign_rs256(signing_input)
        return f"{header_b64}.{payload_b64}.{b64url_encode(signature)}"

    def save_welcome(self, payload: JsonDict) -> None:
        self.ensure_dirs()
        self.welcome.write_text(json.dumps(payload, indent=2) + "\n")

    def save_enrollment(self, payload: JsonDict) -> None:
        self.ensure_dirs()
        self.enrollment.write_text(json.dumps(payload, indent=2) + "\n")

    def load_enrollment(self) -> Optional[JsonDict]:
        if not self.enrollment.exists():
            return None
        return json.loads(self.enrollment.read_text())


def parse_welcome_mat(markdown: str) -> JsonDict:
    endpoints: Dict[str, str] = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("- terms:"):
            endpoints["terms"] = line.split(": ", 1)[1].replace("GET ", "")
        elif line.startswith("- signup:"):
            endpoints["signup"] = line.split(": ", 1)[1].replace("POST ", "")
        elif line.startswith("- station:"):
            endpoints["station"] = line.split(": ", 1)[1]
        elif line.startswith("- itp:"):
            endpoints["itp"] = line.split(": ", 1)[1].replace("POST ", "")
        elif line.startswith("- scan:"):
            endpoints["scan"] = line.split(": ", 1)[1].replace("POST ", "")
        elif line.startswith("- stream:"):
            endpoints["stream"] = line.split(": ", 1)[1].replace("GET ", "")
    return {"markdown": markdown, "endpoints": endpoints}


def build_welcome_mat_access_token(
    local_state: LocalState,
    *,
    service_origin: str,
    tos_text: str,
) -> str:
    return local_state.sign_jwt(
        {"typ": "wm+jwt", "alg": "RS256"},
        {
            "jti": make_id("wm"),
            "tos_hash": sha256_b64url(tos_text),
            "aud": service_origin,
            "cnf": {"jkt": local_state.jwk_thumbprint()},
            "iat": now_s(),
        },
    )


def build_dpop_signup_proof(local_state: LocalState, *, signup_url: str) -> str:
    return local_state.sign_jwt(
        {"typ": "dpop+jwt", "alg": "RS256", "jwk": local_state.public_jwk()},
        {
            "jti": make_id("dpop"),
            "htm": "POST",
            "htu": signup_url,
            "iat": now_s(),
        },
    )


def signup_station(
    local_state: LocalState,
    *,
    service_url: str,
    handle: str,
) -> JsonDict:
    local_state.ensure_dirs()
    welcome_url = urljoin(service_url.rstrip("/") + "/", ".well-known/welcome.md")
    welcome_markdown = fetch_text(welcome_url)
    welcome = parse_welcome_mat(welcome_markdown)
    local_state.save_welcome(welcome)

    endpoints = welcome["endpoints"]
    terms_url = endpoints["terms"]
    signup_url = endpoints["signup"]
    if not isinstance(terms_url, str) or not isinstance(signup_url, str):
        raise RuntimeError("welcome.md did not expose terms and signup endpoints")

    tos_text = fetch_text(terms_url)
    service_origin = f"{urlparse(service_url).scheme}://{urlparse(service_url).netloc}"
    access_token = build_welcome_mat_access_token(
        local_state,
        service_origin=service_origin,
        tos_text=tos_text,
    )
    signup_response = fetch_json(
        signup_url,
        method="POST",
        headers={"DPoP": build_dpop_signup_proof(local_state, signup_url=signup_url)},
        body={
            "tos_signature": local_state.sign_detached_b64url(tos_text),
            "access_token": access_token,
            "handle": handle,
        },
    )

    station_endpoint = signup_response.get("station_endpoint")
    if not isinstance(station_endpoint, str):
        station_endpoint = endpoints.get("station")
    if not isinstance(station_endpoint, str):
        itp_endpoint = signup_response.get("itp_endpoint")
        if isinstance(itp_endpoint, str):
            station_endpoint = itp_endpoint
    if not isinstance(station_endpoint, str):
        station_endpoint = endpoints.get("itp")
    if not isinstance(station_endpoint, str):
        raise RuntimeError("signup response did not expose a live station endpoint")

    signup_response["station_endpoint"] = station_endpoint
    local_state.save_enrollment(signup_response)
    local_state.remember_station(
        endpoint=station_endpoint,
        audience=signup_response.get("station_audience") if isinstance(signup_response.get("station_audience"), str) else None,
        station_token=signup_response.get("station_token") if isinstance(signup_response.get("station_token"), str) else None,
        handle=signup_response.get("handle") if isinstance(signup_response.get("handle"), str) else handle,
        principal_id=signup_response.get("principal_id") if isinstance(signup_response.get("principal_id"), str) else None,
        source="signup",
        space_id=signup_response.get("commons_space_id") if isinstance(signup_response.get("commons_space_id"), str) else None,
    )
    return signup_response
