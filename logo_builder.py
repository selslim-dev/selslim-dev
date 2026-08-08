import numpy as np
from scipy.optimize import linear_sum_assignment

N_PER_LOGO = 100


def _ring(n, cx, cy, r, w):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rr = r + (np.random.default_rng(1).uniform(-w / 2, w / 2, n))
    return np.stack([cx + rr * np.cos(t), cy + rr * np.sin(t)], axis=1)


def _disc(n, cx, cy, r, seed=2):
    rng = np.random.default_rng(seed)
    t = rng.uniform(0, 2 * np.pi, n)
    rad = r * np.sqrt(rng.uniform(0, 1, n))
    return np.stack([cx + rad * np.cos(t), cy + rad * np.sin(t)], axis=1)


def _rounded_square(n, cx, cy, s, seed=3):
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-s / 2, s / 2, (n, 2))
    return pts + [cx, cy]


def _hexagon(n, cx, cy, r, seed=4):
    rng = np.random.default_rng(seed)
    angs = np.arange(6) * np.pi / 3
    verts = np.stack([cx + r * np.cos(angs), cy + r * np.sin(angs)], axis=1)
    out = []
    for i in range(n):
        e = i % 6
        t = rng.uniform(0, 1)
        out.append(verts[e] * (1 - t) + verts[(e + 1) % 6] * t)
    return np.array(out)


def _shield(n, cx, cy, w, h, seed=5):
    rng = np.random.default_rng(seed)
    pts = []
    for _ in range(n):
        u = rng.uniform(-1, 1)
        v = rng.uniform(-1, 1)
        if v > 0.3 and abs(u) > (1 - v) * 1.0:
            v = v * 0.3
        pts.append([cx + u * w / 2, cy + v * h / 2])
    return np.array(pts)


def logo_points(name, cx, cy, scale, n=N_PER_LOGO):
    if name == "Bab08":
        outer = _ring(n // 2, cx, cy, scale * 0.62, scale * 0.10)
        inner = _disc(n - n // 2, cx, cy, scale * 0.22, seed=21)
        return np.concatenate([outer, inner])
    if name == "React":
        pts = []
        for k in range(3):
            ang = k * np.pi / 3
            e = _ring(n // 3, cx, cy, scale * 0.55, scale * 0.06)
            rot = np.array([[np.cos(ang), -np.sin(ang) * 0.42], [np.sin(ang), np.cos(ang) * 0.42]])
            rel = e - [cx, cy]
            pts.append(rel @ rot.T + [cx, cy])
        core = _disc(n - 3 * (n // 3), cx, cy, scale * 0.10, seed=22)
        return np.concatenate(pts + [core])
    if name == "TypeScript":
        return _rounded_square(n, cx, cy, scale * 1.1, seed=23)
    if name == "Node.js":
        return _hexagon(n, cx, cy, scale * 0.62, seed=24)
    if name == "GitHub":
        outer = _disc(int(n * 0.85), cx, cy, scale * 0.6, seed=25)
        tail = _disc(n - int(n * 0.85), cx + scale * 0.35, cy + scale * 0.45, scale * 0.18, seed=26)
        return np.concatenate([outer, tail])
    if name == "OpenAI":
        pts = []
        for k in range(6):
            ang = k * np.pi / 3
            px, py = cx + scale * 0.42 * np.cos(ang), cy + scale * 0.42 * np.sin(ang)
            pts.append(_disc(n // 6, px, py, scale * 0.22, seed=30 + k))
        return np.concatenate(pts)[:n]
    if name == "Docker":
        pts = [_rounded_square(max(1, n // 3), cx - scale * 0.28, cy + scale * 0.05, scale * 0.34, seed=40)]
        for i, (ox, oy) in enumerate([(0.05, -0.28), (0.4, -0.28), (0.05, -0.62), (0.4, -0.62)]):
            pts.append(_rounded_square(max(1, n // 9), cx + scale * ox, cy + scale * oy, scale * 0.28, seed=41 + i))
        allpts = np.concatenate(pts)
        if len(allpts) >= n:
            return allpts[:n]
        reps = int(np.ceil(n / len(allpts)))
        return np.tile(allpts, (reps, 1))[:n]
    if name == "Security":
        return _shield(n, cx, cy, scale * 1.0, scale * 1.3, seed=27)
    if name == "Python":
        top = _rounded_square(n // 2, cx - scale * 0.16, cy - scale * 0.16, scale * 0.62, seed=28)
        bot = _rounded_square(n - n // 2, cx + scale * 0.16, cy + scale * 0.16, scale * 0.62, seed=29)
        return np.concatenate([top, bot])
    return _disc(n, cx, cy, scale * 0.5, seed=99)


def sample_portrait_points(meta, n=900, seed=17):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(meta), size=min(n, len(meta)), replace=len(meta) < n)
    pts = np.array([[meta[i][1], meta[i][2]] for i in idx])
    return pts


def morph_offsets(src, dst):
    """Hungarian assignment minimizing total squared travel distance -
    discrete optimal transport between two equal-size point sets."""
    n = len(src)
    cost = ((src[:, None, :] - dst[None, :, :]) ** 2).sum(-1)
    row, col = linear_sum_assignment(cost)
    order = np.argsort(row)
    return dst[col][order]


def build_traveler_layer(meta, box, colors, n_travelers=150):
    portrait_pts = sample_portrait_points(meta, n_travelers)
    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    scale = min(box["w"], box["h"]) * 0.72

    marks_frac = [round(m, 5) for m in
                  [0, 3.0 / 14.2, 4.3 / 14.2, 6.3 / 14.2, 7.6 / 14.2, 9.6 / 14.2, 10.9 / 14.2, 12.9 / 14.2, 1.0]]

    from animate_builder import LEGS, LEG_DUR

    all_leg_positions = []  # per leg: [portrait, portrait, logo1, logo1, logo2, logo2, logo3, logo3, portrait]
    for leg in LEGS:
        logo_pos = [logo_points(name, cx, cy, scale, n=n_travelers) for name in leg]
        ordered = [portrait_pts, portrait_pts]
        cur = portrait_pts
        for lp in logo_pos:
            nxt = morph_offsets(cur, lp)
            ordered += [nxt, nxt]
            cur = nxt
        back = morph_offsets(cur, portrait_pts)
        ordered.append(back)
        all_leg_positions.append(ordered)

    parts = [f'<g fill="{colors["chrome_a"]}" id="traveler-layer">']
    for i in range(n_travelers):
        vals_by_axis_x, vals_by_axis_y = [], []
        for leg in all_leg_positions:
            for frame in leg:
                p = frame[i]
                vals_by_axis_x.append(round(float(p[0]), 1))
                vals_by_axis_y.append(round(float(p[1]), 1))
        x0, y0 = vals_by_axis_x[0], vals_by_axis_y[0]
        # opacity: hidden during pure-portrait frames (marks 0,1 of each leg), visible during logo dwell
        op_pattern = [0, 0, 1, 1, 1, 1, 1, 1, 0]
        op_vals = ";".join(str(v) for v in (op_pattern * len(LEGS)))
        full_kt = []
        for L in range(len(LEGS)):
            base = L / len(LEGS)
            span = 1 / len(LEGS)
            full_kt += [round(base + f * span, 6) for f in marks_frac]
        full_kt[-1] = 1.0
        kt_str = ";".join(str(v) for v in full_kt)
        x_str = ";".join(str(v) for v in vals_by_axis_x)
        y_str = ";".join(str(v) for v in vals_by_axis_y)
        parts.append(
            f'<circle r="1.4" cx="0" cy="0" opacity="0" transform="translate({x0},{y0})">'
            f'<animateTransform attributeName="transform" type="translate" additive="replace" '
            f'begin="3.2s" dur="{LEG_DUR * len(LEGS)}s" repeatCount="indefinite" calcMode="linear" '
            f'values="{";".join(f"{vx},{vy}" for vx, vy in zip(vals_by_axis_x, vals_by_axis_y))}" '
            f'keyTimes="{kt_str}"/>'
            f'<animate attributeName="opacity" begin="0s" dur="3.2s" values="0;0" fill="remove"/>'
            f'<animate attributeName="opacity" begin="3.2s" dur="{LEG_DUR * len(LEGS)}s" '
            f'repeatCount="indefinite" calcMode="discrete" values="{op_vals}" keyTimes="{kt_str}"/>'
            f'</circle>'
        )
    parts.append("</g>")
    return "".join(parts)
