import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from scipy import ndimage
import json, math

SRC = "/home/claude/profile/source.png"
GRID_W, GRID_H = 300, 340

def load_crop():
    im = Image.open(SRC).convert("RGB")
    # head-and-shoulders crop, trims the fragments of other people at edges
    im = im.crop((35, 150, 334, 506))  # head-and-shoulders; trims the "Project Initiative
                                        # Club" backdrop signage and the edge of the next person
    im = im.resize((GRID_W, GRID_H), Image.LANCZOS)
    return im

def prep_gray(im):
    g = im.convert("L")
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.3)
    g = g.filter(ImageFilter.UnsharpMask(radius=3, percent=140, threshold=3))
    return np.asarray(g, dtype=np.float64)

def segment_subject(im):
    arr = np.asarray(im, dtype=np.float64)
    # sample background swatches from the four corners (backdrop banner)
    corners = np.concatenate([
        arr[0:10, 0:10].reshape(-1, 3),
        arr[0:10, -10:].reshape(-1, 3),
    ], axis=0)
    bg_color = np.median(corners, axis=0)
    dist = np.linalg.norm(arr - bg_color, axis=2)
    mask = dist > 40  # color-distance threshold
    # sever thin single-pixel bridges (e.g. where hair edge anti-aliases into nearby
    # background signage) before component selection, so they don't fuse into one blob
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    # pick the largest connected component BEFORE any closing, so a nearby disjoint
    # bright region (e.g. background signage) can't bridge into the subject mask
    labeled, n = ndimage.label(mask)
    if n > 0:
        sizes = ndimage.sum(mask, labeled, range(1, n + 1))
        biggest = np.argmax(sizes) + 1
        mask = labeled == biggest
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    mask = ndimage.binary_fill_holes(mask)
    # re-select the largest component again post-closing/fill, in case closing merged slivers
    labeled, n = ndimage.label(mask)
    if n > 0:
        sizes = ndimage.sum(mask, labeled, range(1, n + 1))
        biggest = np.argmax(sizes) + 1
        mask = labeled == biggest
    mask = ndimage.binary_erosion(mask, structure=np.ones((3, 3)))
    return mask

def floyd_steinberg(aff, mask=None):
    """aff: float array, higher = more likely to place a dot. serpentine FS dithering.
    error is never diffused outside mask (prevents bleed along the silhouette edge)."""
    h, w = aff.shape
    buf = aff.copy()
    out = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        d = 1 if y % 2 == 0 else -1
        for x in xs:
            if mask is not None and not mask[y, x]:
                continue
            old = buf[y, x]
            new = 255.0 if old >= 128 else 0.0
            out[y, x] = 1 if new == 255.0 else 0
            err = old - new
            for ny, nx, frac in ((y, x + d, 7/16), (y + 1, x - d, 3/16), (y + 1, x, 5/16), (y + 1, x + d, 1/16)):
                if 0 <= ny < h and 0 <= nx < w:
                    if mask is None or mask[ny, nx]:
                        buf[ny, nx] += err * frac
    return out

def evenness_metric(coords, groups, grid_w, grid_h, n_groups, bins=6):
    """Tests whether each group draws proportionally from the SAME spatial density as the
    full portrait (i.e. no group is a spatial wipe/quadrant/patch). For every bin, a group's
    expected share is (bin's overall dot count) * (group size / total dots). Returns the mean
    relative deviation across bins+groups, weighted by bin population. Lower = better scatter."""
    if len(coords) == 0:
        return 0.0
    xs = np.array([c[0] for c in coords])
    ys = np.array([c[1] for c in coords])
    groups = np.array(groups)
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    bx = np.clip(((xs - x0) / (x1 - x0) * bins).astype(int), 0, bins - 1)
    by = np.clip(((ys - y0) / (y1 - y0) * bins).astype(int), 0, bins - 1)
    bin_id = bx * bins + by
    total = len(coords)
    devs, weights = [], []
    for b in range(bins * bins):
        in_bin = bin_id == b
        bin_total = in_bin.sum()
        if bin_total < n_groups:  # too sparse a cell to judge distribution
            continue
        for g in range(n_groups):
            group_size = (groups == g).sum()
            expect = bin_total * (group_size / total)
            actual = (in_bin & (groups == g)).sum()
            if expect > 0:
                devs.append(abs(actual - expect) / expect)
                weights.append(expect)
    if not devs:
        return 0.0
    return float(np.average(devs, weights=weights))

def build(mode):
    im = load_crop()
    gray = prep_gray(im)
    mask = segment_subject(im)  # both themes render the subject only; the panel's
                                 # own theme background shows through everywhere else
    if mode == "dark":
        aff = gray  # bright = dot (illuminated subject glows on dark background)
    else:
        aff = 255.0 - gray  # dark regions of the subject = dot (ink-on-paper feel)
    dots = floyd_steinberg(aff, mask=mask)

    ys, xs = np.nonzero(dots)
    coords = list(zip(xs.tolist(), ys.tolist()))

    # thin toward the ~17k dot / ~900KB-1MB banner budget from the brief
    thin_rng = np.random.default_rng(7)
    thin_factor = 0.72 if mode == "dark" else 0.30
    keep = thin_rng.random(len(coords)) < thin_factor
    coords = [c for c, k in zip(coords, keep) if k]

    # assign each dot to one of 60 interleaved fade groups, scattered (not row/quadrant based)
    n_groups = 60
    rng = np.random.default_rng(42)
    order = rng.permutation(len(coords))
    groups = [0] * len(coords)
    for rank, i in enumerate(order):
        groups[i] = rank % n_groups

    even = evenness_metric(coords, groups, GRID_W, GRID_H, n_groups)
    ink_coverage = len(coords) / (GRID_W * GRID_H)

    result = {
        "mode": mode,
        "grid_w": GRID_W,
        "grid_h": GRID_H,
        "dot_count": len(coords),
        "ink_coverage": ink_coverage,
        "evenness": even,
        "coords": coords,
        "groups": groups,
    }
    with open(f"/home/claude/profile/build/dots_{mode}.json", "w") as f:
        json.dump(result, f)
    print(mode, "dots:", len(coords), "ink_coverage:", round(ink_coverage, 4), "evenness:", round(even, 4))

build("dark")
build("light")
