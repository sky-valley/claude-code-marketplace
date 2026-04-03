#!/usr/bin/env python3
"""
Compatibility shim.

Prefer:
- `tcp_space_tools.py` for pure TCP/ITP participation
- `http_space_tools.py` for Welcome Mat + HTTP participation

This file remains as a small transport-selecting front door for callers that
still want one import path.
"""

from __future__ import annotations

from intent_space_sdk import endpoint_scheme
from tcp_space_tools import *  # noqa: F401,F403
from tcp_space_tools import TcpSpaceToolSession
from http_space_tools import HttpSpaceToolSession


class SpaceToolSession:
    def __new__(cls, endpoint, *args, **kwargs):
        scheme = endpoint_scheme(endpoint)
        if scheme in {"http", "https"}:
            return HttpSpaceToolSession(endpoint, *args, **kwargs)
        return TcpSpaceToolSession(endpoint, *args, **kwargs)
