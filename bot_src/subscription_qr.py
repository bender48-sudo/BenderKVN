"""Happ subscription URL → QR PNG (P3-FLOW-05)."""
from __future__ import annotations

from io import BytesIO

import qrcode


def subscription_qr_png(subscription_url: str) -> bytes:
    """PNG bytes encoding subscription URL (same payload as copy-paste in Happ)."""
    url = (subscription_url or "").strip()
    if not url:
        raise ValueError("empty subscription_url")
    img = qrcode.make(url)
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()
