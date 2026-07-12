"""
Generate Pannellum multires cubemap tiles from equirectangular panoramas.
Output: tiles/{scene}/{face}/{level}/{row}/{col}.jpg
"""
import os
import json
import math
import numpy as np
from PIL import Image

TILE_SIZE = 512
QUALITY = 82
FACES = ['f', 'r', 'b', 'l', 'u', 'd']


def equirect_to_cubemap(img, face_size):
    """Vectorized equirectangular to cubemap conversion."""
    w, h = img.size
    equirect = np.array(img, dtype=np.float64)
    faces = {}

    for name in FACES:
        x = np.arange(face_size)
        y = np.arange(face_size)
        xx, yy = np.meshgrid(x, y)
        u = (2 * (xx + 0.5) / face_size - 1)
        v = (2 * (yy + 0.5) / face_size - 1)

        if name == 'f':   dx, dy, dz = u, v, -np.ones_like(u)
        elif name == 'r': dx, dy, dz = np.ones_like(u), v, u
        elif name == 'b': dx, dy, dz = -u, v, np.ones_like(u)
        elif name == 'l': dx, dy, dz = -np.ones_like(u), v, -u
        elif name == 'u': dx, dy, dz = u, np.ones_like(u), v
        elif name == 'd': dx, dy, dz = u, -np.ones_like(u), -v

        norm = np.sqrt(dx*dx + dy*dy + dz*dz)
        dx, dy, dz = dx/norm, dy/norm, dz/norm

        theta = np.arctan2(dx, dz)
        phi = np.arcsin(np.clip(dy, -1, 1))
        phi = np.clip(phi, -1.45, 1.45)  # clamp poles

        eq_x = (theta / math.pi + 1) * 0.5 * (w - 1)
        eq_y = (0.5 - phi / math.pi) * (h - 1)
        eq_x = np.clip(eq_x, 0, w - 1)  # prevent wrapping
        eq_y = np.clip(eq_y, 0, h - 1)

        x0 = np.floor(eq_x).astype(int)
        y0 = np.floor(eq_y).astype(int)
        x1 = np.minimum(x0 + 1, w - 1)
        y1 = np.minimum(y0 + 1, h - 1)
        fx = (eq_x - x0)[..., np.newaxis]
        fy = (eq_y - y0)[..., np.newaxis]

        pixel = (
            equirect[y0, x0] * (1-fx) * (1-fy) +
            equirect[y0, x1] * fx * (1-fy) +
            equirect[y1, x0] * (1-fx) * fy +
            equirect[y1, x1] * fx * fy
        )
        faces[name] = Image.fromarray(np.clip(pixel, 0, 255).astype(np.uint8))

    # Pannellum 的切片行序 y=0 在顶部，但 u/d 面需要翻转以匹配渲染朝向
    faces['u'] = faces['u'].transpose(Image.FLIP_TOP_BOTTOM)
    faces['d'] = faces['d'].transpose(Image.FLIP_TOP_BOTTOM)

    return faces


def generate_tiles(src_path, scene_name, output_dir):
    print(f"  Loading {src_path}...")
    img = Image.open(src_path)
    orig_w, orig_h = img.size
    print(f"  Source: {orig_w}x{orig_h}")

    cube_size = (orig_w // 4 // TILE_SIZE) * TILE_SIZE
    if cube_size < TILE_SIZE:
        cube_size = TILE_SIZE
    print(f"  Cube face: {cube_size}")

    print(f"  Converting to cubemap...")
    faces = equirect_to_cubemap(img, cube_size)

    scene_dir = os.path.join(output_dir, scene_name)
    max_level = int(math.log2(cube_size / TILE_SIZE))
    print(f"  Max level: {max_level}")

    for face_name, face_img in faces.items():
        for level in range(max_level + 1):
            scale = 2 ** level
            lw = cube_size // scale
            lh = cube_size // scale
            cols = max(1, math.ceil(lw / TILE_SIZE))
            rows = max(1, math.ceil(lh / TILE_SIZE))

            resized = face_img.resize((lw, lh), Image.LANCZOS)

            for row in range(rows):
                for col in range(cols):
                    x0 = col * TILE_SIZE
                    y0 = row * TILE_SIZE
                    x1 = min(x0 + TILE_SIZE, lw)
                    y1 = min(y0 + TILE_SIZE, lh)

                    tile = resized.crop((x0, y0, x1, y1))
                    tile_dir = os.path.join(scene_dir, face_name, str(level), str(row))
                    os.makedirs(tile_dir, exist_ok=True)
                    tile.save(os.path.join(tile_dir, f'{col}.jpg'), 'JPEG', quality=QUALITY, optimize=True)

        print(f"    Face '{face_name}' done")

    config = {
        "basePath": f"tiles/{scene_name}",
        "path": "/%s/%l/%y/%x",
        "fallbackPath": "/fallback/%s",
        "extension": "jpg",
        "tileResolution": TILE_SIZE,
        "maxLevel": max_level,
        "cubeResolution": cube_size,
    }
    with open(os.path.join(scene_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)

    # Generate 256x256 fallback face images
    fb_dir = os.path.join(scene_dir, 'fallback')
    os.makedirs(fb_dir, exist_ok=True)
    for face_name, face_img in faces.items():
        fb = face_img.resize((256, 256), Image.LANCZOS)
        fb.save(os.path.join(fb_dir, f'{face_name}.jpg'), 'JPEG', quality=80)

    print(f"  Config + fallback written")
    return config


def main():
    scenes = {
        'scene1': 'public/images/scene1.jpg',
        'scene2': 'public/images/scene2.jpg',
        'scene3': 'public/images/scene3.jpg',
    }
    output_dir = os.path.join(os.path.dirname(__file__), 'public', 'tiles')

    # Clean old tiles
    import shutil
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    for name, path in scenes.items():
        if not os.path.exists(path):
            print(f"SKIP: {path}")
            continue
        print(f"\n=== {name} ===")
        generate_tiles(path, name, output_dir)

    print("\nDone!")


if __name__ == '__main__':
    main()
