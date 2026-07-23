"""
batch_tile_new.py — 批量切片新图片（8 个楼层）
使用 Pillow 生成 XYZ 瓦片，结构 {z}/{x}/{y}.png

用法：
    python batch_tile_new.py
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tile_engine import auto_tile_size, compute_zoom_levels, compute_resolutions

UNIFY_TARGET_SIZE = (16384, 16384)

SRC_DIR = Path(__file__).resolve().parent.parent / "闵图每层轴测图新的"
OUT_DIR = Path(__file__).resolve().parent / "app" / "data" / "tiles"
UNIFIED_DIR = Path(__file__).resolve().parent / "app" / "data" / "images_unified"

IMAGE_MAP = {
    "整体外观.png": "overall",
    "1层.png": "floor-1",
    "2层.png": "floor-2",
    "3层.png": "floor-3",
    "4层.png": "floor-4",
    "5层.png": "floor-5",
    "6层.png": "floor-6",
    "7层.png": "floor-7",
}


def unify_image_size_rgba(image_path: Path):
    """统一尺寸到 16384x16384，透明填充（RGBA）"""
    tw, th = UNIFY_TARGET_SIZE
    with Image.open(image_path) as img:
        w, h = img.size
        if w == tw and h == th:
            return w, h

        scale = min(tw / w, th / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        offset_x = (tw - new_w) // 2
        offset_y = (th - new_h) // 2
        if resized.mode == "RGBA":
            canvas.paste(resized, (offset_x, offset_y), resized)
        else:
            canvas.paste(resized, (offset_x, offset_y))
        canvas.save(image_path)

    return tw, th


def generate_tiles_pillow(
    image_path: Path,
    output_dir: Path,
    tile_size: int,
    max_zoom: int,
):
    """生成 XYZ 瓦片金字塔，结构 {z}/{x}/{y}.png （x=目录，y=文件）"""
    img = Image.open(image_path)
    w, h = img.size

    total_tiles = 0
    for z in range(max_zoom + 1):
        factor = 2 ** (max_zoom - z)
        level_w = math.ceil(w / factor)
        level_h = math.ceil(h / factor)

        resized = img.resize((level_w, level_h), Image.LANCZOS)
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")

        cols = math.ceil(level_w / tile_size)
        rows = math.ceil(level_h / tile_size)
        total_tiles += cols * rows

        for x in range(cols):
            x_dir = output_dir / str(z) / str(x)
            x_dir.mkdir(parents=True, exist_ok=True)
            for y in range(rows):
                left = x * tile_size
                top = y * tile_size
                right = min(left + tile_size, level_w)
                bottom = min(top + tile_size, level_h)

                tile_img = resized.crop((left, top, right, bottom))

                if tile_img.size == (tile_size, tile_size):
                    tile_img.save(str(x_dir / f"{y}.png"))
                else:
                    tile = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
                    tile.paste(tile_img, (0, 0), tile_img if tile_img.mode == "RGBA" else None)
                    tile.save(str(x_dir / f"{y}.png"))

    return total_tiles


def write_manifest(tile_dir: Path, floor_id: str, title: str, width: int, height: int, tile_size: int, max_zoom: int):
    manifest = {
        "id": floor_id,
        "title": title,
        "width": width,
        "height": height,
        "minZoom": 0,
        "maxZoom": max_zoom,
        "tileSize": tile_size,
        "extent": [0.0, float(-height), float(width), 0.0],
        "origin": [0.0, 0.0],
        "resolutions": compute_resolutions(width, height, 0, max_zoom, tile_size),
        "center": [width / 2, -height / 2],
        "initialResolution": float(compute_resolutions(width, height, 0, max_zoom, tile_size)[0]),
        "urlTemplate": f"/tiles/{floor_id}/{{z}}/{{x}}/{{y}}.png",
        "manifestUrl": f"/tiles/{floor_id}/manifest.json",
        "tileFormat": "png",
        "scheme": "xyz",
        "projection": "pixel",
        "bounds": [0.0, 0.0, float(width), float(height)],
        "generatedBy": "Pillow",
        "note": None,
    }
    manifest_path = tile_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  manifest: {manifest_path}")


def process_image(src_path: Path, floor_id: str):
    print(f"\n{'='*60}")
    print(f"  {src_path.name} -> {floor_id}")
    print(f"{'='*60}")

    UNIFIED_DIR.mkdir(parents=True, exist_ok=True)
    unified_path = UNIFIED_DIR / f"{floor_id}.png"
    shutil.copy2(src_path, unified_path)
    print(f"  copy: {unified_path.name}")

    width, height = unify_image_size_rgba(unified_path)
    print(f"  unified: {width}x{height} RGBA")

    tile_size = auto_tile_size(width, height)
    min_zoom, max_zoom = compute_zoom_levels(width, height, tile_size)
    print(f"  params: tileSize={tile_size}, zoom={min_zoom}-{max_zoom}")

    tile_dir = OUT_DIR / floor_id
    if tile_dir.exists():
        shutil.rmtree(tile_dir)
    tile_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    total = generate_tiles_pillow(unified_path, tile_dir, tile_size, max_zoom)
    elapsed = time.time() - t0
    print(f"  tiles: {total} tiles, {elapsed:.1f}s")

    write_manifest(tile_dir, floor_id, src_path.name, width, height, tile_size, max_zoom)


def main():
    if not SRC_DIR.exists():
        print(f"ERROR: source dir not found: {SRC_DIR}"); sys.exit(1)

    for filename in IMAGE_MAP:
        if not (SRC_DIR / filename).exists():
            print(f"ERROR: source file not found: {SRC_DIR / filename}"); sys.exit(1)

    print(f"Source: {SRC_DIR}")
    print(f"Output: {OUT_DIR}")
    print(f"Floors: {len(IMAGE_MAP)}")
    print()

    t_start = time.time()
    for filename, floor_id in IMAGE_MAP.items():
        process_image(SRC_DIR / filename, floor_id)

    total_elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Done! Total: {total_elapsed:.1f}s")
    print(f"Output: {OUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
