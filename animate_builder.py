import numpy as np
from scipy.optimize import linear_sum_assignment

RNG_SEED = 7

# --- intro: 60 spatially-interleaved groups -------------------------------

def assign_intro_groups(meta, n_groups=60, seed=RNG_SEED):
    idx = np.arange(len(meta))
    rng = np.random.default_rng(seed)
    rng.shuffle(idx)
    return {meta[i][0]: int(g % n_groups) for g, i in zip(np.arange(len(idx)) % n_groups, idx)}


def evenness_metric(meta, group_of, box, n_groups=60, n_cells=4, duration=3.2):
    """Coefficient of variation of per-cell reveal fraction, averaged over
    checkpoints across the intro duration. Low = groups are spatially
    scattered (interleaved); high = groups are spatially clumped (wipe-like)."""
    xs = np.array([m[1] for m in meta])
    ys = np.array([m[2] for m in meta])
    gids = np.array([group_of[m[0]] for m in meta])
    cell_x = np.clip(((xs - box["x"]) / box["w"] * n_cells).astype(int), 0, n_cells - 1)
    cell_y = np.clip(((ys - box["y"]) / box["h"] * n_cells).astype(int), 0, n_cells - 1)
    cell_id = cell_y * n_cells + cell_x
    n_cell_total = n_cells * n_cells

    cell_counts = np.bincount(cell_id, minlength=n_cell_total).astype(float)
    valid = cell_counts > 0

    group_start = {g: g / n_groups * duration for g in range(n_groups)}
    dot_start = np.array([group_start[g] for g in gids])

    cvs = []
    for t in np.linspace(duration / n_groups, duration, 24):
        revealed = dot_start <= t
        rev_counts = np.bincount(cell_id[revealed], minlength=n_cell_total).astype(float)
        frac = np.divide(rev_counts, cell_counts, out=np.zeros_like(rev_counts), where=cell_counts > 0)
        f = frac[valid]
        if f.mean() > 0:
            cvs.append(f.std() / (f.mean() + 1e-9))
    return float(np.mean(cvs))


def build_intro_layer(meta, box, colors, duration=3.2, n_groups=60):
    groups = assign_intro_groups(meta, n_groups)
    by_group = {}
    for rid, cx, cy in meta:
        by_group.setdefault(groups[rid], []).append(rid)

    parts = [f'<g fill="{colors["portrait_hue"]}" shape-rendering="crispEdges" id="intro-layer">']
    step = duration / n_groups
    for g in range(n_groups):
        ids = by_group.get(g, [])
        if not ids:
            continue
        begin = round(g * step, 3)
        gdur = round(step * 2.4, 3)  # slight overlap between consecutive groups
        uses = "".join(f'<use href="#{rid}"/>' for rid in ids)
        parts.append(
            f'<g opacity="0">'
            f'<animate attributeName="opacity" values="0;1" begin="{begin}s" dur="{gdur}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'<animate attributeName="opacity" values="1;0" begin="{duration}s" dur="0.01s" fill="freeze"/>'
            f'{uses}</g>'
        )
    parts.append("</g>")
    ev = evenness_metric(meta, groups, box, n_groups)
    return "".join(parts), ev


# --- drift bands: ~94 spatial bands, portrait <-> dissolve toward logo ----

def assign_drift_bands(meta, box, target=94, seed=11):
    n_side = max(1, round(target ** 0.5))
    cols = n_side
    rows = max(1, round(target / cols))
    rng = np.random.default_rng(seed)
    band_of = {}
    buckets = {}
    for rid, cx, cy in meta:
        cxi = min(cols - 1, int((cx - box["x"]) / box["w"] * cols))
        cyi = min(rows - 1, int((cy - box["y"]) / box["h"] * rows))
        band = cyi * cols + cxi
        band_of[rid] = band
        buckets.setdefault(band, []).append(rid)
    return band_of, buckets


def straight_boundary_metric(buckets, meta_by_id, box, sigma=4, seed=13):
    """Approximate how 'organic' vs 'grid-like' the per-dot noise makes the
    band boundaries. For each band, jitter member centroids by N(0,sigma)
    and measure the residual alignment to the band's axis-aligned bbox
    edges (low = boundary no longer reads as a straight grid line)."""
    rng = np.random.default_rng(seed)
    scores = []
    for band, ids in buckets.items():
        if len(ids) < 4:
            continue
        pts = np.array([meta_by_id[i][1:] for i in ids])
        jitter = rng.normal(0, sigma, pts.shape)
        jp = pts + jitter
        x0, y0 = pts.min(axis=0)
        x1, y1 = pts.max(axis=0)
        edge_dist = np.minimum.reduce([
            np.abs(jp[:, 0] - x0), np.abs(jp[:, 0] - x1),
            np.abs(jp[:, 1] - y0), np.abs(jp[:, 1] - y1),
        ])
        span = max(1.0, max(x1 - x0, y1 - y0))
        near_edge = edge_dist < (span * 0.04)
        scores.append(near_edge.mean())
    return float(np.mean(scores)) if scores else 0.0


LEGS = [
    ["Bab08", "React", "TypeScript"],
    ["Node.js", "GitHub", "OpenAI"],
    ["Docker", "Security", "Python"],
]
T_PORTRAIT, T_LOGO, T_TRANS = 3.0, 2.0, 1.3
LEG_DUR = T_PORTRAIT + 3 * T_LOGO + 4 * T_TRANS  # 14.2s
CYCLE_DUR = LEG_DUR * len(LEGS)  # 42.6s


def leg_keytimes():
    """Boundary offsets (seconds, within one 14.2s leg) for:
    portrait_rest_end, ->logo1 arrive, logo1_end, ->logo2 arrive,
    logo2_end, ->logo3 arrive, logo3_end, ->portrait arrive(=leg end)."""
    t = 0.0
    marks = [t]
    t += T_PORTRAIT; marks.append(t)          # end portrait rest
    t += T_TRANS; marks.append(t)             # arrive logo1
    t += T_LOGO; marks.append(t)              # end logo1
    t += T_TRANS; marks.append(t)             # arrive logo2
    t += T_LOGO; marks.append(t)              # end logo2
    t += T_TRANS; marks.append(t)             # arrive logo3
    t += T_LOGO; marks.append(t)              # end logo3
    t += T_TRANS; marks.append(t)             # arrive back at portrait (== LEG_DUR)
    return marks


def build_drift_layer(meta, box, colors, logo_centroid, intro_duration=3.2):
    band_of, buckets = assign_drift_bands(meta, box)
    meta_by_id = {rid: (rid, cx, cy) for rid, cx, cy in meta}
    lx, ly = logo_centroid
    marks = leg_keytimes()  # 9 marks across one 14.2s leg
    kt = [round(m / LEG_DUR, 5) for m in marks]

    parts = [f'<g fill="{colors["portrait_hue"]}" shape-rendering="crispEdges" id="drift-layer">']
    rng = np.random.default_rng(23)
    for band, ids in buckets.items():
        pts = np.array([meta_by_id[i][1:] for i in ids])
        cx, cy = pts.mean(axis=0)
        dx, dy = (lx - cx) * 0.42, (ly - cy) * 0.42
        nx, ny = rng.normal(0, 4), rng.normal(0, 4)
        dx, dy = round(dx + nx, 1), round(dy + ny, 1)

        # opacity: 1 during portrait rest, 0 while drifted/dissolved into logos, 1 on return
        op_vals = ";".join(["1", "1", "0", "0", "0", "0", "0", "0", "1"])
        tr_vals = ";".join([
            "0,0", "0,0", f"{dx},{dy}", f"{dx},{dy}", f"{dx},{dy}",
            f"{dx},{dy}", f"{dx},{dy}", f"{dx},{dy}", "0,0",
        ])
        kt_str = ";".join(str(x) for x in kt)
        uses = "".join(f'<use href="#{rid}"/>' for rid in ids)
        parts.append(
            f'<g opacity="1">'
            f'<animate attributeName="opacity" begin="0s" dur="{intro_duration}s" values="0;0" fill="remove"/>'
            f'<animateTransform attributeName="transform" type="translate" attributeType="XML" '
            f'begin="{intro_duration}s" dur="{LEG_DUR}s" repeatCount="indefinite" '
            f'values="{tr_vals}" keyTimes="{kt_str}" calcMode="linear"/>'
            f'<animate attributeName="opacity" attributeType="XML" '
            f'begin="{intro_duration}s" dur="{LEG_DUR}s" repeatCount="indefinite" '
            f'values="{op_vals}" keyTimes="{kt_str}" calcMode="discrete"/>'
            f'{uses}</g>'
        )
    parts.append("</g>")
    noise = straight_boundary_metric(buckets, meta_by_id, box)
    return "".join(parts), noise, len(buckets)
