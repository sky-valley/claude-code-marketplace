#!/usr/bin/env python3
from __future__ import annotations

from _space_tools_common import *  # noqa: F401,F403
from _space_tools_common import BaseSpaceToolSession
from http_station_client import HttpStationClient


class HttpSpaceToolSession(BaseSpaceToolSession):
    def build_client(self, endpoint, local_state):
        return HttpStationClient(endpoint, local_state)


SpaceToolSession = HttpSpaceToolSession
