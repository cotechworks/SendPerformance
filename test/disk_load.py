"""T-011用のディスク負荷。専用一時ファイルだけを使用する。"""
import argparse
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import time


MIB = 1024 * 1024


def run_load(directory, seconds=30, size_mib=128, max_write_mib=1024):
    """時間または累積書き込み上限まで実行し、一時ファイルを必ず後片付けする。"""
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError('directoryは既存のフォルダを指定してください')
    if not math.isfinite(seconds) or not 0 < seconds <= 3600:
        raise ValueError('secondsは0より大きく3600以下で指定してください')
    if not 1 <= size_mib <= 4096:
        raise ValueError('size-mibは1～4096で指定してください')
    if not size_mib <= max_write_mib <= 65536:
        raise ValueError('max-write-mibはsize-mib以上、65536以下で指定してください')
    size = size_mib * MIB
    limit = max_write_mib * MIB
    if shutil.disk_usage(directory).free < size + 64 * MIB:
        raise ValueError('一時ファイル容量に加え64MiB以上の空き容量が必要です')

    payload = os.urandom(64 * 1024)
    rng = random.Random()
    written = read = 0
    start = time.monotonic()
    deadline = start + seconds
    next_report = start + 1
    path = None
    interrupted = False
    print(f'対象: {directory}', flush=True)
    print(f'上限: {seconds:g}秒 / 一時ファイル{size_mib}MiB / 累積書込{max_write_mib}MiB', flush=True)
    try:
        # NamedTemporaryFileで既存ファイルと衝突しない名前を排他的に確保する。
        with tempfile.NamedTemporaryFile(
            prefix='sendperformance-load-', suffix='.tmp',
            dir=directory, buffering=0, delete=False,
        ) as stream:
            path = Path(stream.name)
            print(f'一時ファイル: {path}', flush=True)
            # 実データで初期化する。時間上限を超えるまで初期化を続けない。
            while written < size and time.monotonic() < deadline:
                count = stream.write(payload[:min(len(payload), size - written)])
                if not count:
                    raise OSError('書き込みが進みません')
                written += count
                os.fsync(stream.fileno())
            initialized = written
            # 初期化済み範囲を読み書きする。書き込みごとにOSへ同期する。
            while initialized > 0 and written < limit and time.monotonic() < deadline:
                block = min(len(payload), initialized, limit - written)
                offset = rng.randrange(0, initialized - block + 1)
                stream.seek(offset)
                if rng.randrange(2):
                    count = stream.write(payload[:block])
                    if not count:
                        raise OSError('書き込みが進みません')
                    written += count
                    os.fsync(stream.fileno())
                else:
                    read += len(stream.read(block))
                now = time.monotonic()
                if now >= next_report:
                    print(f'{now - start:.1f}秒: 書込 {written / MIB:.1f}MiB / 読込 {read / MIB:.1f}MiB', flush=True)
                    next_report = now + 1
    except KeyboardInterrupt:
        interrupted = True
        print('中断要求を受け付けました。', flush=True)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
            print('一時ファイル削除済み', flush=True)
    result = {
        'written_bytes': written, 'read_bytes': read,
        'elapsed_seconds': time.monotonic() - start,
        'interrupted': interrupted,
    }
    print(f"終了: {result['elapsed_seconds']:.1f}秒 / 書込 {written / MIB:.1f}MiB / 読込 {read / MIB:.1f}MiB", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description='T-011用ディスク負荷。Ctrl+Cで停止する。')
    parser.add_argument('--directory', type=Path, default=Path(tempfile.gettempdir()),
                        help='負荷対象の既存フォルダ（既定: OSの一時フォルダ）')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--size-mib', type=int, default=128)
    parser.add_argument('--max-write-mib', type=int, default=1024)
    args = parser.parse_args()
    try:
        run_load(args.directory, args.seconds, args.size_mib, args.max_write_mib)
    except (OSError, ValueError) as error:
        parser.exit(1, f'エラー: {error}\n')


if __name__ == '__main__':
    main()