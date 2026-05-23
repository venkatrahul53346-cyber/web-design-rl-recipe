"""Perceptual-hash deduplication for generated-website screenshots.

A simple DCT-based pHash that treats two images as duplicates when
their 64-bit fingerprint differs in fewer than ``hamming_threshold`` bits.

Why DCT pHash and not aHash / dHash:
- aHash is too lenient on similar-brightness pages (most modern sites
  default to bg-white, which makes their average-hash look the same).
- dHash is fragile to vertical-position shifts (a section moved 100px
  down can flip half the bits).
- DCT pHash compares low-frequency content — the layout's "shape" — and
  ignores high-frequency content like text antialiasing.

Usage:
    from src.dedup import phash, is_duplicate
    h = phash("/path/to/screenshot.png")
    seen = []
    if is_duplicate(h, seen, hamming_threshold=8):
        print("near-duplicate, reject")
    else:
        seen.append(h)
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image
from scipy.fftpack import dct


_HASH_DIM = 8        # 8x8 = 64-bit fingerprint
_DCT_INPUT = 32      # resize to 32x32 before DCT


def phash(image_path: str | Path) -> int:
    """Compute a 64-bit perceptual hash for an image.

    The hash is positioned-aware (a layout shifted 200px shifts bits)
    but lighting-invariant (pages with similar layout but different
    background brightness still hash close).
    """
    img = Image.open(image_path).convert("L").resize(
        (_DCT_INPUT, _DCT_INPUT), Image.LANCZOS,
    )
    arr = np.asarray(img, dtype=np.float64)
    # 2D DCT-II = DCT-II along each axis sequentially.
    dct_full = dct(dct(arr, axis=0, norm="ortho"), axis=1, norm="ortho")
    low_freq = dct_full[:_HASH_DIM, :_HASH_DIM]
    # Drop the DC term (mean luminance) — it dominates the median otherwise.
    flat = low_freq.flatten()
    median = np.median(flat[1:])
    bits = (flat > median).astype(np.uint8)
    return int("".join(str(b) for b in bits), 2)


def hamming(a: int, b: int) -> int:
    """Hamming distance between two 64-bit fingerprints."""
    return bin(a ^ b).count("1")


def is_duplicate(new_hash: int, prior_hashes: Sequence[int],
                 hamming_threshold: int = 8) -> bool:
    """Return True if ``new_hash`` is within ``hamming_threshold`` bits of
    ANY prior hash. Default threshold of 8 / 64 ≈ 12% bit difference is
    a conservative "near-duplicate" cutoff for full-page screenshots —
    layouts with substantively different structure typically differ in
    ≥20 bits."""
    return any(hamming(new_hash, h) <= hamming_threshold for h in prior_hashes)


def distance_matrix(hashes: Sequence[int]) -> np.ndarray:
    """Compute the full N×N hamming distance matrix. Useful for diagnostics
    when comparing a batch of generations."""
    n = len(hashes)
    out = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(i + 1, n):
            d = hamming(hashes[i], hashes[j])
            out[i, j] = out[j, i] = d
    return out


def diversity_summary(hashes: Sequence[int]) -> dict:
    """Returns mean / min / max pairwise hamming distance + duplicate count
    for a batch of fingerprints."""
    if len(hashes) < 2:
        return {"n": len(hashes), "min": 0, "mean": 0.0, "max": 0, "duplicates": 0}
    m = distance_matrix(hashes)
    iu = np.triu_indices(len(hashes), k=1)
    pairs = m[iu]
    duplicates = int((pairs <= 8).sum())
    return {
        "n": len(hashes),
        "min": int(pairs.min()),
        "mean": float(pairs.mean()),
        "max": int(pairs.max()),
        "duplicates": duplicates,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m src.dedup IMAGE1 [IMAGE2 ...]")
        sys.exit(1)
    hashes = [(p, phash(p)) for p in sys.argv[1:]]
    for p, h in hashes:
        print(f"{p}  hash=0x{h:016x}")
    if len(hashes) > 1:
        print()
        print("pairwise hamming distance matrix:")
        names = [Path(p).name for p, _ in hashes]
        m = distance_matrix([h for _, h in hashes])
        print("   " + " ".join(f"{n[:8]:>8}" for n in names))
        for i, name in enumerate(names):
            row = " ".join(f"{m[i, j]:>8}" for j in range(len(names)))
            print(f"{name[:8]:>8} {row}")
        print()
        s = diversity_summary([h for _, h in hashes])
        print(f"summary: n={s['n']}, min={s['min']}, mean={s['mean']:.2f}, "
              f"max={s['max']}, duplicates={s['duplicates']}")
