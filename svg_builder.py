import numpy as np

CANVAS_W, CANVAS_H = 1180, 610
TITLEBAR_H = 36
CONTENT_TOP = TITLEBAR_H
CONTENT_BOTTOM = CANVAS_H - 14

PORTRAIT_BOX = dict(x=40, y=CONTENT_TOP + 34, w=390, h=442)  # render box for the 300x340 grid
PANEL_X = 468
PANEL_RIGHT = 1150
ROW_SPACING = 23
ROW_FONT = 14
HEADER_FONT = 13
LIVE_FONT = 12
PILL_FONT = 14
LABEL_COL_CHARS = 18  # label + dot padding, in monospace character units

THEMES = {
    "dark": dict(
        bg="#0A101F", panel_bg="#0D1424", border="#1E2A44",
        portrait_hue="#A78BFA", chrome_a="#22D3EE", chrome_b="#0891B2",
        accent="#10B981", label="#5B6785", value="#E7E9F5", header="#22D3EE",
        live_red="#EF4444", pill_bg="#151F35", pill_text="#22D3EE",
        titlebar_bg="#0D1424", dot_leader="#2A3552",
    ),
    "light": dict(
        bg="#F7F7FB", panel_bg="#FFFFFF", border="#E2E4EE",
        portrait_hue="#7C3AED", chrome_a="#0891B2", chrome_b="#0E7490",
        accent="#059669", label="#8A90A6", value="#161A2B", header="#0891B2",
        live_red="#DC2626", pill_bg="#EEF2FF", pill_text="#0891B2",
        titlebar_bg="#EFEFF5", dot_leader="#D7D9E6",
    ),
}

ROWS = [
    [("Subject", "Selmani Slim"), ("Role", "Full-Stack Developer"),
     ("Specialization", "AI + Secure Software"), ("Origin", "Algiers, Algeria"),
     ("Education", "USTHB Computer Science"), ("Experience", "Bab08 Intern"),
     ("Status", "Building / Learning / Shipping")],
    [("Current.Project", "Bab08 Website Modernization"), ("AI.Focus", "LLMs + Agents + Automation"),
     ("Security.Focus", "Secure Web Applications"), ("ToolChain", "Claude / Copilot / Git / Figma")],
    [("Core.Lang", "JavaScript \u00b7 TypeScript \u00b7 Python \u00b7 C"),
     ("Core.Frontend", "React \u00b7 Next.js \u00b7 Tailwind"),
     ("Core.Backend", "Node.js \u00b7 NestJS"), ("Core.Database", "MongoDB \u00b7 SQL"),
     ("Core.Infra", "Git \u00b7 GitHub Actions \u00b7 Docker")],
    [("Grid.Mail", "selmanislim8@gmail.com"),
     ("Grid.Portfolio", "selslim-devportfolio-76aeb7.netlify.app"),
     ("Grid.LinkedIn", "linkedin.com/in/slim-selmani-a1946a3a7"),
     ("Grid.GitHub", "github.com/selslim-dev")],
]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_dot_defs(dots, box, layer_id, grid_w=300, grid_h=340, dot_size=1.27):
    """Merges dots into axis-aligned rectangles (row runs, then vertical
    merge of matching runs) and defines each ONCE in a <defs> block with
    a unique id. Returns (defs_svg, list of (id, cx, cy) in render-px
    space) so multiple independent animated groupings can reference the
    same geometry via <use> without duplicating rect data."""
    if len(dots) == 0:
        return "", []
    sx = box["w"] / grid_w
    sy = box["h"] / grid_h
    gap = sx - dot_size if sx > dot_size else 0

    by_row = {}
    for gx, gy in dots:
        by_row.setdefault(int(gy), []).append(int(gx))

    def row_runs(gy):
        xs = sorted(by_row.get(gy, []))
        if not xs:
            return []
        runs, start, prev = [], xs[0], xs[0]
        for gx in xs[1:]:
            if gx == prev + 1:
                prev = gx
                continue
            runs.append((start, prev))
            start = prev = gx
        runs.append((start, prev))
        return runs

    rects = []
    open_rects = {}
    for gy in range(grid_h + 1):
        current = set(row_runs(gy)) if gy < grid_h else set()
        for key in list(open_rects):
            if key not in current:
                rects.append((key[0], key[1], open_rects[key], gy - 1))
                del open_rects[key]
        for key in current:
            if key not in open_rects:
                open_rects[key] = gy

    defs_parts = []
    meta = []
    for i, (gx0, gx1, gy0, gy1) in enumerate(rects):
        x = round(box["x"] + gx0 * sx)
        y = round(box["y"] + gy0 * sy)
        w = max(1, round((gx1 - gx0 + 1) * sx - gap))
        h = max(1, round((gy1 - gy0 + 1) * sy - gap))
        rid = f"{layer_id}-{i}"
        defs_parts.append(f'<rect id="{rid}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
        meta.append((rid, x + w / 2, y + h / 2))
    return "".join(defs_parts), meta


def row_text_svg(label, value, x, y, colors, content_chars=48):
    pad = max(1, LABEL_COL_CHARS - len(label))
    row_str = f"{label} {'.' * pad} {value}"
    row_str = row_str[:content_chars]
    return (f'<text x="{x}" y="{y}" font-family="\'JetBrains Mono\',\'Courier New\',monospace" '
            f'font-size="{ROW_FONT}" fill="{colors["value"]}" textLength="{content_chars * 7.15:.1f}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">'
            f'<tspan fill="{colors["label"]}">{esc(label)}</tspan>'
            f'<tspan fill="{colors["dot_leader"]}"> {"." * pad} </tspan>'
            f'<tspan fill="{colors["value"]}">{esc(value)}</tspan></text>')


def build_panel(colors):
    out = []
    header_y = CONTENT_TOP + 30
    out.append(f'<text x="{PANEL_X}" y="{header_y}" font-family="\'JetBrains Mono\',monospace" '
                f'font-size="{HEADER_FONT}" font-weight="700" fill="{colors["header"]}" '
                f'letter-spacing="2">SYSTEM.INFO</text>')

    # pulsing LIVE badge, top-right of panel
    badge_cx = PANEL_RIGHT - 78
    badge_cy = header_y - 5
    out.append(f'<g>'
                f'<circle cx="{badge_cx - 12}" cy="{badge_cy}" r="4" fill="{colors["live_red"]}">'
                f'<animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/>'
                f'</circle>'
                f'<text x="{badge_cx}" y="{badge_cy + 4}" font-family="\'JetBrains Mono\',monospace" '
                f'font-size="{LIVE_FONT}" font-weight="700" fill="{colors["live_red"]}" '
                f'letter-spacing="1.5">LIVE</text></g>')

    # username pill, top-right corner
    pill_w = 150
    pill_x = PANEL_RIGHT - pill_w
    pill_y = header_y + 12
    out.append(f'<rect x="{pill_x}" y="{pill_y}" width="{pill_w}" height="22" rx="11" '
                f'fill="{colors["pill_bg"]}" stroke="{colors["chrome_b"]}" stroke-width="1"/>')
    out.append(f'<text x="{pill_x + pill_w/2}" y="{pill_y + 15}" text-anchor="middle" '
                f'font-family="\'JetBrains Mono\',monospace" font-size="{PILL_FONT-2}" '
                f'fill="{colors["pill_text"]}">@selslim-dev</text>')

    y = header_y + 46
    for block_i, block in enumerate(ROWS):
        for label, value in block:
            out.append(row_text_svg(label, value, PANEL_X, y, colors))
            y += ROW_SPACING
        y += 13  # gap between blocks

    return "\n".join(out), y


def build_chrome(colors, theme_name):
    out = []
    out.append(f'<rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" rx="14" fill="{colors["bg"]}"/>')
    # title bar
    out.append(f'<path d="M0,14 a14,14 0 0 1 14,-14 h{CANVAS_W-28} a14,14 0 0 1 14,14 v{TITLEBAR_H-14} '
                f'h-{CANVAS_W} z" fill="{colors["titlebar_bg"]}"/>')
    for i, c in enumerate(["#EF4444", "#F59E0B", "#10B981"]):
        out.append(f'<circle cx="{22 + i*18}" cy="{TITLEBAR_H/2}" r="5" fill="{c}" opacity="0.85"/>')
    out.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" text-anchor="middle" '
                f'font-family="\'JetBrains Mono\',monospace" font-size="12.5" fill="{colors["label"]}">'
                f'profile.sh --live</text>')
    out.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" '
                f'stroke="{colors["border"]}" stroke-width="1"/>')
    # portrait frame
    pb = PORTRAIT_BOX
    out.append(f'<text x="{pb["x"]}" y="{pb["y"] - 14}" font-family="\'JetBrains Mono\',monospace" '
                f'font-size="{HEADER_FONT}" font-weight="700" fill="{colors["header"]}" '
                f'letter-spacing="2">VISUAL.MAP</text>')
    out.append(f'<rect x="{pb["x"]-1}" y="{pb["y"]-1}" width="{pb["w"]+2}" height="{pb["h"]+2}" '
                f'fill="none" stroke="{colors["chrome_b"]}" stroke-width="1.4" rx="4"/>')
    # corner ticks for a "scan frame" feel, using chrome_a
    tick = 14
    for cx, cy, dx, dy in [(pb["x"], pb["y"], 1, 1), (pb["x"]+pb["w"], pb["y"], -1, 1),
                            (pb["x"], pb["y"]+pb["h"], 1, -1), (pb["x"]+pb["w"], pb["y"]+pb["h"], -1, -1)]:
        out.append(f'<path d="M{cx},{cy+dy*tick} L{cx},{cy} L{cx+dx*tick},{cy}" '
                    f'fill="none" stroke="{colors["chrome_a"]}" stroke-width="2"/>')
    # panel/portrait divider
    out.append(f'<line x1="{PANEL_X-24}" y1="{CONTENT_TOP+20}" x2="{PANEL_X-24}" y2="{CONTENT_BOTTOM}" '
                f'stroke="{colors["border"]}" stroke-width="1"/>')
    return "\n".join(out)


def build_static_svg(theme_name, portrait_dots):
    colors = THEMES[theme_name]
    chrome = build_chrome(colors, theme_name)
    panel, _ = build_panel(colors)
    defs, meta = build_dot_defs(portrait_dots, PORTRAIT_BOX, layer_id="p")
    inline = defs.replace('<rect id="p-', '<rect data-id="p-')
    portrait_layer = f'<g fill="{colors["portrait_hue"]}" shape-rendering="crispEdges">{inline}</g>'

    svg = f'''<svg viewBox="0 0 {CANVAS_W} {CANVAS_H}" width="{CANVAS_W}" height="{CANVAS_H}" xmlns="http://www.w3.org/2000/svg">
<style>text{{dominant-baseline:alphabetic;}}</style>
{chrome}
<g id="portrait-static">{portrait_layer}</g>
{panel}
</svg>'''
    return svg


if __name__ == "__main__":
    for theme in ("dark", "light"):
        dots = np.load(f"out/portrait_dots_{theme}.npy")
        svg = build_static_svg(theme, dots)
        with open(f"build/static_{theme}.svg", "w") as f:
            f.write(svg)
        print(theme, "svg bytes:", len(svg.encode()))
