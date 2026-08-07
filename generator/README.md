# Generator (source of truth)

The exported SVGs in `../assets/` are a *build artifact*, not the master asset.
Re-run this pipeline whenever the portrait, palette, or logo sequence changes.

```
python3 portrait.py     # crops + dithers source.png -> dots_dark.json / dots_light.json
python3 logos.py        # renders the 9 dot-icon logos -> logos.json
python3 build_svg.py    # assembles ../assets/dark.svg and ../assets/light.svg
```

Requires: `pillow`, `numpy`, `scipy` (`pip install pillow numpy scipy --break-system-packages`).

- `source.png` — the original head-and-shoulders photo used for the portrait.
- `dots_dark.json` / `dots_light.json` — dithered dot coordinates + intro fade-group
  assignments + measured evenness/ink metrics for each theme.
- `logos.json` — dot coordinates for the 9 loop-animation icons.
- Loop timing constants (`PORTRAIT_HOLD`, `TRANS`, `LOGO_HOLD`, `LOGO_ORDER`) live at
  the top of `build_svg.py` — tune these and re-run to change the animation pacing.
