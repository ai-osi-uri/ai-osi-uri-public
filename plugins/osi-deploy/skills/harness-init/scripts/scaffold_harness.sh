#!/usr/bin/env bash
#
# scaffold_harness.sh — harness-init スキルの実体。
# assets/ の4テンプレを TARGET にコピーし、{{...}} を実値で置換して配置する。
# 既存ファイルは OVERWRITE=1 でない限りスキップ（冪等・既存破壊なし）。
#
# 使い方:
#   bash scaffold_harness.sh --target <dir> [options]
#
# options:
#   --target DIR        必須。ハーネスを置くリポジトリのルート
#   --agent-file NAME   AGENTS.md | CLAUDE.md（既定 AGENTS.md）
#   --stack NAME        node | python | static | auto（既定 auto）
#   --install CMD       依存インストールコマンド
#   --verify CMD        フル検証コマンド
#   --start CMD         開発サーバ起動コマンド
#   --test CMD          テストコマンド（AGENTS.md 表示用）
#   --typecheck CMD     型チェックコマンド（AGENTS.md 表示用）
#   --lint CMD          Lint コマンド（AGENTS.md 表示用）
#   --project-name NAME
#   --project-desc DESC
#   --overwrite 0|1     既存ファイルを上書きするか（既定 0）
#   --run-verify 0|1    配置後に init.sh を実行してベースライン検証（既定 0）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

TARGET=""
AGENT_FILE="AGENTS.md"
STACK="auto"
INSTALL_CMD=""
VERIFY_CMD=""
START_CMD=""
TEST_CMD=""
TYPECHECK_CMD=""
LINT_CMD=""
PROJECT_NAME=""
PROJECT_DESC=""
OVERWRITE="0"
RUN_VERIFY="0"

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2;;
    --agent-file) AGENT_FILE="$2"; shift 2;;
    --stack) STACK="$2"; shift 2;;
    --install) INSTALL_CMD="$2"; shift 2;;
    --verify) VERIFY_CMD="$2"; shift 2;;
    --start) START_CMD="$2"; shift 2;;
    --test) TEST_CMD="$2"; shift 2;;
    --typecheck) TYPECHECK_CMD="$2"; shift 2;;
    --lint) LINT_CMD="$2"; shift 2;;
    --project-name) PROJECT_NAME="$2"; shift 2;;
    --project-desc) PROJECT_DESC="$2"; shift 2;;
    --overwrite) OVERWRITE="$2"; shift 2;;
    --run-verify) RUN_VERIFY="$2"; shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

[ -n "$TARGET" ] || { echo "ERROR: --target は必須です" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "ERROR: TARGET が存在しません: $TARGET" >&2; exit 2; }

# ---- スタック自動判定 ----
if [ "$STACK" = "auto" ]; then
  if [ -f "$TARGET/package.json" ]; then STACK="node"
  elif [ -f "$TARGET/pyproject.toml" ] || [ -f "$TARGET/requirements.txt" ]; then STACK="python"
  elif ls "$TARGET"/*.html >/dev/null 2>&1; then STACK="static"
  else STACK="static"; fi
fi

# ---- スタック別フォールバック ----
case "$STACK" in
  node)
    : "${INSTALL_CMD:=npm install}"; : "${VERIFY_CMD:=npm test}"; : "${START_CMD:=npm run dev}"
    : "${TEST_CMD:=npm test}"; : "${TYPECHECK_CMD:=tsc --noEmit}"; : "${LINT_CMD:=eslint .}"
    ;;
  python)
    if [ -f "$TARGET/uv.lock" ]; then : "${INSTALL_CMD:=uv sync}"; else : "${INSTALL_CMD:=pip install -r requirements.txt}"; fi
    : "${VERIFY_CMD:=pytest -x}"; : "${START_CMD:=【TODO: 起動コマンド】}"
    : "${TEST_CMD:=pytest -x}"; : "${TYPECHECK_CMD:=mypy src/ --strict}"; : "${LINT_CMD:=ruff check src/}"
    ;;
  static|*)
    : "${INSTALL_CMD:=【TODO: なし or ビルドコマンド】}"; : "${VERIFY_CMD:=【TODO: 任意の検証】}"
    : "${START_CMD:=【TODO: プレビュー / 不要】}"
    : "${TEST_CMD:=【TODO】}"; : "${TYPECHECK_CMD:=【TODO】}"; : "${LINT_CMD:=【TODO】}"
    ;;
esac

# 未指定の AGENTS.md 表示用フィールドは TODO のまま残す
: "${PROJECT_NAME:=【TODO: プロジェクト名】}"
: "${PROJECT_DESC:=【TODO: 1〜2文の概要】}"
: "${TEST_CMD:=【TODO】}"; : "${TYPECHECK_CMD:=【TODO】}"; : "${LINT_CMD:=【TODO】}"

# ---- 置換ヘルパ（区切りに | を使い、値内の | は退避）----
render() {
  # $1=src $2=dst
  sed \
    -e "s|{{PROJECT_NAME}}|${PROJECT_NAME//|/\\|}|g" \
    -e "s|{{PROJECT_DESCRIPTION}}|${PROJECT_DESC//|/\\|}|g" \
    -e "s|{{INSTALL_CMD}}|${INSTALL_CMD//|/\\|}|g" \
    -e "s|{{VERIFY_CMD}}|${VERIFY_CMD//|/\\|}|g" \
    -e "s|{{START_CMD}}|${START_CMD//|/\\|}|g" \
    -e "s|{{TEST_CMD}}|${TEST_CMD//|/\\|}|g" \
    -e "s|{{TYPECHECK_CMD}}|${TYPECHECK_CMD//|/\\|}|g" \
    -e "s|{{LINT_CMD}}|${LINT_CMD//|/\\|}|g" \
    "$1" > "$2"
}

placed=(); skipped=()

place() {
  # $1=asset filename  $2=dest filename
  local src="$ASSETS_DIR/$1" dst="$TARGET/$2"
  if [ -e "$dst" ] && [ "$OVERWRITE" != "1" ]; then
    skipped+=("$2"); return
  fi
  render "$src" "$dst"
  placed+=("$2")
}

place "AGENTS.md"          "$AGENT_FILE"
place "init.sh"            "init.sh"
place "claude-progress.md" "claude-progress.md"
place "feature_list.json"  "feature_list.json"

# feature_list.json は置換不要なのでそのままコピー（既に render 済みだが {{}} を含まないので無害）
chmod +x "$TARGET/init.sh" 2>/dev/null || true

# ---- 残 TODO カウント ----
todo_count=0
[ -f "$TARGET/$AGENT_FILE" ] && todo_count=$(grep -c '【TODO' "$TARGET/$AGENT_FILE" || true)

echo "=== harness-init 完了 ==="
echo "TARGET   : $TARGET"
echo "STACK    : $STACK"
echo "配置     : ${placed[*]:-（なし）}"
echo "スキップ : ${skipped[*]:-（なし）}"
echo "埋めた値 : INSTALL=[$INSTALL_CMD] VERIFY=[$VERIFY_CMD] START=[$START_CMD]"
echo "残TODO   : $AGENT_FILE 内に ${todo_count} 箇所"
echo "次の一手 : feature_list.json に最初の機能を1件書き、./init.sh でベースライン検証を通す"

if [ "$RUN_VERIFY" = "1" ]; then
  echo ""
  echo "--- ベースライン検証 (./init.sh) ---"
  ( cd "$TARGET" && ./init.sh ) || { echo "❌ ベースライン検証に失敗。新機能着手前に修復が必要。"; exit 1; }
fi
