import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json, math

# All icons are original geometric interpretations (not traced brand marks) --
# generic shapes that read clearly as "react/node/docker/etc" without
# reproducing any company's trademarked logo art.

HR = 240          # high-res working canvas
GRID = 48         # dot-grid resolution for every logo (kept uniform so the
                   # crossfade between logos reads as one consistent system)

def canvas():
    return Image.new("L", (HR, HR), 0)

def to_grid(im):
    arr = np.asarray(im, dtype=np.float64) / 255.0
    cell = HR // GRID
    small = arr[: cell * GRID, : cell * GRID].reshape(GRID, cell, GRID, cell).mean(axis=(1, 3))
    return (small > 0.4).astype(np.uint8)

def draw_bab08(d):
    # abstract "coworking" mark: a shared space with four linked desks
    d.rounded_rectangle([30, 30, 210, 210], radius=26, outline=255, width=8)
    pts = [(80, 80), (160, 80), (80, 160), (160, 160)]
    for x, y in pts:
        d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=255, width=7)
    d.line([80, 80, 160, 160], fill=255, width=5)
    d.line([160, 80, 80, 160], fill=255, width=5)

def draw_react(d):
    cx, cy = HR / 2, HR / 2
    for ang in (0, 60, 120):
        a = math.radians(ang)
        rx, ry = 95, 34
        pts = []
        for t in range(0, 360, 6):
            tr = math.radians(t)
            x = rx * math.cos(tr)
            y = ry * math.sin(tr)
            xr = x * math.cos(a) - y * math.sin(a)
            yr = x * math.sin(a) + y * math.cos(a)
            pts.append((cx + xr, cy + yr))
        d.line(pts + [pts[0]], fill=255, width=5)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=255)

def draw_typescript(d):
    d.rounded_rectangle([28, 28, HR - 28, HR - 28], radius=22, outline=255, width=8)
    d.line([60, 70, 150, 70], fill=255, width=10)
    d.line([105, 70, 105, 170], fill=255, width=10)
    d.line([150, 120, 190, 120], fill=255, width=8)
    d.line([150, 170, 190, 170], fill=255, width=8)
    d.line([150, 120, 150, 170], fill=255, width=8)

def draw_node(d):
    cx, cy, r = HR / 2, HR / 2, 95
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-90, 271, 60)]
    d.polygon(pts, outline=255, width=8)
    d.polygon([(cx + 40 * math.cos(math.radians(a)), cy + 40 * math.sin(math.radians(a))) for a in range(-90, 271, 60)], fill=255)

def draw_github(d):
    # generic "git graph" mark -- three linked commit nodes, not the octocat
    d.ellipse([40, 40, 80, 80], outline=255, width=8)
    d.ellipse([160, 40, 200, 80], outline=255, width=8)
    d.ellipse([100, 160, 140, 200], outline=255, width=8)
    d.line([60, 80, 120, 160], fill=255, width=6)
    d.line([180, 80, 120, 160], fill=255, width=6)
    d.ellipse([60, 60, 64, 64], fill=255)

def draw_openai(d):
    cx, cy = HR / 2, HR / 2
    for i in range(6):
        a = math.radians(i * 60)
        x, y = cx + 70 * math.cos(a), cy + 70 * math.sin(a)
        d.ellipse([x - 26, y - 26, x + 26, y + 26], outline=255, width=6)
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=255)

def draw_docker(d):
    ox, oy, s, gap = 45, 110, 34, 6
    for col in range(3):
        for row in range(2):
            x0 = ox + col * (s + gap)
            y0 = oy - row * (s + gap)
            d.rectangle([x0, y0, x0 + s, y0 + s], outline=255, width=6)
    d.rectangle([ox + (s + gap), oy - 2 * (s + gap), ox + (s + gap) + s, oy - 2 * (s + gap) + s], outline=255, width=6)
    d.polygon([(30, 150), (210, 150), (190, 190), (50, 190)], outline=255, width=6)

def draw_security(d):
    d.polygon([(120, 30), (200, 60), (200, 130), (120, 210), (40, 130), (40, 60)], outline=255, width=8)
    d.line([90, 118, 112, 145], fill=255, width=10)
    d.line([112, 145, 155, 90], fill=255, width=10)

def draw_python(d):
    cx, cy = HR / 2, HR / 2
    pts = []
    for t in np.linspace(0, 1, 60):
        x = cx + 55 * math.sin(t * math.pi * 2)
        y = cy - 80 + t * 160
        pts.append((x, y))
    d.line(pts, fill=255, width=16, joint="curve")
    d.ellipse([cx - 55 - 10, cy - 80 - 10, cx - 55 + 10, cy - 80 + 10], fill=255)
    d.ellipse([cx + 55 - 10, cy + 80 - 10, cx + 55 + 10, cy + 80 + 10], fill=255)

LOGOS = {
    "bab08": draw_bab08,
    "react": draw_react,
    "typescript": draw_typescript,
    "node": draw_node,
    "github": draw_github,
    "openai": draw_openai,
    "docker": draw_docker,
    "security": draw_security,
    "python": draw_python,
}

out = {}
for name, fn in LOGOS.items():
    im = canvas()
    d = ImageDraw.Draw(im)
    fn(d)
    grid = to_grid(im)
    ys, xs = np.nonzero(grid)
    out[name] = {"grid": GRID, "coords": list(zip(xs.tolist(), ys.tolist()))}
    print(name, len(xs))

with open("/home/claude/profile/build/logos.json", "w") as f:
    json.dump(out, f)
