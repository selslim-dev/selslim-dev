"""
Portrait -> dot-matrix pipeline.
Source of truth for the animated banner's portrait layer.
Outputs .npy dot-coordinate arrays (grid space 300x340) for both themes.
"""
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from scipy import ndimage

GRID_W, GRID_H = 300, 340
CROP_BOX = (58, 8, 354, 480)  # locked crop on the 354x515 source


def load_and_frame(src_path):
    im = Image.open(src_path).convert("RGB")
    crop = im.crop(CROP_BOX)
    cw, ch = crop.size

    # sample background from the two top corners (reliably banner-blue in this photo)
    arr = np.array(crop)
    patch = np.concatenate([
        arr[0:15, 0:15].reshape(-1, 3),
        arr[0:15, -15:].reshape(-1, 3),
    ], axis=0)
    bg_color = patch.mean(axis=0)

    # preserve aspect ratio: fit to target height, pad width to GRID_W
    scale = GRID_H / ch
    new_w = max(1, round(cw * scale))
    resized = crop.resize((new_w, GRID_H), Image.LANCZOS)

    canvas = Image.new("RGB", (GRID_W, GRID_H), tuple(bg_color.astype(int)))
    off_x = (GRID_W - new_w) // 2
    canvas.paste(resized, (off_x, 0))

    return canvas, bg_color, (off_x, 0, off_x + new_w, GRID_H)


def segment_mask(framed_rgb, bg_color, thresh=42):
    arr = np.array(framed_rgb).astype(np.float32)
    dist = np.sqrt(((arr - bg_color[None, None, :]) ** 2).sum(axis=-1))
    fg = dist > thresh

    # opening first: erode away thin bridges (e.g. background logo text
    # touching hair) before we ever pick a "largest" component, then
    # dilate back. Do NOT close here - closing would reconnect exactly
    # the bridges we're trying to break.
    fg = ndimage.binary_opening(fg, structure=np.ones((3, 3)), iterations=7)

    labeled, n = ndimage.label(fg)
    if n > 0:
        sizes = ndimage.sum(fg, labeled, range(1, n + 1))
        largest = np.argmax(sizes) + 1
        fg = labeled == largest
        # now that we have a single isolated component, closing + hole
        # fill is safe and just smooths its own boundary/interior
        fg = ndimage.binary_closing(fg, structure=np.ones((3, 3)), iterations=2)
        fg = ndimage.binary_fill_holes(fg)
    return fg


def preprocess_gray(framed_rgb):
    g = ImageOps.autocontrast(framed_rgb.convert("L"), cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.3)
    g = g.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    return np.array(g).astype(np.float32)


def serpentine_floyd_steinberg(gray, mask=None, threshold=128.0):
    """Manual FS dithering with alternating (serpentine) row direction.
    If mask is given, only pixels inside mask are processed and error is
    only diffused to neighbors that are also inside the mask (no bleed
    across the segmentation boundary)."""
    h, w = gray.shape
    buf = gray.copy()
    out = np.zeros((h, w), dtype=bool)
    if mask is None:
        mask = np.ones((h, w), dtype=bool)

    for y in range(h):
        left_to_right = (y % 2 == 0)
        xs = range(w) if left_to_right else range(w - 1, -1, -1)
        for x in xs:
            if not mask[y, x]:
                continue
            old = buf[y, x]
            new = 0.0 if old < threshold else 255.0
            out[y, x] = new < 1.0  # dot "on" where dark
            err = old - new
            step = 1 if left_to_right else -1
            nbrs = [(y, x + step, 7 / 16), (y + 1, x - step, 3 / 16),
                    (y + 1, x, 5 / 16), (y + 1, x + step, 1 / 16)]
            for ny, nx, frac in nbrs:
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                    buf[ny, nx] += err * frac
    return out


def dots_from_bitmap(bitmap):
    ys, xs = np.nonzero(bitmap)
    return np.stack([xs, ys], axis=1).astype(np.int16)  # (N,2) in grid space


def process(src_path, mode):
    framed, bg_color, content_box = load_and_frame(src_path)
    mask = segment_mask(framed, bg_color, thresh=42)
    gray = preprocess_gray(framed)

    if mode == "dark":
        bitmap = serpentine_floyd_steinberg(gray, mask=mask)
    else:
        # keep the background (don't hard-cut it like dark mode does) but
        # lighten it substantially before dithering so it reads as a soft
        # texture behind the subject rather than competing at equal density
        gray_light = gray.copy()
        gray_light[~mask] = gray_light[~mask] + (255 - gray_light[~mask]) * 0.93
        bitmap = serpentine_floyd_steinberg(gray_light, mask=None)

    dots = dots_from_bitmap(bitmap)
    return dots, bitmap, framed


if __name__ == "__main__":
    import sys
    src = "build/source.jpg"
    for mode in ("dark", "light"):
        dots, bitmap, framed = process(src, mode)
        np.save(f"out/portrait_dots_{mode}.npy", dots)
        # quick raster preview: dot color per theme on its page background
        bg = (10, 16, 31) if mode == "dark" else (250, 249, 252)
        fg = (167, 139, 250) if mode == "dark" else (124, 58, 237)
        prev = Image.new("RGB", (GRID_W, GRID_H), bg)
        px = prev.load()
        for x, y in dots:
            px[int(x), int(y)] = fg
        prev = prev.resize((GRID_W * 2, GRID_H * 2), Image.NEAREST)
        prev.save(f"build/preview_{mode}.png")
        print(mode, "dot count:", len(dots), "coverage:", round(len(dots) / (GRID_W * GRID_H) * 100, 1), "%")
