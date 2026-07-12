# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

makeTiles is a Python FastAPI tile generation service with a web management UI. It converts large images into map tile pyramids using GDAL's `gdal2tiles`.

## Commands

### Environment setup (conda)
```bash
conda create -n maketiles python=3.12 -y
conda activate maketiles
conda install -c conda-forge gdal -y
pip install fastapi uvicorn pillow python-multipart
```

### Run the server
```bash
conda activate maketiles
python run.py
```

### Verify GDAL works
```bash
python -m osgeo_utils.gdal2tiles --help
```

## Architecture

- **`tile_engine.py`**: Pure logic module — tile computation, image validation, gdal2tiles invocation, thumbnail generation, manifest generation. Auto-determines tile size based on image dimensions (256/512/1024/2048).
- **`settings.py`**: Config hot-reload — reads/writes `app/data/config.json`, provides `get_settings()` / `update_settings()`.
- **`main.py`**: FastAPI app (~550 lines) — routes, job management, SSRF protection, static file serving.
- **`app/admin/`**: Web management UI (vanilla HTML/CSS/JS + local Leaflet).
- **`app/data/`**: Runtime data (images, tiles, manifests, thumbnails, config).

### Auto tile size
Tile size is determined by image dimensions, not user configuration:
- ≤ 4096px → 256
- ≤ 16384px → 512
- ≤ 65536px → 1024
- > 65536px → 2048

### API Endpoints
```
GET    /health                  → {"ok": true}
POST   /api/tiles               → { jobId, status }       Create tile job (202)
GET    /api/tiles               → { total, items }        List tiles (paginated, searchable)
GET    /api/tiles/jobs/{id}     → { jobId, status, ... }  Poll job status
GET    /api/tiles/{id}/manifest → TileManifest            Get manifest
PATCH  /api/tiles/{id}          → TileManifest            Update note
DELETE /api/tiles/{id}          → { deleted: true }       Delete tile set
GET    /api/tiles/{id}/{z}/{x}/{y}.png → PNG              Serve tile
GET    /api/tiles/{id}/thumb    → JPEG                    Serve thumbnail
GET    /api/config              → Config                  Get config
PUT    /api/config              → Config                  Update config (hot-reload)
GET    /admin/                  → Web management UI
GET    /docs                    → Swagger API docs
```

### Tile generation pipeline
1. Validate inputs, save image, generate thumbnail
2. Auto-compute zoom levels from image dimensions
3. Auto-determine tile size from image dimensions
4. Run `gdal2tiles` via `python -m osgeo_utils.gdal2tiles`
5. Clean up GDAL artifacts
6. Generate and save manifest JSON（含 levels 和 imageExtension）

### 示例页面（app/admin/ 下，独立文件）
- `demo-html.html` — 纯 HTML 瓦片预览（CDN Leaflet，有 API 地址输入框，任意 HTTP 服务器打开即用）
- `TileMapViewer.vue` — Vue 组件参考代码（复制到自己项目使用）

### Background job system
- In-memory job store with thread lock
- Jobs auto-evict after 1 hour
- Unified `run_job()` handles URL sources and uploads

## Important Notes

- **GDAL** installed via conda (`conda install -c conda-forge gdal`).
- PIL pixel limit raised to 2^31 (~2 billion pixels).
- SSRF protection: remote URLs resolving to private/reserved IPs are blocked.
- File size limit: default 200 MB, configurable via `/api/config`.
- CORS configurable via `CORS_ORIGINS` env var or `PUT /api/config`.
- Config is hot-reloadable via `/api/config`.
- App is at project root (`main.py`). Import: `main:app`.
- Primary developer works in Chinese.
