#!/usr/bin/env bash
#
# init.sh — ハーネスの「環境サブシステム」起動スクリプト
# 依存インストール → 検証 → 起動コマンド表示を一発で行う。
#
# 使い方:
#   ./init.sh                       （セットアップ＋検証まで）
#   RUN_START_COMMAND=1 ./init.sh   （検証後そのまま起動）
#
# 検証(VERIFY_CMD)が失敗したら、ここで停止する。
# エージェントは新しい機能に着手する前に、まずこのベースラインを直すこと。

set -euo pipefail

# ===== harness-init が埋める3変数（手で直してもよい）=====================
INSTALL_CMD="{{INSTALL_CMD}}"
VERIFY_CMD="{{VERIFY_CMD}}"
START_CMD="{{START_CMD}}"
# =======================================================================

echo "=============================================="
echo " init.sh"
echo " 作業ディレクトリ: $(pwd)"
echo "=============================================="

echo ""
echo "[1/3] 依存をインストール中..."
eval "$INSTALL_CMD"

echo ""
echo "[2/3] 検証を実行中..."
if ! eval "$VERIFY_CMD"; then
  echo ""
  echo "❌ 検証に失敗しました。ベースラインが壊れています。"
  echo "   新機能に着手する前に、まずこれを直してください。"
  exit 1
fi
echo "✅ 検証に成功しました。"

echo ""
echo "[3/3] 起動コマンド:"
echo "   $START_CMD"

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo ""
  echo "RUN_START_COMMAND=1 のため起動します..."
  eval "$START_CMD"
else
  echo ""
  echo "（起動するには: RUN_START_COMMAND=1 ./init.sh）"
fi
