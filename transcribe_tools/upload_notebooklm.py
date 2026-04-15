#!/usr/bin/env python3
"""
upload_notebooklm - 分割済みMP4ファイルをNotebookLMにアップロードするツール

使い方:
  upload_notebooklm 動画.mp4
  upload_notebooklm 動画.mp4 --name "会議録 2026-04"

  動画_part001.mp4, 動画_part002.mp4 ... が存在すればそれらを全てアップロード。
  分割ファイルがなければ 動画.mp4 をそのままアップロード。

初回のみ事前に認証が必要:
  notebooklm login
"""

import subprocess
import sys
import os
import glob
import argparse
import asyncio


def check_dependencies():
    try:
        import notebooklm  # noqa: F401
    except ImportError:
        print("notebooklm-py をインストール中...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "notebooklm-py[browser]"],
            check=True,
        )
        print("インストール完了\n")


def collect_files(filepath):
    """アップロード対象ファイルを収集する（分割済み優先）"""
    base = os.path.splitext(os.path.abspath(filepath))[0]
    split_files = sorted(glob.glob(f"{base}_part*.mp4"))

    if split_files:
        print(f"分割ファイルを検出: {len(split_files)} 件")
        for f in split_files:
            size_mb = os.path.getsize(f) / 1024 / 1024
            print(f"  {os.path.basename(f)}  ({size_mb:.1f} MB)")
        print()
        return split_files

    print(f"分割ファイルなし → 元ファイルをそのまま使用: {os.path.basename(filepath)}\n")
    return [os.path.abspath(filepath)]


async def upload(files, notebook_name):
    """ノートブックを作成してソースを順番にアップロードする"""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        print(f"[1/2] ノートブック作成中: 「{notebook_name}」")
        nb = await client.notebooks.create(notebook_name)
        print(f"  → 作成完了 (ID: {nb.id})\n")

        print(f"[2/2] ソースをアップロード中... ({len(files)} 件)")
        print("─" * 50)

        for i, filepath in enumerate(files, 1):
            size_mb = os.path.getsize(filepath) / 1024 / 1024
            print(f"  [{i}/{len(files)}] {os.path.basename(filepath)}  ({size_mb:.1f} MB)")
            await client.sources.add_file(nb.id, filepath, wait=True)
            print(f"        完了")

        print("─" * 50)
        return nb


def main():
    parser = argparse.ArgumentParser(
        description="分割済みMP4ファイルをNotebookLMにアップロードします",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "例:\n"
            "  upload_notebooklm 動画.mp4\n"
            "  upload_notebooklm 動画.mp4 --name \"会議録 2026-04\"\n\n"
            "初回のみ事前に認証が必要です:\n"
            "  notebooklm login"
        ),
    )
    parser.add_argument("input", help="MP4ファイルのパス（元ファイル）")
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

    check_dependencies()

    notebook_name = args.name or os.path.splitext(os.path.basename(args.input))[0]

    # 対象ファイルを収集
    files = collect_files(args.input)

    # アップロード
    try:
        nb = asyncio.run(upload(files, notebook_name))
    except Exception as e:
        if "login" in str(e).lower() or "auth" in str(e).lower():
            print("\n認証エラー: 先に以下を実行してください:", file=sys.stderr)
            print("  notebooklm login", file=sys.stderr)
        else:
            print(f"\nエラー: {e}", file=sys.stderr)
        sys.exit(1)

    # 結果表示
    notebook_url = f"https://notebooklm.google.com/notebook/{nb.id}"

    print(f"""
=== 完了 ===
ノートブック : {notebook_name}
ソース数     : {len(files)} 件
URL          : {notebook_url}

次のステップ（マインドマップの作成）:
  1. 上記URLをブラウザで開く
  2. 画面右側の「ノートブックガイド」を開く
  3. 「マインドマップ」をクリック
""")

    try:
        subprocess.Popen(["xdg-open", notebook_url])
    except Exception:
        pass


if __name__ == "__main__":
    main()
