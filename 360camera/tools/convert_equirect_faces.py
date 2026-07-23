"""
等矩形全景图 → 6 面立方体 + logo 贴底面
用法: python convert_equirect_faces.py --input scene.jpg --logo logo.png --name scene1
"""
import os, argparse
import numpy as np
from PIL import Image

FACES_CUBE = ['f', 'r', 'b', 'l', 'u', 'd']

def equirect_to_cubemap(img, face_size):
    w, h = img.size
    arr = np.array(img, dtype=np.float64)
    faces = {}

    for name in FACES_CUBE:
        xs = np.arange(face_size)
        ys = np.arange(face_size)
        xx, yy = np.meshgrid(xs, ys)
        u = (2 * (xx + 0.5) / face_size - 1)
        v = (2 * (yy + 0.5) / face_size - 1)

        if name == 'f':   dx, dy, dz = u, v, -np.ones_like(u)
        elif name == 'r': dx, dy, dz = np.ones_like(u), v, u
        elif name == 'b': dx, dy, dz = -u, v, np.ones_like(u)
        elif name == 'l': dx, dy, dz = -np.ones_like(u), v, -u
        elif name == 'u': dx, dy, dz = u, np.ones_like(u), v
        elif name == 'd': dx, dy, dz = u, -np.ones_like(u), -v

        norm = np.sqrt(dx*dx + dy*dy + dz*dz)
        dx /= norm; dy /= norm; dz /= norm

        theta = np.arctan2(dx, dz)
        phi = np.arcsin(np.clip(dy, -1, 1))

        eq_x = (theta / np.pi + 1) * 0.5 * (w - 1)
        eq_y = (0.5 - phi / np.pi) * (h - 1)
        eq_x = np.clip(eq_x, 0, w - 1)
        eq_y = np.clip(eq_y, 0, h - 1)

        x0 = np.floor(eq_x).astype(int)
        y0 = np.floor(eq_y).astype(int)
        x1 = np.minimum(x0 + 1, w - 1)
        y1 = np.minimum(y0 + 1, h - 1)
        fx = (eq_x - x0)[..., np.newaxis]
        fy = (eq_y - y0)[..., np.newaxis]

        pixel = (
            arr[y0, x0] * (1-fx) * (1-fy) +
            arr[y0, x1] * fx * (1-fy) +
            arr[y1, x0] * (1-fx) * fy +
            arr[y1, x1] * fx * fy
        )
        face = Image.fromarray(np.clip(pixel, 0, 255).astype(np.uint8))

        if name == 'u':
            face = face.transpose(Image.FLIP_TOP_BOTTOM)
        elif name == 'd':
            face = face.transpose(Image.FLIP_TOP_BOTTOM)

        faces[name] = face

    return faces


def paste_logo_center(face, logo, radius):
    logo_size = radius * 2
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    x = (face.width - logo_size) // 2
    y = (face.height - logo_size) // 2

    face_rgba = face.convert('RGBA')
    face_rgba.paste(logo, (x, y), logo)
    return face_rgba


def main():
    parser = argparse.ArgumentParser(description='等矩形 → 立方体面 + logo 贴底面')
    parser.add_argument('--input', required=True, help='等矩形全景图路径')
    parser.add_argument('--logo', required=True, help='logo 图片路径')
    parser.add_argument('--name', default='scene', help='场景名称，用于输出目录名')
    parser.add_argument('--radius', type=int, default=900, help='logo 在底面中的半径，像素（默认 900）')
    parser.add_argument('--out', default=None, help='输出目录（默认 tools/faces/{name}）')
    args = parser.parse_args()

    out_dir = args.out or os.path.join(os.path.dirname(__file__), 'faces', args.name)
    os.makedirs(out_dir, exist_ok=True)

    print(f'读取等矩形图: {args.input}')
    src = Image.open(args.input).convert('RGBA')
    w, h = src.size
    cube_size = (w // 4 // 64) * 64
    if cube_size < 512:
        cube_size = 512
    print(f'等矩形尺寸: {w}x{h}  →  面图尺寸: {cube_size}x{cube_size}')

    print('转换 6 面...')
    faces = equirect_to_cubemap(src, cube_size)

    for name in FACES_CUBE:
        fpath = os.path.join(out_dir, f'{name}.png')
        faces[name].save(fpath, 'PNG')
        print(f'  {name}.png 保存')

    print(f'贴 logo 到底面...')
    logo = Image.open(args.logo).convert('RGBA')
    d_logo = paste_logo_center(faces['d'], logo, args.radius)
    d_logo_path = os.path.join(out_dir, 'd_logo.png')
    d_logo.save(d_logo_path, 'PNG')
    print(f'  d_logo.png 保存')

    print(f'\n完成！输出目录: {out_dir}')
    print(f'  原始 6 面: f.png r.png b.png l.png u.png d.png')
    print(f'  贴 logo 底面: d_logo.png')


if __name__ == '__main__':
    main()
