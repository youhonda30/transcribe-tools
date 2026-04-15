#!/usr/bin/env python3
"""
mp4_to_notebooklm - MP4を分割してNotebookLMにアップロードするツール

使い方:
  mp4_to_notebooklm 動画.mp4
  mp4_to_notebooklm 動画.mp4 --name "会議録 2026-04"

内部で以下を順番に実行します:
  1. split_mp4 動画.mp4
  2. upload_notebooklm 動画.mp4

初回のみ事前に認証が必要:
  notebooklm login
"""

import subprocess
import sys
import os
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="MP4を200MB以下に分割してNotebookLMにアップロードします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "例:\n"
            "  mp4_to_notebooklm 動画.mp4\n"
            "  mp4_to_notebooklm 動画.mp4 --name \"会議録 2026-04\"\n\n"
            "初回のみ事前に認証が必要です:\n"
            "  notebooklm login"
        ),
    )
    parser.add_argument("input", help="MP4ファイルのパス")
    parser.add_argument(
        "--name",
        default=None,
        metavar="NAME",
        help="ノートブック名（省略時はファイル名を使用）",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"エラー: ファイルが見つかりません: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 1. 分割
    print("=" * 50)
    print("STEP 1: split_mp4")
    print("=" * 50)
    result = subprocess.run(["split_mp4", args.input])
    if result.returncode != 0:
        sys.exit(result.returncode)

    # 2. アップロード
    print()
    print("=" * 50)
    print("STEP 2: upload_notebooklm")
    print("=" * 50)
    upload_cmd = ["upload_notebooklm", args.input]
    if args.name:
        upload_cmd += ["--name", args.name]
    result = subprocess.run(upload_cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
