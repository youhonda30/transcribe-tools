#!/usr/bin/env python3
"""
split_mp4 - MP4ファイルを200MB以下に分割するツール
使い方: split_mp4 <input.mp4> [--max-size 200]
"""

import subprocess
import sys
import os
import json
import math
import argparse


def get_file_info(filepath):
    """ffprobeでファイルの長さとサイズを取得"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            filepath,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"エラー: ファイルを読み込めません: {filepath}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    size = int(data["format"]["size"])
    return duration, size


def split_video(filepath, max_size_mb=200, target_size_mb=None):
    if not os.path.isfile(filepath):
        print(f"エラー: ファイルが見つかりません: {filepath}", file=sys.stderr)
        sys.exit(1)

    # target_size未指定の場合はmax_sizeの95%を目標にする（キーフレーム分の余裕）
    if target_size_mb is None:
        target_size_mb = int(max_size_mb * 0.95)

    duration, size = get_file_info(filepath)
    max_size_bytes = max_size_mb * 1024 * 1024
    target_size_bytes = target_size_mb * 1024 * 1024

    print(f"ファイル: {os.path.basename(filepath)}")
    print(f"サイズ: {size / 1024 / 1024:.1f} MB")
    print(f"長さ: {duration:.1f} 秒 ({duration / 60:.1f} 分)")
    print(f"目標分割サイズ: {target_size_mb} MB（上限: {max_size_mb} MB）")

    if size <= max_size_bytes:
        print(f"\n{max_size_mb}MB以下のため、分割不要です。")
        return

    num_parts = math.ceil(size / target_size_bytes)
    chunk_duration = duration / num_parts

    print(f"\n{num_parts} 分割で処理します（各 {chunk_duration:.1f} 秒 / 約 {size / num_parts / 1024 / 1024:.1f} MB）\n")

    base_dir = os.path.dirname(os.path.abspath(filepath))
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    ext = os.path.splitext(filepath)[1]

    created_files = []
    for i in range(num_parts):
        start = i * chunk_duration
        output = os.path.join(base_dir, f"{base_name}_part{i + 1:03d}{ext}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", filepath,
            "-ss", str(start),
            "-t", str(chunk_duration),
            "-c", "copy",
            "-avoid_negative_ts", "1",
            output,
        ]

        print(f"[{i + 1}/{num_parts}] 作成中: {os.path.basename(output)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"エラー: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        actual_size = os.path.getsize(output) / 1024 / 1024
        status = "⚠ 超過" if actual_size > max_size_mb else "OK"
        print(f"         完了: {actual_size:.1f} MB [{status}]")
        created_files.append((output, actual_size))

    print("\n=== 完了 ===")
    over_limit = [(f, s) for f, s in created_files if s > max_size_mb]
    if over_limit:
        print(f"警告: 以下のファイルが {max_size_mb}MB を超えています（キーフレームの都合）:")
        for f, s in over_limit:
            print(f"  {os.path.basename(f)}: {s:.1f} MB")
    else:
        print(f"全ファイルが {max_size_mb}MB 以下に収まりました。")


def main():
    parser = argparse.ArgumentParser(
        description="MP4ファイルを指定サイズ以下に分割します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="例:\n  split_mp4 動画.mp4\n  split_mp4 動画.mp4 --max-size 200 --target-size 100",
    )
    parser.add_argument("input", help="分割するMP4ファイルのパス")
    parser.add_argument(
        "--max-size",
        type=int,
        default=200,
        metavar="MB",
        help="1ファイルの上限サイズ（MB）。デフォルト: 200",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=None,
        metavar="MB",
        help="分割の目標サイズ（MB）。未指定の場合はmax-sizeの95%%（200MB上限なら190MB）",
    )
    args = parser.parse_args()

    split_video(args.input, args.max_size, args.target_size)


if __name__ == "__main__":
    main()
