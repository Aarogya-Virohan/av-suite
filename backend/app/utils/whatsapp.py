from __future__ import annotations

import re
from urllib.parse import quote


def build_whatsapp_link(phone: str, message: str) -> str:
    """Build a wa.me click-to-chat link for an Indian phone number."""

    digits = re.sub(r"\D", "", phone or "")
    if not digits.startswith("91"):
        digits = f"91{digits}"

    encoded_message = quote(message or "", safe="")
    return f"https://wa.me/{digits}?text={encoded_message}"