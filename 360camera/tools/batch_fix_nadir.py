"""
批量修复天底脚架：等矩形 → 拆面 → 贴 logo → 拼回等矩形（PNG 无损）
用法: python batch_fix_nadir.py --input-dir tools/Orgin_images --logo public/images/logo.png --workers 4
"""
import os, sys, time, shutil, argparse, glob, subprocess, signal
from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


def process_one(args):
    src_path, idx, logo_path, radius, temp_base = args
    name = os.path.splitext(os.path.basename(src_path))[0]
    temp_dir = os.path.join(temp_base, f'_{idx:04d}')
    out_name = f'scene{idx}.png'

    t0 = time.time()

    img = Image.open(src_path)
    img_w, img_h = img.size
    img.close()

    subprocess.run([
        sys.executable,
        os.path.join(TOOLS_DIR, 'convert_equirect_faces.py'),
        '--input', src_path,
        '--logo', logo_path,
        '--name', f'scene{idx}',
        '--radius', str(radius),
        '--out', temp_dir,
    ], check=True)

    subprocess.run([
        sys.executable,
        os.path.join(TOOLS_DIR, 'convert_cube_equirect.py'),
        '--faces-dir', temp_dir,
        '--output', os.path.join(temp_base, out_name),
        '--size', f'{img_w}x{img_h}',
    ], check=True)

    shutil.rmtree(temp_dir, ignore_errors=True)

    elapsed = time.time() - t0
    return (idx, out_name, elapsed, os.path.join(temp_base, out_name))


def main():
    parser = argparse.ArgumentParser(description='批量修复全景图天底脚架')
    parser.add_argument('--input-dir', required=True, help='等矩形原图目录')
    parser.add_argument('--logo', required=True, help='logo 图片路径')
    parser.add_argument('--output-dir', default=None, help='输出目录（默认 public/images）')
    parser.add_argument('--radius', type=int, default=900, help='logo 半径（像素，默认 900）')
    parser.add_argument('--workers', type=int, default=4, help='并行进程数（默认 4）')
    parser.add_argument('--ext', default='.jpg', help='输入图片扩展名（默认 .jpg）')
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    logo_path = os.path.abspath(args.logo)
    output_dir = args.output_dir or os.path.join(os.path.dirname(TOOLS_DIR), 'public', 'images')
    os.makedirs(output_dir, exist_ok=True)

    temp_base = os.path.join(TOOLS_DIR, '.tmp')
    os.makedirs(temp_base, exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, f'*{args.ext}')))
    if not files:
        print(f'错误: {input_dir} 下没有 *{args.ext} 文件')
        sys.exit(1)

    total = len(files)
    print(f'发现 {total} 张等矩形图')
    print(f'logo: {logo_path}')
    print(f'logo 半径: {args.radius}px')
    print(f'并行进程: {args.workers}')
    print(f'输出: {output_dir}')
    print(f'格式: PNG 无损')
    print('=' * 60)
    print('按 Ctrl+C 停止（可能需按多次）')

    task_args = [
        (src, i, logo_path, args.radius, temp_base)
        for i, src in enumerate(files, 1)
    ]

    from concurrent.futures import ProcessPoolExecutor, as_completed

    t_start = time.time()
    completed = 0
    total_elapsed = 0
    interrupted = False

    executor = ProcessPoolExecutor(max_workers=args.workers)
    try:
        futures = {executor.submit(process_one, arg): arg for arg in task_args}

        for future in as_completed(futures):
            if interrupted:
                break
            try:
                idx, out_name, elapsed, temp_path = future.result(timeout=600)
            except KeyboardInterrupt:
                print('\n正在停止...')
                interrupted = True
                executor.shutdown(wait=False, cancel_futures=True)
                break

            out_path = os.path.join(output_dir, out_name)
            if os.path.exists(temp_path):
                if os.path.exists(out_path):
                    os.remove(out_path)
                shutil.move(temp_path, out_path)

            completed += 1
            total_elapsed += elapsed
            avg = total_elapsed / completed
            eta = avg * (total - completed)

            print(
                f'[{completed:>3}/{total}] {out_name}  '
                f'{elapsed:>5.0f}s  '
                f'已用 {total_elapsed:>5.0f}s  '
                f'剩余 {eta:>5.0f}s'
            )
    except KeyboardInterrupt:
        print('\n正在停止...')
        executor.shutdown(wait=False, cancel_futures=True)
    finally:
        if not executor._shutdown:
            executor.shutdown(wait=False)

    t_total = time.time() - t_start
    print('=' * 60)
    print(f'处理完成: {completed}/{total} 张  → {output_dir}  用时 {t_total:.0f}s')


if __name__ == '__main__':
    main()
