#!/usr/bin/env python3
"""Generate placeholder setup guide GIFs (P3-FLOW-06). Replace with real screen recordings later."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "portal" / "media"

FRAMES = {
    "ios-first-connect.gif": [
        ("iPhone · Happ", "1. Установите Happ"),
        ("iPhone · Happ", "2. + → из буфера / QR"),
        ("iPhone · Happ", "3. Включите VPN"),
    ],
    "android-first-connect.gif": [
        ("Android · Happ", "1. Google Play → Happ"),
        ("Android · Happ", "2. Вставьте ссылку"),
        ("Android · Happ", "3. Включите VPN"),
    ],
}


def _render_frames(labels: list[tuple[str, str]]):
    from PIL import Image, ImageDraw, ImageFont

    w, h = 360, 640
    images = []
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        step_font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        title_font = ImageFont.load_default()
        step_font = title_font
    for title, step in labels:
        img = Image.new("RGB", (w, h), "#0a0a0c")
        draw = ImageDraw.Draw(img)
        draw.rectangle((12, 12, w - 12, h - 12), outline="#e85d04", width=3)
        draw.text((24, 48), title, fill="#f5f5f5", font=title_font)
        draw.text((24, 280), step, fill="#22d3ee", font=step_font)
        draw.text((24, h - 80), "BenderVPN", fill="#888888", font=title_font)
        images.append(img)
    return images


def main() -> int:
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"generate_setup_guide_media: install Pillow ({exc})", file=__import__("sys").stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for name, labels in FRAMES.items():
        path = OUT / name
        imgs = _render_frames(labels)
        imgs[0].save(
            path,
            save_all=True,
            append_images=imgs[1:],
            duration=1200,
            loop=0,
            optimize=True,
        )
        print(f"Wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
