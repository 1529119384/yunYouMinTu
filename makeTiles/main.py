from __future__ import annotations

import ipaddress
import json
import logging
import os
import shutil
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

import settings
from tile_engine import (
    CreateTileResponse,
    TileManifest,
    auto_tile_size,
    compute_zoom_levels,
    generate_manifest,
    generate_thumbnail,
    guess_image_suffix,
    normalize_image_id,
    remove_gdal_artifacts,
    run_gdal2tiles,
    validate_and_save_image,
    validate_optional_zoom_inputs,
    validate_zoom_range,
)

logger = logging.getLogger("maketiles")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "app" / "data"
IMAGES_DIR = DATA_DIR / "images"
TILES_DIR = DATA_DIR / "tiles"
MANIFESTS_DIR = DATA_DIR / "manifests"
THUMBS_DIR = DATA_DIR / "thumbs"
ADMIN_DIR = BASE_DIR / "app" / "admin"


# ── Models ──────────────────────────────────────────────────────────────

class CreateTileJobRequest(BaseModel):
    file: str = Field(description="图片 URL 或本地路径")
    imageId: Optional[str] = Field(default=None, description="自定义切片 ID")
    maxZoom: Optional[int] = Field(default=None, description="最大缩放级别")
    minZoom: Optional[int] = Field(default=None, description="最小缩放级别")
    tileSize: Optional[int] = Field(default=None, description="瓦片尺寸")
    title: Optional[str] = Field(default=None, description="切片标题")

    @model_validator(mode="before")
    @classmethod
    def normalize_image_id_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and "imageid" in data and "imageId" not in data:
            data["imageId"] = data.pop("imageid")
        return data


class TileJobAcceptedResponse(BaseModel):
    jobId: str = Field(description="任务 ID")
    status: Literal["queued"] = Field(description="任务状态")


class TileJobStatusResponse(BaseModel):
    jobId: str = Field(description="任务 ID")
    status: Literal["queued", "processing", "completed", "failed"]
    imageId: Optional[str] = Field(default=None, description="完成后的切片 ID")
    result: Optional[CreateTileResponse] = Field(default=None, description="切片结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class TileJobRecord(BaseModel):
    jobId: str
    status: Literal["queued", "processing", "completed", "failed"]
    imageId: Optional[str] = None
    result: Optional[CreateTileResponse] = None
    error: Optional[str] = None
    createdAt: float
    updatedAt: float


class TileListItem(BaseModel):
    id: str
    title: str
    width: int
    height: int
    minZoom: int
    maxZoom: int
    tileSize: int
    note: Optional[str] = None


class TileListResponse(BaseModel):
    total: int
    items: List[TileListItem]


class NoteUpdateRequest(BaseModel):
    note: Optional[str] = Field(default=None, description="备注内容")


class ConfigResponse(BaseModel):
    max_image_bytes: int
    cors_origins: List[str]
    tile_cache_max_age: int
    max_job_age_seconds: int
    subprocess_timeout: int


# ── Job Store ───────────────────────────────────────────────────────────

JOBS: Dict[str, TileJobRecord] = {}
JOBS_LOCK = threading.Lock()


def create_job_record() -> str:
    job_id = uuid.uuid4().hex
    now = time.time()
    with JOBS_LOCK:
        JOBS[job_id] = TileJobRecord(
            jobId=job_id, status="queued", createdAt=now, updatedAt=now,
        )
    return job_id


def update_job(job_id: str, **changes: Any) -> None:
    with JOBS_LOCK:
        current = JOBS[job_id]
        updated = current.model_copy(update={**changes, "updatedAt": time.time()})
        JOBS[job_id] = updated


def _evict_stale_jobs() -> None:
    cfg = settings.get_settings()
    cutoff = time.time() - cfg["max_job_age_seconds"]
    with JOBS_LOCK:
        stale = [jid for jid, rec in JOBS.items() if rec.updatedAt < cutoff]
        for jid in stale:
            del JOBS[jid]


# ── SSRF Protection ────────────────────────────────────────────────────

def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="仅支持 http/https URL")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="无效 URL")
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(status_code=400, detail="URL 解析到私有/保留地址")
    except HTTPException:
        raise
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="无法解析主机名")


def load_source_bytes(source: str) -> tuple[bytes, str]:
    if not source:
        raise HTTPException(status_code=400, detail="file 参数不能为空")

    cfg = settings.get_settings()
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        _validate_remote_url(source)
        with urlopen(source, timeout=300) as response:
            data = bytearray()
            while chunk := response.read(8192):
                data.extend(chunk)
                if len(data) > cfg["max_image_bytes"]:
                    raise HTTPException(status_code=413, detail="远程文件过大")
        return bytes(data), Path(parsed.path).name or "remote-image"

    path = Path(source)
    if not path.exists():
        raise HTTPException(status_code=400, detail="源文件不存在")
    raw = path.read_bytes()
    if len(raw) > cfg["max_image_bytes"]:
        raise HTTPException(status_code=413, detail="文件过大")
    return raw, path.name


# ── Core Job Logic ──────────────────────────────────────────────────────

def run_job(
    job_id: str,
    raw_bytes: Optional[bytes],
    source_url: Optional[str],
    filename: Optional[str],
    image_id: Optional[str],
    title: Optional[str],
    min_zoom: Optional[int],
    max_zoom: Optional[int],
    base_url: str,
) -> None:
    try:
        update_job(job_id, status="processing")
        if raw_bytes is None and source_url:
            raw_bytes, filename = load_source_bytes(source_url)
        resolved_image_id = normalize_image_id(image_id)
        resolved_title = title or filename or "tile image"
        response = process_image_bytes(
            raw_bytes=raw_bytes,
            filename=filename,
            image_id=resolved_image_id,
            title=resolved_title,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            base_url=base_url,
        )
        update_job(
            job_id, status="completed",
            imageId=response.imageId, result=response, error=None,
        )
    except Exception as exc:
        logger.exception("任务 %s 失败", job_id)
        update_job(job_id, status="failed", error=str(exc))
    finally:
        _evict_stale_jobs()


def process_image_bytes(
    raw_bytes: bytes,
    filename: Optional[str],
    image_id: str,
    title: str,
    min_zoom: Optional[int],
    max_zoom: Optional[int],
    base_url: str,
) -> CreateTileResponse:
    validate_optional_zoom_inputs(min_zoom, max_zoom)

    suffix = guess_image_suffix(filename, raw_bytes)
    image_path = IMAGES_DIR / f"{image_id}{suffix}"
    width, height = validate_and_save_image(raw_bytes, image_path)

    # 统一尺寸：resize+padding 到 16384×16384
    from tile_engine import unify_image_size
    width, height = unify_image_size(image_path)

    tile_size = auto_tile_size(width, height)

    thumb_path = THUMBS_DIR / f"{image_id}.jpg"
    generate_thumbnail(image_path, thumb_path)

    manifest = build_tiles_for_image(
        image_path=image_path, image_id=image_id, title=title,
        tile_size=tile_size, min_zoom=min_zoom, max_zoom=max_zoom,
        width=width, height=height, base_url=base_url,
    )
    return CreateTileResponse(imageId=image_id, manifest=manifest)


def build_tiles_for_image(
    image_path: Path, image_id: str, title: str, tile_size: int,
    min_zoom: Optional[int], max_zoom: Optional[int],
    width: int, height: int, base_url: str,
) -> TileManifest:
    cfg = settings.get_settings()
    auto_min, auto_max = compute_zoom_levels(width, height, tile_size)
    min_zoom = auto_min if min_zoom is None else min_zoom
    max_zoom = auto_max if max_zoom is None else max_zoom
    validate_zoom_range(min_zoom, max_zoom)

    tile_output_dir = TILES_DIR / image_id
    if tile_output_dir.exists():
        shutil.rmtree(tile_output_dir)
    tile_output_dir.mkdir(parents=True, exist_ok=True)

    run_gdal2tiles(
        image_path=image_path, output_dir=tile_output_dir,
        min_zoom=min_zoom, max_zoom=max_zoom, tile_size=tile_size,
        timeout=cfg["subprocess_timeout"],
    )
    remove_gdal_artifacts(tile_output_dir)

    manifest = generate_manifest(
        base_url=base_url, image_id=image_id, title=title,
        width=width, height=height, min_zoom=min_zoom,
        max_zoom=max_zoom, tile_size=tile_size,
    )

    manifest_path = MANIFESTS_DIR / f"{image_id}.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


# ── FastAPI App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="makeTiles 切片服务",
    description="图片切片管理服务，支持上传、预览、删除切片",
    version="2.0.0",
    swagger_ui_parameters={"docExpansion": "none", "tagsSorter": "alpha"},
)


@app.on_event("startup")
def startup():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings.load_settings()
    for d in (IMAGES_DIR, TILES_DIR, MANIFESTS_DIR, THUMBS_DIR):
        d.mkdir(parents=True, exist_ok=True)


cfg = settings.get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg["cors_origins"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ADMIN_DIR.exists():
    app.mount("/admin", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")


# ── Routes ──────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/admin/")


@app.get("/health", summary="健康检查", tags=["系统"])
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post(
    "/api/tiles", response_model=TileJobAcceptedResponse, status_code=202,
    summary="创建切片任务", tags=["切片"],
)
async def create_tiles(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(default=None, description="图片文件（multipart）"),
    image_id: Optional[str] = Form(default=None, description="自定义切片 ID"),
    title: Optional[str] = Form(default=None, description="切片标题"),
    min_zoom: Optional[int] = Form(default=None, description="最小缩放级别"),
    max_zoom: Optional[int] = Form(default=None, description="最大缩放级别"),
):
    cfg = settings.get_settings()
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        payload = CreateTileJobRequest.model_validate(await request.json())
        job_id = create_job_record()
        base_url = str(request.base_url).rstrip("/")
        background_tasks.add_task(
            run_job,
            job_id=job_id, raw_bytes=None, source_url=payload.file,
            filename=None, image_id=payload.imageId, title=payload.title,
            min_zoom=payload.minZoom, max_zoom=payload.maxZoom,
            base_url=base_url,
        )
        return TileJobAcceptedResponse(jobId=job_id, status="queued")

    if file is None:
        raise HTTPException(status_code=400, detail="file 参数必填")

    raw_bytes = bytearray()
    while chunk := await file.read(1024 * 1024):
        raw_bytes.extend(chunk)
        if len(raw_bytes) > cfg["max_image_bytes"]:
            raise HTTPException(status_code=413, detail="文件过大")
    raw_bytes = bytes(raw_bytes)
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")

    job_id = create_job_record()
    base_url = str(request.base_url).rstrip("/")
    background_tasks.add_task(
        run_job,
        job_id=job_id, raw_bytes=raw_bytes, source_url=None,
        filename=file.filename, image_id=image_id, title=title,
        min_zoom=min_zoom, max_zoom=max_zoom,
        base_url=base_url,
    )
    return TileJobAcceptedResponse(jobId=job_id, status="queued")


@app.get(
    "/api/tiles", response_model=TileListResponse,
    summary="列出所有切片", tags=["切片"],
)
def list_tiles(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    q: Optional[str] = Query(default=None, description="搜索关键词"),
) -> TileListResponse:
    items: list[TileListItem] = []
    for manifest_file in sorted(MANIFESTS_DIR.glob("*.json")):
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if q:
                search_text = f"{data.get('id', '')} {data.get('title', '')} {data.get('note', '')}"
                if q.lower() not in search_text.lower():
                    continue
            items.append(TileListItem(
                id=data["id"], title=data["title"],
                width=data["width"], height=data["height"],
                minZoom=data["minZoom"], maxZoom=data["maxZoom"],
                tileSize=data["tileSize"], note=data.get("note"),
            ))
        except Exception:
            continue
    total = len(items)
    start = (page - 1) * page_size
    return TileListResponse(total=total, items=items[start:start + page_size])


@app.get(
    "/api/tiles/jobs/{job_id}", response_model=TileJobStatusResponse,
    summary="查询任务状态", tags=["任务"],
)
def get_job_status(job_id: str) -> TileJobStatusResponse:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TileJobStatusResponse(
        jobId=job.jobId, status=job.status,
        imageId=job.imageId, result=job.result, error=job.error,
    )


@app.get(
    "/api/tiles/{image_id}/manifest", response_model=TileManifest,
    summary="获取切片 manifest", tags=["切片"],
)
def get_manifest(image_id: str) -> dict:
    manifest_path = MANIFESTS_DIR / f"{image_id}.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="切片不存在")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.patch(
    "/api/tiles/{image_id}", response_model=TileManifest,
    summary="更新切片备注", tags=["切片"],
)
def update_tile_note(image_id: str, body: NoteUpdateRequest) -> dict:
    manifest_path = MANIFESTS_DIR / f"{image_id}.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="切片不存在")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["note"] = body.note
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return data


@app.delete(
    "/api/tiles/{image_id}",
    summary="删除切片", tags=["切片"],
)
def delete_tile(image_id: str) -> dict[str, bool]:
    deleted = False
    tile_dir = TILES_DIR / image_id
    if tile_dir.exists():
        shutil.rmtree(tile_dir)
        deleted = True
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        img_file = IMAGES_DIR / f"{image_id}{ext}"
        if img_file.exists():
            img_file.unlink()
            deleted = True
    manifest_file = MANIFESTS_DIR / f"{image_id}.json"
    if manifest_file.exists():
        manifest_file.unlink()
        deleted = True
    thumb_file = THUMBS_DIR / f"{image_id}.jpg"
    if thumb_file.exists():
        thumb_file.unlink()
        deleted = True
    if not deleted:
        raise HTTPException(status_code=404, detail="切片不存在")
    return {"deleted": True}


@app.get(
    "/api/tiles/{image_id}/{z}/{x}/{y}.png",
    summary="获取瓦片", tags=["切片"],
)
def get_tile(image_id: str, z: int, x: int, y: int) -> FileResponse:
    tile_path = TILES_DIR / image_id / str(z) / str(x) / f"{y}.png"
    if not tile_path.exists():
        raise HTTPException(status_code=404, detail="瓦片不存在")
    cfg = settings.get_settings()
    return FileResponse(
        tile_path, media_type="image/png",
        headers={"Cache-Control": f"public, max-age={cfg['tile_cache_max_age']}, immutable"},
    )


@app.get(
    "/api/tiles/{image_id}/thumb",
    summary="获取缩略图", tags=["切片"],
)
def get_thumbnail(image_id: str) -> FileResponse:
    thumb_path = THUMBS_DIR / f"{image_id}.jpg"
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="缩略图不存在")
    return FileResponse(thumb_path, media_type="image/jpeg")


@app.get(
    "/api/config", response_model=ConfigResponse,
    summary="获取当前配置", tags=["配置"],
)
def get_config() -> dict:
    return settings.get_settings()


@app.put(
    "/api/config", response_model=ConfigResponse,
    summary="更新配置（热加载）", tags=["配置"],
)
def update_config(body: ConfigResponse) -> dict:
    data = body.model_dump()
    result = settings.update_settings(data)
    new_cfg = settings.get_settings()
    return new_cfg
