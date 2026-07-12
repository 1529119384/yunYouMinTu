from __future__ import annotations

import math
import shutil
import subprocess
import sys
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

Image.MAX_IMAGE_PIXELS = 2 ** 31  # ~20 亿像素

# 统一切片目标尺寸（所有楼层 resize+padding 到此尺寸）
UNIFY_TARGET_SIZE = (16384, 16384)


def unify_image_size(image_path: Path, target_size: tuple[int, int] = UNIFY_TARGET_SIZE) -> tuple[int, int]:
    """将图片 resize+padding 到统一尺寸，保持宽高比，居中放置，黑色填充。

    返回统一后的 (width, height)。
    """
    tw, th = target_size
    with Image.open(image_path) as img:
        w, h = img.size
        if w == tw and h == th:
            return w, h  # 已经是目标尺寸，无需处理

        # 计算缩放比例（保持宽高比，fit 到目标尺寸内）
        scale = min(tw / w, th / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # 缩放
        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # 创建黑色画布
        canvas = Image.new("RGB", (tw, th), (0, 0, 0))

        # 居中粘贴
        offset_x = (tw - new_w) // 2
        offset_y = (th - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))

        # 保存覆盖原图
        canvas.save(image_path)

    return tw, th


class TileManifest(BaseModel):
    id: str = Field(description="切片唯一标识")
    title: str = Field(description="切片标题")
    width: int = Field(description="原图宽度（像素）")
    height: int = Field(description="原图高度（像素）")
    minZoom: int = Field(description="最小缩放级别")
    maxZoom: int = Field(description="最大缩放级别")
    tileSize: int = Field(description="瓦片尺寸（像素）")
    extent: List[float] = Field(description="图像范围 [left, bottom, right, top]")
    origin: List[float] = Field(description="原点坐标")
    resolutions: List[float] = Field(description="每个缩放级别的分辨率")
    center: List[float] = Field(description="图像中心点坐标")
    initialResolution: float = Field(description="初始分辨率")
    urlTemplate: str = Field(description="瓦片 URL 模板")
    manifestUrl: str = Field(description="manifest 自身 URL")
    tileFormat: str = Field(default="png", description="瓦片格式")
    scheme: str = Field(default="xyz", description="坐标方案")
    projection: str = Field(default="pixel", description="投影方式")
    bounds: List[float] = Field(description="边界 [left, top, right, bottom]")
    generatedBy: str = Field(default="gdal2tiles", description="生成工具")
    levels: Optional[List[dict]] = Field(default=None, description="每个缩放级别的瓦片网格信息 [{z, cols, rows}]")
    imageExtension: str = Field(default="png", description="瓦片文件扩展名")
    note: Optional[str] = Field(default=None, description="备注")


class CreateTileResponse(BaseModel):
    imageId: str = Field(description="切片唯一标识")
    manifest: TileManifest = Field(description="切片 manifest")


def get_image_size(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as img:
        return img.size


def compute_zoom_levels(width: int, height: int, tile_size: int) -> tuple[int, int]:
    max_dim = max(width, height)
    min_zoom = 0
    max_zoom = int(math.ceil(math.log2(max(max_dim / tile_size, 1))))
    return min_zoom, max_zoom


def compute_resolutions(
    width: int, height: int, min_zoom: int, max_zoom: int, tile_size: int
) -> List[float]:
    levels = max_zoom - min_zoom + 1
    max_dim = max(width, height)
    base = max(max_dim / tile_size, 1)
    start = float(2 ** math.ceil(math.log2(base)))
    return [start / (2 ** i) for i in range(levels)]


def run_gdal2tiles(
    image_path: Path,
    output_dir: Path,
    min_zoom: int,
    max_zoom: int,
    tile_size: int,
    timeout: int = 600,
) -> None:
    cmd = [
        sys.executable, "-m", "osgeo_utils.gdal2tiles",
        "--profile", "raster",
        "--xyz",
        "--webviewer", "none",
        "--zoom", f"{min_zoom}-{max_zoom}",
        "--tilesize", str(tile_size),
        str(image_path),
        str(output_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "gdal2tiles failed")


def remove_gdal_artifacts(output_path: Path) -> None:
    for name in [
        "googlemaps.html", "leaflet.html", "openlayers.html",
        "tilemapresource.xml", "doc.kml",
    ]:
        target = output_path / name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()


def auto_tile_size(width: int, height: int) -> int:
    max_dim = max(width, height)
    if max_dim <= 4096:
        return 256
    if max_dim <= 16384:
        return 512
    if max_dim <= 65536:
        return 1024
    return 2048


def validate_and_save_image(raw_bytes: bytes, image_path: Path) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            width, height = img.size
            img.verify()
    except DecompressionBombError:
        raise ValueError("图片过大，无法处理")
    except UnidentifiedImageError:
        raise ValueError("无效的图片文件")
    except Exception as exc:
        raise ValueError(str(exc))

    with image_path.open("wb") as f:
        f.write(raw_bytes)
    return width, height


def generate_thumbnail(image_path: Path, thumb_path: Path, size: int = 256) -> None:
    with Image.open(image_path) as img:
        img.thumbnail((size, size), Image.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(thumb_path, "JPEG", quality=85)


def guess_image_suffix(filename: Optional[str], raw_bytes: bytes) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix:
            return suffix
    if raw_bytes.startswith(b"\x89PNG"):
        return ".png"
    if raw_bytes.startswith(b"\xff\xd8"):
        return ".jpg"
    return ".png"


def normalize_image_id(image_id: Optional[str]) -> str:
    raw = image_id or uuid.uuid4().hex
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in ("-", "_"))
    if not cleaned:
        raise ValueError("无效的 image id")
    return cleaned


def validate_tile_size(tile_size: int) -> None:
    if tile_size <= 0:
        raise ValueError("tileSize 必须大于 0")


def validate_zoom_range(min_zoom: int, max_zoom: int) -> None:
    if min_zoom < 0 or max_zoom < min_zoom:
        raise ValueError("无效的缩放范围")


def validate_optional_zoom_inputs(
    min_zoom: Optional[int], max_zoom: Optional[int]
) -> None:
    if min_zoom is None and max_zoom is None:
        return
    if min_zoom is None or max_zoom is None:
        raise ValueError("minZoom 和 maxZoom 必须同时提供")
    validate_zoom_range(min_zoom, max_zoom)


def generate_manifest(
    base_url: str,
    image_id: str,
    title: str,
    width: int,
    height: int,
    min_zoom: int,
    max_zoom: int,
    tile_size: int,
) -> TileManifest:
    extent = [0.0, float(-height), float(width), 0.0]
    origin = [0.0, 0.0]
    center = [width / 2, -height / 2]
    bounds = [0.0, 0.0, float(width), float(height)]

    resolutions = compute_resolutions(width, height, min_zoom, max_zoom, tile_size)
    initial_resolution = resolutions[0]

    levels = []
    for z in range(min_zoom, max_zoom + 1):
        factor = 2 ** (max_zoom - z)
        cols = math.ceil(math.ceil(width / factor) / tile_size)
        rows = math.ceil(math.ceil(height / factor) / tile_size)
        levels.append({"z": z, "cols": cols, "rows": rows})

    return TileManifest(
        id=image_id,
        title=title,
        width=width,
        height=height,
        minZoom=min_zoom,
        maxZoom=max_zoom,
        tileSize=tile_size,
        extent=extent,
        origin=origin,
        resolutions=resolutions,
        center=center,
        initialResolution=initial_resolution,
        urlTemplate=f"{base_url}/api/tiles/{image_id}/{{z}}/{{x}}/{{y}}.png",
        manifestUrl=f"{base_url}/api/tiles/{image_id}/manifest",
        bounds=bounds,
        levels=levels,
    )
