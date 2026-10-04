"""Render quality measurement -- the "is the output actually right?" layer.

A render that is 100% black, 100% white, or completely empty is a *successful*
render as far as Blender is concerned. ``bpy.ops.render.render()`` returns
``{'FINISHED'}``, the file is written, and nothing anywhere reports a problem.
Measuring the pixels is the only way to catch it.

Pixel reading notes (verified on 5.2.2):
  * ``image.pixels`` is a flat float sequence, row-major, bottom-up,
    length ``width * height * channels``.
  * Use ``pixels.foreach_get(buf)`` -- it is a direct memcpy and is orders of
    magnitude faster than indexing ``pixels[i]`` in a Python loop.
    Measured: 96x96 RGBA, 0.0025 s with foreach_get.
  * For 8-bit PNGs the values are the raw byte values divided by 255, i.e.
    still sRGB-encoded. They are NOT linearised scene-referred floats.
    A pixel that was byte 50 reads back as exactly 0.196078.
  * ``Render Result`` is a special image datablock whose ``.pixels`` are not
    reliably populated right after a background render. Save to file and load
    the file back instead -- that is what this module does.
"""

import bpy

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:  # Blender bundles numpy, but never assume
    HAVE_NUMPY = False


def _read_pixels(img):
    """Return a flat list of floats, len == w*h*channels."""
    n = img.size[0] * img.size[1] * img.channels
    buf = [0.0] * n
    img.pixels.foreach_get(buf)
    return buf


def _stats_slow(px, channels, w, h):
    luma = []
    for i in range(0, len(px), channels):
        r, g, b = px[i], px[i + 1], px[i + 2]
        luma.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    return _summarise_luma(luma, px, channels, w, h)


def _stats_fast(px, channels, w, h):
    a = np.asarray(px, dtype=np.float32).reshape(-1, channels)
    rgb = a[:, :3]
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return _summarise_luma(luma.tolist(), px, channels, w, h)


def _summarise_luma(luma, px, channels, w, h):
    n = len(luma)
    ordered = sorted(luma)
    mean = sum(luma) / n
    median = ordered[n // 2]
    p01 = ordered[int(n * 0.01)]
    p99 = ordered[min(n - 1, int(n * 0.99))]
    black = sum(1 for v in luma if v <= 0.002)
    white = sum(1 for v in luma if v >= 0.998)

    # content bounding box: columns/rows that contain at least one
    # non-background pixel. Background = within `tol` of the corner pixel.
    tol = 0.02
    corner = luma[0]
    cols_hit, rows_hit = set(), set()
    for idx, v in enumerate(luma):
        if abs(v - corner) > tol:
            y, x = divmod(idx, w)
            cols_hit.add(x)
            rows_hit.add(y)

    alpha = None
    if channels == 4:
        alpha = sum(px[i] for i in range(3, len(px), 4)) / (w * h)

    return {
        "width": w,
        "height": h,
        "channels": channels,
        "mean_luma": round(mean, 6),
        "median_luma": round(median, 6),
        "p01_luma": round(p01, 6),
        "p99_luma": round(p99, 6),
        "contrast_p01_p99": round(p99 - p01, 6),
        "min_luma": round(ordered[0], 6),
        "max_luma": round(ordered[-1], 6),
        "black_fraction": round(black / n, 6),
        "white_fraction": round(white / n, 6),
        "mean_alpha": None if alpha is None else round(alpha, 6),
        "content_bbox": None if not cols_hit else [
            min(cols_hit), min(rows_hit), max(cols_hit), max(rows_hit)
        ],
        "content_fraction": round(len(cols_hit) * len(rows_hit) / float(w * h), 6) if cols_hit else 0.0,
        "background_luma": round(corner, 6),
    }


def analyze_image_file(path, fast=True):
    """Load a rendered image from disk and compute quality statistics.

    Returns the stats dict, or ``{"error": ...}`` if the file is not a
    readable image.
    """
    if not path:
        return {"error": "no path given"}
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size
        channels = img.channels
        px = _read_pixels(img)
        stats = (_stats_fast if (fast and HAVE_NUMPY) else _stats_slow)(px, channels, w, h)
        stats["path"] = path
        stats["filepath_raw"] = img.filepath_raw
        stats["colorspace"] = img.colorspace_settings.name
        stats["is_float"] = img.is_float
        stats["depth"] = img.depth
        stats["verdict"], stats["reasons"] = judge(stats)
        return stats
    finally:
        bpy.data.images.remove(img)


def judge(stats, mean_black_threshold=0.010, black_fraction_limit=0.985,
          white_fraction_limit=0.30, min_contrast=0.02):
    """Turn raw statistics into a verdict plus human-readable reasons.

    ``verdict`` is ``"ok"``, ``"suspicious"`` or ``"bad"``.

    Thresholds were calibrated against six deliberately broken scenes rendered
    in Blender 5.2.2 (see references/09-verification-loop.md sec 3.0).
    Defaults:

    ``mean_black_threshold``   mean luma below this counts as a dead frame
    ``black_fraction_limit``   fraction of pure-black pixels that is "empty"
    ``white_fraction_limit``   fraction of clipped-white pixels that is "blown"
    ``min_contrast``           1st-99th percentile luma spread that is "flat"

    IMPORTANT -- this is a *necessary*, not a *sufficient*, check. Measured on
    5.2.2, all of these broken scenes rendered successfully AND produced frames
    that pass a naive "is it black?" test, because the default world supplies
    faint grey ambient light::

        no light objects       mean=0.00032  black=91.8%
        subject not linked     mean=0.04123  black=78.8%
        no material assigned   mean=0.04123  black=78.8%
        obj.hide_render = True mean=0.00032  black=91.8%
        BSDF not wired to out  mean=0.00032  black=91.8%
        scale axis = 0         mean=0.00032  black=91.8%

    Every one of them returned ``{'FINISHED'}``. The first three rows also pass
    a pure "fraction of pure-black pixels" test. Only a mean-luma floor plus the
    scene check together catch them. Always run both.
    """
    reasons = []
    if "error" in stats:
        return "bad", [stats["error"]]

    mean = stats["mean_luma"]
    contrast = stats["contrast_p01_p99"]
    black = stats["black_fraction"]
    white = stats["white_fraction"]
    hard = []

    if mean < mean_black_threshold:
        hard.append(
            f"frame is effectively black: mean luma {mean:.5f} < {mean_black_threshold}. "
            f"Either nothing is lit, the subject is out of frame, or it is hidden from render"
        )
    if mean <= 0.0005 and black > 0.99:
        hard.append("frame is entirely black (nothing was lit, or nothing was in frame)")
    if mean >= 0.999 and white > 0.99:
        hard.append("frame is entirely white (blown out; check light energy and view transform)")
    if contrast < min_contrast and mean_black_threshold <= mean <= 1 - mean_black_threshold:
        hard.append(f"frame is flat: 1-99 percentile contrast is only {contrast:.4f}")

    soft = []
    if black > black_fraction_limit:
        soft.append(f"{black*100:.2f}% of the frame is pure black -- likely an empty framing")
    if white > white_fraction_limit:
        soft.append(f"{white*100:.1f}% of the frame is clipped to pure white")
    if stats.get("content_bbox") is None and mean > mean_black_threshold:
        soft.append("no pixel differs from the background -- subject may be missing or out of frame")

    if hard:
        return "bad", hard + soft
    if soft:
        return "suspicious", soft
    return "ok", []


def compare(a, b):
    """Compare two stats dicts (e.g. two render iterations) and list deltas.

    Used by the improvement loop: did changing the light actually change the
    exposure, or did nothing happen?
    """
    keys = ("mean_luma", "median_luma", "p01_luma", "p99_luma", "contrast_p01_p99",
            "black_fraction", "white_fraction", "content_fraction", "mean_alpha")
    deltas = {}
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            deltas[k] = round(vb - va, 6)
    deltas["_relative_mean_luma"] = (
        round(deltas["mean_luma"] / a["mean_luma"], 4) if a.get("mean_luma") else None
    )
    return deltas


def print_stats(stats, title="image analysis"):
    """Pretty-print a stats dict."""
    print(f"--- {title} ---")
    if "error" in stats:
        print("  ERROR:", stats["error"])
        return
    print(f"  size            {stats['width']}x{stats['height']} ch={stats['channels']} "
          f"depth={stats['depth']} float={stats['is_float']} cs={stats['colorspace']}")
    print(f"  mean luma       {stats['mean_luma']:.6f}")
    print(f"  median luma     {stats['median_luma']:.6f}")
    print(f"  p01 / p99       {stats['p01_luma']:.6f} / {stats['p99_luma']:.6f} "
          f"(contrast {stats['contrast_p01_p99']:.6f})")
    print(f"  min / max       {stats['min_luma']:.6f} / {stats['max_luma']:.6f}")
    print(f"  pure black      {stats['black_fraction']*100:.2f}%")
    print(f"  pure white      {stats['white_fraction']*100:.2f}%")
    if stats.get("mean_alpha") is not None:
        print(f"  mean alpha      {stats['mean_alpha']:.6f}")
    print(f"  content bbox    {stats['content_bbox']} ({stats['content_fraction']*100:.1f}% of frame)")
    print(f"  VERDICT         {stats['verdict'].upper()}")
    for r in stats["reasons"]:
        print(f"    - {r}")
