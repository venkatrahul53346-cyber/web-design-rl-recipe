"""Generate the 5 procedural placeholder JPGs that ship with every task.

Why procedural: avoids licensing of real photography, keeps the repo
self-contained, deterministic across regenerations.

Each image is ~600x400 px (small) but visually distinct enough for the
agent to know what kind of content was supposed to be there.

Run once after cloning:
    .venv/bin/python scripts/build_placeholders.py

Output: templates/_placeholders/{photo-product-1,photo-product-2,
photo-portrait-1,photo-landscape-1,illustration-abstract}.jpg
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "templates" / "_placeholders"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 720, 480


def _gradient(rng: random.Random, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Vertical 3-stop linear gradient between sampled palette colors."""
    a, b, c = rng.sample(palette, 3) if len(palette) >= 3 else (palette + palette)[:3]
    img = Image.new("RGB", (W, H), a)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        if y < H // 2:
            t = y / (H // 2)
            col = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        else:
            t = (y - H // 2) / (H // 2)
            col = tuple(int(b[i] * (1 - t) + c[i] * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=col)
    return img


def _add_noise(img: Image.Image, rng: random.Random, strength: int = 12) -> Image.Image:
    """Add per-pixel noise — gives a procedural / film-grain feel."""
    px = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            n = rng.randint(-strength, strength)
            px[x, y] = (
                max(0, min(255, r + n)),
                max(0, min(255, g + n)),
                max(0, min(255, b + n)),
            )
    return img


def _add_centered_shape(img: Image.Image, rng: random.Random,
                       shape: str = "circle") -> Image.Image:
    """Add a soft-edged centered shape — gives the image a focal point."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    cx, cy = W // 2, H // 2
    r = min(W, H) // 3
    color = (
        rng.randint(180, 255),
        rng.randint(180, 255),
        rng.randint(180, 255),
        160,
    )
    if shape == "circle":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif shape == "rect":
        d.rectangle([cx - r, cy - r * 2 // 3, cx + r, cy + r * 2 // 3], fill=color)
    elif shape == "horizon":
        d.rectangle([0, cy + r // 2, W, H], fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(20))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ---------------------------------------------------------------------------

def photo_product_1() -> Image.Image:
    """Generic still-life — warm tones, centered subject."""
    rng = random.Random(1)
    palette = [(220, 200, 180), (180, 150, 120), (90, 70, 60),
               (245, 230, 215), (140, 110, 95)]
    img = _gradient(rng, palette)
    img = _add_centered_shape(img, rng, "circle")
    img = _add_noise(img, rng)
    return img


def photo_product_2() -> Image.Image:
    """Cooler-toned product — a second variant for grids."""
    rng = random.Random(2)
    palette = [(190, 200, 215), (130, 145, 165), (60, 70, 85),
               (220, 225, 235), (95, 110, 130)]
    img = _gradient(rng, palette)
    img = _add_centered_shape(img, rng, "rect")
    img = _add_noise(img, rng)
    return img


def photo_portrait_1() -> Image.Image:
    """Generic portrait — warm skin tones with vignette."""
    rng = random.Random(3)
    palette = [(60, 50, 45), (140, 100, 85), (220, 180, 155),
               (200, 160, 130), (80, 60, 50)]
    img = _gradient(rng, palette)
    img = _add_centered_shape(img, rng, "circle")
    img = _add_noise(img, rng)
    return img


def photo_landscape_1() -> Image.Image:
    """Generic landscape — sky over land/sea horizon."""
    rng = random.Random(4)
    palette = [(160, 200, 220), (200, 215, 230), (90, 110, 90),
               (60, 80, 70), (180, 195, 175)]
    img = _gradient(rng, palette)
    img = _add_centered_shape(img, rng, "horizon")
    img = _add_noise(img, rng, strength=8)
    return img


def illustration_abstract() -> Image.Image:
    """Abstract decorative — saturated mesh-gradient feel."""
    rng = random.Random(5)
    palette = [(140, 92, 246), (110, 91, 203), (96, 165, 250),
               (236, 72, 153), (52, 211, 153)]
    img = _gradient(rng, palette)
    # Multiple soft circles for a mesh-gradient effect
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for _ in range(4):
        cx = rng.randint(50, W - 50)
        cy = rng.randint(50, H - 50)
        r = rng.randint(80, 200)
        col = rng.choice(palette)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=(*col, 120))
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img = _add_noise(img, rng, strength=6)
    return img


GENERATORS = {
    "photo-product-1.jpg":     photo_product_1,
    "photo-product-2.jpg":     photo_product_2,
    "photo-portrait-1.jpg":    photo_portrait_1,
    "photo-landscape-1.jpg":   photo_landscape_1,
    "illustration-abstract.jpg": illustration_abstract,
}

if __name__ == "__main__":
    for name, fn in GENERATORS.items():
        path = OUT / name
        img = fn()
        img.save(path, "JPEG", quality=85, optimize=True)
        print(f"wrote {path} ({path.stat().st_size // 1024} KB)")
