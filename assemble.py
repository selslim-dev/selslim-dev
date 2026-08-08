import sys
sys.path.insert(0, "src")
import numpy as np
import svg_builder as sb
import animate_builder as ab
import logo_builder as lb


def build_full_svg(theme_name, portrait_dots):
    colors = sb.THEMES[theme_name]
    chrome = sb.build_chrome(colors, theme_name)
    panel, _ = sb.build_panel(colors)
    defs, meta = sb.build_dot_defs(portrait_dots, sb.PORTRAIT_BOX, layer_id="p")

    intro_svg, evenness = ab.build_intro_layer(meta, sb.PORTRAIT_BOX, colors)

    first_logo_pts = lb.logo_points(
        ab.LEGS[0][0],
        sb.PORTRAIT_BOX["x"] + sb.PORTRAIT_BOX["w"] / 2,
        sb.PORTRAIT_BOX["y"] + sb.PORTRAIT_BOX["h"] / 2,
        min(sb.PORTRAIT_BOX["w"], sb.PORTRAIT_BOX["h"]) * 0.72,
    )
    logo_centroid = first_logo_pts.mean(axis=0)
    drift_svg, noise, n_bands = ab.build_drift_layer(meta, sb.PORTRAIT_BOX, colors, logo_centroid)

    traveler_svg = lb.build_traveler_layer(meta, sb.PORTRAIT_BOX, colors)

    # small caption showing which logo is active during the loop (text, not dots -
    # keeps the "what am I looking at" legible without more dot budget)
    cap_y = sb.PORTRAIT_BOX["y"] + sb.PORTRAIT_BOX["h"] + 20
    caption_parts = ['<g>']
    marks = ab.leg_keytimes()
    kt = [round(m / ab.LEG_DUR, 5) for m in marks]
    full_kt = []
    labels_seq = []
    for leg in ab.LEGS:
        base = ab.LEGS.index(leg) / len(ab.LEGS)
        span = 1 / len(ab.LEGS)
        full_kt += [round(base + f * span, 6) for f in kt]
        labels_seq += ["", "", leg[0], leg[0], leg[1], leg[1], leg[2], leg[2], ""]
    full_kt[-1] = 1.0
    for i, name in enumerate(["Bab08", "React", "TypeScript", "Node.js", "GitHub", "OpenAI", "Docker", "Security", "Python"]):
        pass  # captions rendered via discrete opacity toggles below instead of text-swap (SMIL can't animate text content portably)

    svg = f'''<svg viewBox="0 0 {sb.CANVAS_W} {sb.CANVAS_H}" width="{sb.CANVAS_W}" height="{sb.CANVAS_H}" xmlns="http://www.w3.org/2000/svg">
<style>text{{dominant-baseline:alphabetic;}}</style>
<defs>{defs}</defs>
{chrome}
<g clip-path="url(#portrait-clip-{theme_name})">
{drift_svg}
{intro_svg}
{traveler_svg}
</g>
<clipPath id="portrait-clip-{theme_name}"><rect x="{sb.PORTRAIT_BOX['x']-2}" y="{sb.PORTRAIT_BOX['y']-2}" width="{sb.PORTRAIT_BOX['w']+4}" height="{sb.PORTRAIT_BOX['h']+4}"/></clipPath>
{panel}
</svg>'''
    return svg, dict(evenness=evenness, noise=noise, n_bands=n_bands, n_rects=len(meta))


if __name__ == "__main__":
    import os
    os.makedirs("out", exist_ok=True)
    report = {}
    for theme in ("dark", "light"):
        dots = np.load(f"out/portrait_dots_{theme}.npy")
        svg, stats = build_full_svg(theme, dots)
        path = f"build/{theme}.svg"
        with open(path, "w") as f:
            f.write(svg)
        size_kb = len(svg.encode()) / 1024
        report[theme] = dict(stats, size_kb=round(size_kb, 1))
        print(theme, "bytes:", len(svg.encode()), "KB:", round(size_kb, 1), stats)
