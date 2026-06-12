"""ATS client registry."""

from __future__ import annotations

from typing import Any

from .ats import CLIENTS
from .ats.base import ATSClient

SUPPORTED_PORTALS = frozenset(CLIENTS.keys())


def get_client(portal: str) -> Any | None:
    return CLIENTS.get(portal)


__all__ = ["ATSClient", "CLIENTS", "SUPPORTED_PORTALS", "get_client"]
