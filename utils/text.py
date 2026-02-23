# /utils/text.py
# This module provides utility functions for handling text data, including binary detection, base64 decoding, text truncation, and whitespace compaction.
import base64
import re


BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv",
    ".woff", ".woff2", ".ttf", ".otf",
}


def is_probably_binary_bytes(b: bytes) -> bool:
    if not b:
        return False
    if b"\x00" in b:
        return True
    # heuristic: lots of non-text control chars
    ctrl = sum(1 for x in b[:4000] if x < 9 or (13 < x < 32))
    return ctrl / max(1, min(len(b), 4000)) > 0.08


def safe_b64decode(s: str) -> bytes:
    return base64.b64decode(s.encode("utf-8"), validate=False)


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.75)
    tail = max_chars - head
    return text[:head].rstrip() + "\n...\n" + text[-tail:].lstrip()


def compact_whitespace(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s).strip()