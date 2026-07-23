"""
批量生成 Pannellum multires 立方体贴图瓦片（官方 generate.py + Hugin nona）
用法: python tools/batch_tiles.py --input-dir public/images --output-dir title_new --nona "D:/soft/Hugin/bin/nona.exe" --workers 4
"""
import os, sys, time, shutil, argparse, glob, subprocess, signal
from PIL import Image

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATE_PY = os.path.join(PROJECT_DIR, 'pannellum-2.5.7', 'utils', 'multires', 'generate.py')


def process_one(args):
    src_path, idx, nona_bin, out_base = args
    name = f'scene{idx}'
    out_dir = os.path.join(out_base, name)

    if os.path.exists(os.path.join(out_dir, 'config.json')):
        return (idx, name, 0, 'SKIP')

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    t0 = time.time()

    subprocess.run([
        sys.executable, GENERATE_PY,
        '-n', nona_bin,
        '-o', out_dir,
        '-s', '512',
        '--png',
        src_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elapsed = time.time() - t0
    tile_count = 0
    config_path = os.path.join(out_dir, 'config.json')
    if os.path.exists(config_path):
        import json
        with open(config_path) as f:
            cfg = json.load(f)
        cfg['multiRes']['extension'] = 'png'
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
        max_lv = cfg['multiRes']['maxLevel']
        for lv in range(1, max_lv + 1):
            lv_dir = os.path.join(out_dir, str(lv))
            if os.path.isdir(lv_dir):
                tile_count += len([x for x in os.listdir(lv_dir) if x.endswith('.png')])

    return (idx, name, elapsed, tile_count)


def main():
    parser = argparse.ArgumentParser(description='批量生成 Pannellum multires 瓦片')
    parser.add_argument('--input-dir', required=True, help='等矩形全景图目录（含 scene1.png ~ sceneN.png）')
    parser.add_argument('--output-dir', required=True, help='输出瓦片根目录')
    parser.add_argument('--nona', required=True, help='Hugin nona.exe 路径')
    parser.add_argument('--workers', type=int, default=4, help='并行进程数（默认 4）')
    parser.add_argument('--ext', default='.png', help='输入图片扩展名（默认 .png）')
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    out_base = os.path.abspath(args.output_dir)
    nona_bin = os.path.abspath(args.nona)
    os.makedirs(out_base, exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, f'scene*{args.ext}')))
    if not files:
        print(f'错误: {input_dir} 下没有 scene*{args.ext} 文件')
        sys.exit(1)

    def sort_key(f):
        base = os.path.basename(f)
        num = base.replace('scene', '').replace(args.ext, '')
        return int(num) if num.isdigit() else 0

    files.sort(key=sort_key)
    total = len(files)

    print(f'发现 {total} 张全景图')
    print(f'nona: {nona_bin}')
    print(f'瓦片格式: PNG')
    print(f'并行进程: {args.workers}')
    print(f'输出: {out_base}')
    print('=' * 60)
    print('按 Ctrl+C 停止')

    from concurrent.futures import ProcessPoolExecutor, as_completed

    task_args = [(f, i + 1, nona_bin, out_base) for i, f in enumerate(files)]

    t_start = time.time()
    completed, skipped, total_elapsed = 0, 0, 0
    executor = ProcessPoolExecutor(max_workers=args.workers)
    interrupted = False

    try:
        futures = {executor.submit(process_one, arg): arg for arg in task_args}
        for future in as_completed(futures):
            if interrupted:
                break
            try:
                idx, name, elapsed, tiles = future.result(timeout=1800)
            except KeyboardInterrupt:
                print('\n正在停止...')
                interrupted = True
                executor.shutdown(wait=False, cancel_futures=True)
                break

            completed += 1
            if elapsed == 0:
                skipped += 1
                print(f'[{completed:>3}/{total}] {name}  SKIP（已存在）')
            else:
                total_elapsed += elapsed
                avg = total_elapsed / (completed - skipped)
                eta = avg * (total - completed)
                print(f'[{completed:>3}/{total}] {name}  {elapsed:>5.0f}s  {tiles:>4} tiles  剩余 {eta:>5.0f}s', flush=True)
    except KeyboardInterrupt:
        print('\n正在停止...')
        executor.shutdown(wait=False, cancel_futures=True)
    finally:
        executor.shutdown(wait=False)

    t_total = time.time() - t_start
    print('=' * 60)
    print(f'完成! {completed}/{total}  ({skipped} SKIP)  用时 {t_total:.0f}s ({t_total/60:.1f}min)')


if __name__ == '__main__':
    main()
