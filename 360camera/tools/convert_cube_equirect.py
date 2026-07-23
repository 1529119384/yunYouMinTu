"""
6 面立方体图（含贴 logo 底面）→ 等矩形全景图
用法: python convert_cube_equirect.py --faces-dir faces/scene1 --output scene1.png
"""
import os, argparse
import numpy as np
from PIL import Image

FACES = ['f', 'r', 'b', 'l', 'u']


def load_faces(faces_dir, d_face='d_logo.png'):
    face_imgs = {}
    ref = None
    for name in FACES:
        path = os.path.join(faces_dir, f'{name}.png')
        im = Image.open(path).convert('RGBA')
        face_imgs[name] = im
        ref = im.size

    d_path = os.path.join(faces_dir, d_face)
    if not os.path.exists(d_path):
        d_path = os.path.join(faces_dir, 'd.png')
    face_imgs['d'] = Image.open(d_path).convert('RGBA')

    assert Image.open(os.path.join(faces_dir, 'f.png')).size == ref, '所有面图尺寸必须一致'
    return face_imgs, ref[0]


def cubemap_to_equirect(faces, cube_size, eq_w, eq_h):
    eq_x = np.arange(eq_w, dtype=np.float64)
    eq_y = np.arange(eq_h, dtype=np.float64)
    xx, yy = np.meshgrid(eq_x, eq_y)

    theta = (2 * xx / (eq_w - 1) - 1) * np.pi
    phi = (0.5 - yy / (eq_h - 1)) * np.pi

    dx = -np.cos(phi) * np.sin(theta)
    dy = np.sin(phi)
    dz = -np.cos(phi) * np.cos(theta)

    abs_dx = np.abs(dx)
    abs_dy = np.abs(dy)
    abs_dz = np.abs(dz)

    result = np.zeros((eq_h, eq_w, 4), dtype=np.uint8)

    face_rules = [
        ('f', (dz < 0) & (abs_dz >= abs_dx) & (abs_dz >= abs_dy),
         lambda: dx / abs_dz, lambda: dy / abs_dz, False),
        ('r', (dx > 0) & (abs_dx >= abs_dy) & (abs_dx >= abs_dz),
         lambda: dz / dx, lambda: dy / dx, False),
        ('b', (dz > 0) & (abs_dz >= abs_dx) & (abs_dz >= abs_dy),
         lambda: -dx / dz, lambda: dy / dz, False),
        ('l', (dx < 0) & (abs_dx >= abs_dy) & (abs_dx >= abs_dz),
         lambda: dz / dx, lambda: -dy / dx, False),
        ('u', (dy > 0) & (abs_dy >= abs_dx) & (abs_dy >= abs_dz),
         lambda: dx / dy, lambda: dz / dy, True),
        ('d', (dy < 0) & (abs_dy >= abs_dx) & (abs_dy >= abs_dz),
         lambda: -dx / dy, lambda: dz / dy, True),
    ]

    for name, cond, u_fn, v_fn, flip_v in face_rules:
        mask = cond
        if not mask.any():
            continue

        u = u_fn()
        v = v_fn()
        if flip_v:
            v = -v

        u = np.clip(u[mask], -1, 1)
        v = np.clip(v[mask], -1, 1)

        fx = (u + 1) / 2 * (cube_size - 1)
        fy = (v + 1) / 2 * (cube_size - 1)

        face_arr = np.array(faces[name], dtype=np.float64)

        x0 = np.floor(fx).astype(int)
        y0 = np.floor(fy).astype(int)
        x1 = np.minimum(x0 + 1, cube_size - 1)
        y1 = np.minimum(y0 + 1, cube_size - 1)
        wx = (fx - x0)[:, np.newaxis]
        wy = (fy - y0)[:, np.newaxis]

        sampled = (
            face_arr[y0, x0] * (1-wx) * (1-wy) +
            face_arr[y0, x1] * wx * (1-wy) +
            face_arr[y1, x0] * (1-wx) * wy +
            face_arr[y1, x1] * wx * wy
        )
        result[mask] = np.clip(sampled, 0, 255).astype(np.uint8)

    return Image.fromarray(result, 'RGBA')


def main():
    parser = argparse.ArgumentParser(description='立方体面 → 等矩形全景图')
    parser.add_argument('--faces-dir', required=True, help='面图目录（包含 f.png r.png b.png l.png u.png d.png）')
    parser.add_argument('--output', required=True, help='输出等矩形全景图路径（如 scene1_fixed.jpg）')
    parser.add_argument('--size', default=None, help='输出尺寸 WxH（如 11904x5952，默认匹配原等矩形图）')
    args = parser.parse_args()

    print('加载面图...')
    faces, cube_size = load_faces(args.faces_dir)

    if args.size:
        parts = args.size.split('x')
        eq_w, eq_h = int(parts[0]), int(parts[1])
    else:
        w4 = cube_size * 4
        eq_w = (w4 // 64) * 64
        eq_h = eq_w // 2
    print(f'面图尺寸: {cube_size}x{cube_size}  → 输出等矩形: {eq_w}x{eq_h}')

    print('立方体 → 等矩形...')
    eq_img = cubemap_to_equirect(faces, cube_size, eq_w, eq_h)

    eq_img.save(args.output, 'PNG')
    print(f'完成: {args.output}')


if __name__ == '__main__':
    main()
