#!/usr/bin/env bash
# 別マシンへのセットアップスクリプト
# 使い方: bash setup.sh

set -euo pipefail

echo "=== transcribe-tools セットアップ ==="

# --- システム依存: ffmpeg ---
if ! command -v ffmpeg &>/dev/null; then
    echo "[1/3] ffmpeg をインストール中..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y ffmpeg
    elif command -v brew &>/dev/null; then
        brew install ffmpeg
    else
        echo "  ※ ffmpeg を手動でインストールしてください: https://ffmpeg.org/download.html"
    fi
else
    echo "[1/3] ffmpeg: 既インストール済み ($(ffmpeg -version 2>&1 | head -1))"
fi

# --- Python パッケージ（Pythonツール群 + 依存ライブラリ）---
echo "[2/3] Python パッケージをインストール中..."
pip install --upgrade pip
pip install -e "$(dirname "$0")[notebooklm]"

# --- 動作確認 ---
echo "[3/3] 動作確認..."
for cmd in transcribe-ffmpeg transcribe-groq transcribe-faster split_mp4 mp4_to_notebooklm upload_notebooklm; do
    if command -v "$cmd" &>/dev/null; then
        echo "  ✓ $cmd"
    else
        echo "  ✗ $cmd — PATH に ~/.local/bin が含まれているか確認してください"
    fi
done

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "【GROQ_API_KEY の設定】（transcribe-groq を使う場合）"
echo "  ~/.bashrc または ~/.zshrc に以下を追加:"
echo "  export GROQ_API_KEY='your_key_here'"
