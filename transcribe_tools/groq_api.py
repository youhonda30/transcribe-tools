#!/usr/bin/env python3
"""
transcribe-groq: Groq API (whisper-large-v3-turbo) で文字起こし
使い方: transcribe-groq <ファイルパス> [--output_dir <出力先>]
環境変数: GROQ_API_KEY
"""

import sys
import os
import re
import argparse
import tempfile
import subprocess
import time
from pathlib import Path

GROQ_LIMIT_MB = 24      # 安全マージン込み24MB
CHUNK_MINUTES = 15      # 分割単位（分）
MAX_RETRIES = 5         # レート制限リトライ上限


def to_mp3(input_file: Path, output_path: str) -> Path:
    subprocess.run(
        ["ffmpeg", "-i", str(input_file), "-vn", "-ar", "16000", "-ac", "1",
         "-b:a", "32k", output_path, "-y"],
        check=True, capture_output=True
    )
    return Path(output_path)


def get_duration_seconds(audio_file: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_file)],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def split_audio(audio_file: Path, chunk_seconds: int, tmp_dir: str) -> list[Path]:
    pattern = os.path.join(tmp_dir, "chunk_%03d.mp3")
    subprocess.run(
        ["ffmpeg", "-i", str(audio_file),
         "-f", "segment", "-segment_time", str(chunk_seconds),
         "-c", "copy", pattern, "-y"],
        check=True, capture_output=True
    )
    return sorted(Path(tmp_dir).glob("chunk_*.mp3"))


def parse_wait_seconds(error_message: str) -> int:
    """エラーメッセージから待機秒数を抽出 (例: 'try again in 1m58s')"""
    match = re.search(r'try again in (?:(\d+)m)?(\d+)s', str(error_message))
    if match:
        minutes = int(match.group(1) or 0)
        seconds = int(match.group(2) or 0)
        return minutes * 60 + seconds + 5  # 5秒の余裕
    return 120


def transcribe_chunk(client, chunk_path: Path, chunk_index: int, total: int) -> str:
    """1チャンクを送信（レート制限時は自動待機してリトライ）"""
    from groq import RateLimitError

    size_mb = chunk_path.stat().st_size / (1024 * 1024)
    print(f"  [{chunk_index}/{total}] {chunk_path.name} ({size_mb:.1f}MB) 送信中...", end="", flush=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with open(chunk_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(chunk_path.name, f),
                    model="whisper-large-v3-turbo",
                    language="ja",
                    response_format="text"
                )
            print(" 完了")
            if chunk_index < total:
                time.sleep(1)
            return str(result).strip()

        except RateLimitError as e:
            wait_sec = parse_wait_seconds(str(e))
            print(f"\n  レート制限（試行 {attempt}/{MAX_RETRIES}）。{wait_sec}秒待機中...", end="", flush=True)
            for remaining in range(wait_sec, 0, -10):
                time.sleep(min(10, remaining))
                print(f" {remaining}秒...", end="", flush=True)
            print(" 再試行")

    raise RuntimeError(f"チャンク [{chunk_index}/{total}] が {MAX_RETRIES} 回失敗しました")


def main():
    parser = argparse.ArgumentParser(description="Groq API で音声/動画を文字起こし")
    parser.add_argument("input", help="入力ファイルパス（mp4/mp3/wav等）")
    parser.add_argument("--output_dir", default=None, help="出力先ディレクトリ（省略時は入力ファイルと同じ場所）")
    parser.add_argument("--chunk_min", type=int, default=CHUNK_MINUTES,
                        help=f"分割単位（分）デフォルト: {CHUNK_MINUTES}")
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"エラー: ファイルが見つかりません: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / (input_file.stem + ".txt")
    progress_file = output_dir / (input_file.stem + ".progress.txt")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("エラー: GROQ_API_KEY が設定されていません")
        print("  export GROQ_API_KEY='your_key_here'")
        sys.exit(1)

    try:
        from groq import Groq
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "groq"], check=True)
        from groq import Groq

    print(f"文字起こし中: {input_file.name}")
    print(f"モデル: whisper-large-v3-turbo (Groq)\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Step1: mp3変換
        size_mb = input_file.stat().st_size / (1024 * 1024)
        print(f"Step1: MP3変換中 (元ファイル: {size_mb:.0f}MB)...")
        mp3_path = to_mp3(input_file, os.path.join(tmp_dir, "audio.mp3"))
        mp3_mb = mp3_path.stat().st_size / (1024 * 1024)
        print(f"       変換後: {mp3_mb:.1f}MB")

        # Step2: 必要なら分割
        if mp3_mb <= GROQ_LIMIT_MB:
            chunks = [mp3_path]
        else:
            duration = get_duration_seconds(mp3_path)
            chunk_sec = args.chunk_min * 60
            n_chunks = int(duration / chunk_sec) + 1
            print(f"Step2: 分割中 (合計 {duration/60:.0f}分 → 約{n_chunks}チャンク × {args.chunk_min}分)...")
            chunks = split_audio(mp3_path, chunk_sec, tmp_dir)
            print(f"       {len(chunks)}チャンクに分割完了\n")

        # Step3: 文字起こし（途中結果を逐次保存）
        client = Groq(api_key=api_key)
        progress_file.write_text("", encoding="utf-8")

        for i, chunk in enumerate(chunks, 1):
            text = transcribe_chunk(client, chunk, i, len(chunks))
            with open(progress_file, "a", encoding="utf-8") as pf:
                pf.write(text + "\n")

    # Step4: 途中結果ファイルを最終出力にリネーム
    progress_file.rename(output_file)
    full_text = output_file.read_text(encoding="utf-8")
    print(f"\n完了: {output_file}")
    print(f"文字数: {len(full_text)} 文字")


if __name__ == "__main__":
    main()
