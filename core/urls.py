"""Pure validation helpers for user-authored web links."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def validate_web_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("url must be text")
    clean = value.strip()
    if not clean or any(ord(character) < 32 for character in clean):
        raise ValueError("url must be a complete HTTP or HTTPS address")
    try:
        parsed = urlsplit(clean)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError("url must be a valid HTTP or HTTPS address") from None
    if parsed.scheme.casefold() not in {"http", "https"} or not hostname:
        raise ValueError("url must begin with http:// or https:// and include a host")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("url contains an invalid port")
    return clean


def safe_web_url(value: Any) -> str | None:
    try:
        return validate_web_url(value)
    except ValueError:
        return None
