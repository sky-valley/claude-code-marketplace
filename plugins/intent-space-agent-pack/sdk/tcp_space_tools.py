#!/usr/bin/env python3
from __future__ import annotations

from _space_tools_common import *  # noqa: F401,F403
from _space_tools_common import BaseSpaceToolSession
from tcp_station_client import TcpStationClient


class TcpSpaceToolSession(BaseSpaceToolSession):
    def build_client(self, endpoint, local_state):
        return TcpStationClient(endpoint, local_state)


SpaceToolSession = TcpSpaceToolSession
