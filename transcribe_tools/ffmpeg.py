#!/usr/bin/env python3
"""
transcribe-ffmpeg: ffmpeg で mp3 変換 → whisper で文字起こし（軽量・安定版）
使い方: transcribe-ffmpeg <ファイルパス> [--model small] [--output_dir <出力先>]
"""

import sys
import os
import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="ffmpeg変換 + whisper で文字起こし")
    parser.add_argument("input", help="入力ファイルパス（mp4/mp3/wav等）")
    parser.add_argument(
        "--model", default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="whisper モデルサイズ (default: small)"
    )
    parser.add_argument("--output_dir", default=None, help="出力先ディレクトリ（省略時は入力ファイルと同じ場所）")
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"エラー: ファイルが見つかりません: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # whisper コマンド確認
    whisper_path = subprocess.run(["which", "whisper"], capture_output=True, text=True).stdout.strip()
    if not whisper_path:
        print("エラー: whisper コマンドが見つかりません")
        print("  pip install openai-whisper")
        sys.exit(1)

    # ffmpeg 確認
    ffmpeg_path = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True).stdout.strip()
    if not ffmpeg_path:
        print("エラー: ffmpeg が見つかりません")
        print("  sudo apt install ffmpeg")
        sys.exit(1)

    # mp3 に変換（音声のみ抽出・軽量化）
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    tmp_mp3 = Path(tmp.name)

    try:
        print(f"MP3変換中: {input_file.name}")
        subprocess.run(
            ["ffmpeg", "-i", str(input_file), "-vn", "-ar", "16000", "-ac", "1", str(tmp_mp3), "-y"],
            check=True, capture_output=True
        )
        size_mb = tmp_mp3.stat().st_size / (1024 * 1024)
        print(f"変換完了: {size_mb:.1f}MB\n")

        # whisper 実行
        print(f"文字起こし中 (モデル: {args.model})...")
        subprocess.run(
            ["whisper", str(tmp_mp3),
             "--language", "Japanese",
             "--model", args.model,
             "--output_format", "txt",
             "--output_dir", str(output_dir)],
            check=True
        )

        # 出力ファイル名をオリジナルのファイル名に変更
        tmp_txt = output_dir / (tmp_mp3.stem + ".txt")
        final_txt = output_dir / (input_file.stem + ".txt")
        if tmp_txt.exists():
            tmp_txt.rename(final_txt)
            print(f"\n完了: {final_txt}")
        else:
            print(f"\n完了（出力先: {output_dir}）")

    finally:
        if tmp_mp3.exists():
            os.unlink(tmp_mp3)


if __name__ == "__main__":
    main()
