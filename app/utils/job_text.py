from __future__ import annotations

import hashlib
import re
import unicodedata
from html import unescape

from bs4 import BeautifulSoup


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = unescape(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None


def normalize_title(value: str) -> str:
    return normalize_text(value.lower()) or ""


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_text(value.lower())


def html_to_text(html: str | None) -> str | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    normalized = normalize_text(text)
    if normalized:
        normalized = re.sub(r"\s+([.,;:!?])", r"\1", normalized)
    return normalized


def stable_hash(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned.rstrip("/") or None
