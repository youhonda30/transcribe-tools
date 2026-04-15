#!/usr/bin/env python3
"""
transcribe-faster: faster-whisper でローカル文字起こし（オリジナルの4倍速）
使い方: transcribe-faster <ファイルパス> [--model medium] [--output_dir <出力先>]
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="faster-whisper でローカル文字起こし")
    parser.add_argument("input", help="入力ファイルパス（mp4/mp3/wav等）")
    parser.add_argument(
        "--model", default="medium",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="モデルサイズ (default: medium)"
    )
    parser.add_argument("--output_dir", default=None, help="出力先ディレクトリ（省略時は入力ファイルと同じ場所）")
    parser.add_argument("--timestamps", action="store_true", help="タイムスタンプ付きで出力")
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"エラー: ファイルが見つかりません: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / (input_file.stem + ".txt")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("faster-whisper をインストールしています...")
        subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"], check=True)
        from faster_whisper import WhisperModel

    print(f"モデル読み込み中: {args.model} (初回はダウンロードに時間がかかります)")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"文字起こし中: {input_file.name}")
    segments, info = model.transcribe(str(input_file), language="ja", beam_size=5)

    print(f"言語検出: {info.language} (確度: {info.language_probability:.2f})\n")

    with open(output_file, "w", encoding="utf-8") as f:
        for segment in segments:
            if args.timestamps:
                line = f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text.strip()}"
            else:
                line = segment.text.strip()
            print(line)
            f.write(line + "\n")

    print(f"\n完了: {output_file}")


if __name__ == "__main__":
    main()
