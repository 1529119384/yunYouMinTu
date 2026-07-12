# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

360° panoramic viewer web application using Pannellum 2.5.7. Displays equirectangular panorama images as interactive 360° views with scene navigation. UI is in Chinese (zh-CN).

## Commands

```bash
# Start the server (zero dependencies, pure Node.js)
node server.js
# or: npm start

# Generate multires cubemap tiles (official Pannellum tool via Hugin's nona)
# Requires: Hugin installed at D:\soft\Hugin (nona.exe)
cd pannellum-2.5.7/utils/multires
python generate.py -n "D:/soft/Hugin/bin/nona.exe" -o "../../public/tiles/sceneN" -s 512 "../../public/images/sceneN.jpg"
```

Server runs on `http://localhost:3000` (or `PORT` env var). No build step, no tests, no linter.

## Architecture

Shared code pattern — two viewer pages share `style.css` and `app.js`:

- **`public/style.css`** — All shared CSS (scene nav, loading overlay, hotspots, auto-rotate button)
- **`public/app.js`** — Shared logic: `initViewer(config)` handles viewer creation, scene switching, nav, auto-rotate, loading. Hotspots are auto-generated from `sceneOrder` array
- **`public/index.html`** — Multires viewer. Only defines scene configs with `type: 'multires'` and `multiRes` tile paths
- **`public/simple.html`** — Equirectangular viewer. Only defines scene configs with `type: 'equirectangular'` and image paths. Has a `.badge` element
- **`server.js`** — Zero-dependency Node.js static file server. Serves `public/` with directory traversal protection
- **`public/vendor/pannellum.js`** — Pannellum 2.5.7 (vendored, not CDN)
- **`pannellum-2.5.7/utils/multires/generate.py`** — Official Pannellum tile generation script (requires Hugin's `nona`)
- **`docs/pannellum-reference.md`** — Pannellum configuration reference, API docs, and cubemap coordinate mapping

## Adding a New Scene

1. Place the equirectangular JPG as `public/images/sceneN.jpg`
2. Generate tiles using the official script (see Commands above)
3. Add the scene config to both `index.html` (multires) and `simple.html` (equirectangular)
4. Add the scene ID to the `sceneOrder` array in both HTML files (controls navigation order and hotspot generation)

## Tile Structure (Official Pannellum Format)

Output: `public/tiles/{scene}/{level}/{face}{row}_{col}.jpg`

```json
{
    "path": "/%l/%s%y_%x",
    "fallbackPath": "/fallback/%s",
    "extension": "jpg",
    "tileResolution": 512,
    "maxLevel": 4,
    "cubeResolution": 3784
}
```

Path template: `%l`=level, `%s`=face (f/r/b/l/u/d), `%y`=row, `%x`=col. Official naming: `f0_0.jpg` (face + row + underscore + col).

## Pannellum Multires Gotchas

- `firstScene` is required or the viewer won't create a canvas
- The `load` event may not fire in multires mode; both viewers use `setTimeout` fallback (3s for multires, 10s for simple)
- **Do not write custom equirectangular-to-cubemap conversion** — use Hugin's `nona` via the official `generate.py` script. Custom implementations consistently get face directions wrong
- `config.json` values (maxLevel, cubeResolution) must match what's hardcoded in `index.html`
- The official tile path template is `"/%l/%s%y_%x"`, NOT `"/%s/%l/%y/%x"`
