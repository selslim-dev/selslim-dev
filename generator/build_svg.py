import json, math

CANVAS_W, CANVAS_H = 1180, 610
TITLEBAR_H = 40

PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 24, 56, 440, 530
RIGHT_X, RIGHT_W = 488, CANVAS_W - 488 - 24

INTRO_DUR = 3.2
N_GROUPS = 60
TRANS = 0.65      # per-edge crossfade (spec's "1.3s transition" split evenly in/out)
PORTRAIT_HOLD = 3.0
LOGO_HOLD = 2.0
LOGO_ORDER = ["bab08", "react", "typescript", "node", "github", "openai", "docker", "security", "python"]
LOOP_DUR = round(PORTRAIT_HOLD + len(LOGO_ORDER) * (TRANS + LOGO_HOLD) + TRANS, 3)

THEMES = {
    "dark": dict(
        bg="#0A101F", panel="#111827", panel_border="#232B3D",
        portrait="#A78BFA", chrome="#22D3EE", chrome_dim="#0891B2",
        accent="#10B981", live="#F43F5E",
        text="#E5E9F5", text_dim="#64748B", text_faint="#3A445C",
        pill_bg="#A78BFA", pill_text="#0A101F",
        title_bar="#0D1424", traffic=("#F43F5E", "#FBBF24", "#10B981"),
    ),
    "light": dict(
        bg="#F8FAFC", panel="#FFFFFF", panel_border="#E2E8F0",
        portrait="#7C3AED", chrome="#0891B2", chrome_dim="#0E7490",
        accent="#059669", live="#DC2626",
        text="#0F172A", text_dim="#64748B", text_faint="#94A3B8",
        pill_bg="#7C3AED", pill_text="#FFFFFF",
        title_bar="#EEF1F6", traffic=("#DC2626", "#D97706", "#059669"),
    ),
}

ROW_GROUPS = [
    [("Subject", "Selmani Slim"), ("Role", "Full-Stack Developer"), ("Specialization", "AI + Secure Software"),
     ("Origin", "Algiers, Algeria"), ("Education", "USTHB Computer Science"), ("Experience", "Bab08 Intern"),
     ("Status", "Building / Learning / Shipping")],
    [("Current.Project", "Bab08 Website Modernization"), ("AI.Focus", "LLMs + Agents + Automation"),
     ("Security.Focus", "Secure Web Applications"), ("ToolChain", "Claude / Copilot / Git / Figma")],
    [("Core.Lang", "JavaScript . TypeScript . Python . C"), ("Core.Frontend", "React . Next.js . Tailwind"),
     ("Core.Backend", "Node.js . NestJS"), ("Core.Database", "MongoDB . SQL"),
     ("Core.Infra", "Git . GitHub Actions . Docker")],
    [("Grid.Mail", "selmanislim8@gmail.com"), ("Grid.Portfolio", "selslim-devportfolio-76aeb7.netlify.app"),
     ("Grid.LinkedIn", "linkedin.com/in/slim-selmani-a1946a3a7"), ("Grid.GitHub", "github.com/selslim-dev")],
]

FONT = "'JetBrains Mono','Fira Code',Consolas,Menlo,monospace"
ROW_COLS = 58  # fixed character budget so textLength keeps every row identically wide


def dotted_row(label, value, cols=ROW_COLS):
    pad = cols - len(label) - len(value) - 2
    pad = max(pad, 3)
    return f"{label} {'.' * pad} {value}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_portrait_layer(dots, theme, ox, oy, scale, dot_px, intro_begin=0.0):
    groups = {}
    for (x, y), g in zip(dots["coords"], dots["groups"]):
        groups.setdefault(g, []).append((x, y))
    parts = []
    stagger = INTRO_DUR / N_GROUPS
    for g in range(N_GROUPS):
        pts = groups.get(g, [])
        if not pts:
            continue
        begin = intro_begin + g * stagger
        rects = "".join(
            f'<rect x="{ox+px*scale:.2f}" y="{oy+py*scale:.2f}" width="{dot_px:.2f}" height="{dot_px:.2f}"/>'
            for px, py in pts
        )
        parts.append(
            f'<g fill="{theme["portrait"]}" opacity="0" shape-rendering="crispEdges">'
            f'{rects}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.3f}s" dur="0.5s" '
            f'fill="freeze" calcMode="spline" keySplines="0.2 0 0.2 1"/>'
            f'</g>'
        )
    return "".join(parts)


def portrait_layer_opacity_anim():
    L = LOOP_DUR
    t0 = PORTRAIT_HOLD
    t1 = t0 + TRANS
    t2 = L - TRANS
    kt = [0, t0 / L, t1 / L, t2 / L, 1]
    vals = [1, 1, 0, 0, 1]
    return (
        f'<animate attributeName="opacity" begin="{INTRO_DUR:.2f}s" dur="{L:.3f}s" '
        f'repeatCount="indefinite" calcMode="linear" '
        f'keyTimes="{";".join(f"{v:.4f}" for v in kt)}" values="{";".join(str(v) for v in vals)}"/>'
    )


def logo_layer_opacity_anim(i):
    L = LOOP_DUR
    start = PORTRAIT_HOLD + i * (TRANS + LOGO_HOLD)
    full_in = start + TRANS
    fade_out = full_in + LOGO_HOLD
    full_out = min(fade_out + TRANS, L)
    kt = [0, start / L, full_in / L, fade_out / L, full_out / L]
    vals = [0, 0, 1, 1, 0]
    if full_out / L < 1:
        kt.append(1); vals.append(0)
    return (
        f'<animate attributeName="opacity" begin="{INTRO_DUR:.2f}s" dur="{L:.3f}s" '
        f'repeatCount="indefinite" calcMode="linear" '
        f'keyTimes="{";".join(f"{v:.4f}" for v in kt)}" values="{";".join(str(v) for v in vals)}"/>'
    )


def build_logo_layers(logos, theme, ox, oy, scale, dot_px):
    parts = []
    for i, name in enumerate(LOGO_ORDER):
        data = logos[name]
        rects = "".join(
            f'<rect x="{ox+px*scale:.2f}" y="{oy+py*scale:.2f}" width="{dot_px:.2f}" height="{dot_px:.2f}"/>'
            for px, py in data["coords"]
        )
        parts.append(
            f'<g fill="{theme["chrome"]}" opacity="0" shape-rendering="crispEdges">'
            f'{rects}{logo_layer_opacity_anim(i)}</g>'
        )
    return "".join(parts)


def build_system_info(theme):
    x0 = RIGHT_X + 28
    y = PANEL_Y + 40
    out = [f'<text x="{x0}" y="{PANEL_Y+26}" font-family="{FONT}" font-size="13" '
           f'font-weight="700" letter-spacing="2" fill="{theme["chrome"]}">SYSTEM.INFO</text>']
    row_w = RIGHT_W - 56
    for gi, group in enumerate(ROW_GROUPS):
        for label, value in group:
            txt = esc(dotted_row(label, value))
            out.append(
                f'<text x="{x0}" y="{y}" font-family="{FONT}" font-size="14" '
                f'textLength="{row_w}" lengthAdjust="spacingAndGlyphs" '
                f'fill="{theme["text_dim"]}"><tspan fill="{theme["text"]}">{esc(label)}</tspan>'
                f'{esc(" " + "." * 2)}<tspan fill="{theme["text_faint"]}">{esc("." * max(3, ROW_COLS-len(label)-len(value)-2))}</tspan> '
                f'<tspan fill="{theme["text"]}">{esc(value)}</tspan></text>'
            )
            y += 23
        if gi < len(ROW_GROUPS) - 1:
            y += 6
            out.append(f'<line x1="{x0}" y1="{y}" x2="{x0+row_w}" y2="{y}" stroke="{theme["panel_border"]}" stroke-width="1" stroke-dasharray="1,3"/>')
            y += 12
    return "".join(out)


def build_svg(mode):
    theme = THEMES[mode]
    dots = json.load(open(f"/home/claude/profile/build/dots_{mode}.json"))
    logos = json.load(open("/home/claude/profile/build/logos.json"))

    inner_pad = 16
    header_h = 40
    avail_w = PANEL_W - 2 * inner_pad
    avail_h = PANEL_H - header_h - inner_pad
    scale = min(avail_w / dots["grid_w"], avail_h / dots["grid_h"])
    pw, ph = dots["grid_w"] * scale, dots["grid_h"] * scale
    ox = PANEL_X + (PANEL_W - pw) / 2
    oy = PANEL_Y + header_h + (avail_h - ph) / 2
    dot_px = scale * 0.82

    lscale = 5.2
    lg = logos[LOGO_ORDER[0]]["grid"]
    lw, lh = lg * lscale, lg * lscale
    lox = PANEL_X + (PANEL_W - lw) / 2
    loy = PANEL_Y + header_h + (avail_h - lh) / 2
    ldot = lscale * 0.7

    portrait_svg = build_portrait_layer(dots, theme, ox, oy, scale, dot_px)
    logos_svg = build_logo_layers(logos, theme, lox, loy, lscale, ldot)
    sysinfo_svg = build_system_info(theme)

    traffic = theme["traffic"]
    handle = "selslim-dev"

    svg = f'''<svg viewBox="0 0 {CANVAS_W} {CANVAS_H}" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">
<defs>
  <clipPath id="winclip-{mode}"><rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" rx="14"/></clipPath>
  <clipPath id="portraitclip-{mode}"><rect x="{PANEL_X}" y="{PANEL_Y+header_h}" width="{PANEL_W}" height="{PANEL_H-header_h}" rx="8"/></clipPath>
</defs>
<g clip-path="url(#winclip-{mode})">
  <rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" fill="{theme["bg"]}"/>
  <rect x="0" y="0" width="{CANVAS_W}" height="{TITLEBAR_H}" fill="{theme["title_bar"]}"/>
  <line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{theme["panel_border"]}" stroke-width="1"/>
  <circle cx="22" cy="{TITLEBAR_H/2}" r="6" fill="{traffic[0]}"/>
  <circle cx="42" cy="{TITLEBAR_H/2}" r="6" fill="{traffic[1]}"/>
  <circle cx="62" cy="{TITLEBAR_H/2}" r="6" fill="{traffic[2]}"/>
  <text x="88" y="{TITLEBAR_H/2+5}" font-size="14" fill="{theme["text_dim"]}">profile.sh --live</text>

  <g>
    <circle cx="{CANVAS_W-330}" cy="{TITLEBAR_H/2}" r="5" fill="{theme["live"]}">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <text x="{CANVAS_W-318}" y="{TITLEBAR_H/2+4}" font-size="12" font-weight="700" letter-spacing="1.5" fill="{theme["live"]}">LIVE</text>
  </g>
  <g>
    <rect x="{CANVAS_W-270}" y="9" width="246" height="22" rx="11" fill="{theme["pill_bg"]}"/>
    <text x="{CANVAS_W-270+123}" y="24" font-size="14" font-weight="600" text-anchor="middle" fill="{theme["pill_text"]}">@{handle}</text>
  </g>

  <rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="10" fill="{theme["panel"]}" stroke="{theme["panel_border"]}"/>
  <text x="{PANEL_X+16}" y="{PANEL_Y+26}" font-size="13" font-weight="700" letter-spacing="2" fill="{theme["chrome"]}">VISUAL.MAP</text>
  <g clip-path="url(#portraitclip-{mode})">
    {portrait_svg}
    {logos_svg}
  </g>

  <rect x="{RIGHT_X}" y="{PANEL_Y}" width="{RIGHT_W}" height="{PANEL_H}" rx="10" fill="{theme["panel"]}" stroke="{theme["panel_border"]}"/>
  {sysinfo_svg}
</g>
</svg>'''
    return svg


import os
os.makedirs("/home/claude/profile/out", exist_ok=True)
for mode in ("dark", "light"):
    svg = build_svg(mode)
    path = f"/home/claude/profile/out/{mode}.svg"
    with open(path, "w") as f:
        f.write(svg)
    size_kb = os.path.getsize(path) / 1024
    print(mode, "loop_dur", LOOP_DUR, "size_kb", round(size_kb, 1))
