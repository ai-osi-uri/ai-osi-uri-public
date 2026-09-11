#!/usr/bin/env bash
# preflight.sh — デプロイ前プリフライト（read-only）。機械判定できる項目のみ実行し JSON を出す。
# 使い方: preflight.sh <aws-static|aws-ecs|vercel> <project_dir> [--domain d] [--billing stripe] [--credentials file]
set -uo pipefail
export AWS_PROFILE="${AWS_PROFILE:-ai-osi-uri}"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 が必要です" >&2; exit 2; }
[ $# -ge 2 ] || { echo "ERROR: target と project_dir が必要です" >&2; exit 2; }
TARGET="$1"; DIR="$2"; shift 2
case "$TARGET" in aws-static|aws-ecs|vercel) ;; *) echo "ERROR: 不明な target: $TARGET" >&2; exit 2 ;; esac
[ -d "$DIR" ] || { echo "ERROR: project_dir が存在しません: $DIR" >&2; exit 2; }
DIR="$(cd "$DIR" && pwd)"
DOMAIN=""; BILLING=""; CREDENTIALS_FILE="${DEPLOY_CREDENTIALS_FILE:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --domain) [ $# -ge 2 ] || exit 2; DOMAIN="$2"; shift 2 ;;
    --billing) [ $# -ge 2 ] || exit 2; BILLING="$2"; shift 2 ;;
    --credentials) [ $# -ge 2 ] || exit 2; CREDENTIALS_FILE="$2"; shift 2 ;;
    *) echo "ERROR: 不明なオプション: $1" >&2; exit 2 ;;
  esac
done

checks=(); blocking=()
json_string() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$1"
}
add() { # id status detail
  checks+=("{\"id\":$(json_string "$1"),\"status\":$(json_string "$2"),\"detail\":$(json_string "${3:-}")}")
  [ "$2" = "FAIL" ] && blocking+=("$(json_string "$1")")
  return 0
}

needs_aws=false
[ "$TARGET" != "vercel" ] && needs_aws=true
[ -n "$DOMAIN" ] && needs_aws=true
if [ "$needs_aws" = true ]; then
  if command -v aws >/dev/null 2>&1 \
    && acct=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
    if [ -n "${EXPECTED_AWS_ACCOUNT_ID:-}" ] && [ "$acct" != "$EXPECTED_AWS_ACCOUNT_ID" ]; then
      add aws-auth FAIL "account ${acct}（期待値: ${EXPECTED_AWS_ACCOUNT_ID}）"
    else
      add aws-auth PASS "account $acct"
    fi
  else
    add aws-auth FAIL "aws sts 失敗 → setup-deploy-environment / AWS_PROFILE"
  fi
fi

if [ -z "$CREDENTIALS_FILE" ] && [ -f "$DIR/.deploy-credentials/.env" ]; then
  CREDENTIALS_FILE="$DIR/.deploy-credentials/.env"
fi
has_credential() {
  local key="$1"
  [ -n "${!key:-}" ] && return 0
  [ -n "$CREDENTIALS_FILE" ] && [ -f "$CREDENTIALS_FILE" ] \
    && grep -Eq "^[[:space:]]*${key}=[^[:space:]].*" "$CREDENTIALS_FILE"
}
missing_credentials=()
for key in GITHUB_PAT GITHUB_USERNAME; do
  has_credential "$key" || missing_credentials+=("$key")
done
if [ "$TARGET" = "vercel" ]; then
  has_credential VERCEL_TOKEN || missing_credentials+=("VERCEL_TOKEN")
fi
if [ ${#missing_credentials[@]} -eq 0 ]; then
  add deploy-credentials PASS "${CREDENTIALS_FILE:-environment}"
else
  add deploy-credentials FAIL "未設定: ${missing_credentials[*]}（--credentials または環境変数）"
fi

if git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1; then
  if [ -z "$(git -C "$DIR" status --porcelain)" ]; then
    if git -C "$DIR" rev-parse '@{u}' >/dev/null 2>&1; then
      read -r behind ahead < <(git -C "$DIR" rev-list --left-right --count '@{u}...HEAD')
      if [ "$behind" = "0" ] && [ "$ahead" = "0" ]; then
        add git-pushed PASS "clean & upstream同期済み"
      else
        add git-pushed WARN "upstreamとの差分: behind=$behind ahead=$ahead"
      fi
    else
      add git-pushed WARN "upstream 未設定 → gh-create-repo-and-push"
    fi
  else add git-pushed WARN "未コミットの変更あり"; fi
else add git-pushed WARN "git リポジトリ外"; fi

# ---- 非機能の決定（nonfunctional.yaml）: 空欄=決めていない → FAIL / 未検証 → WARN ----
# yaml パーサに依存しない（PyYAML 不在でも動く）ため、トップレベルキーと decided/verified を行単位で読む。
if [ -f "$DIR/nonfunctional.yaml" ]; then
  nf_out=$(python3 - "$DIR/nonfunctional.yaml" <<'PY'
import re, sys
keys = ["recovery","load","observability","access","change","outside"]
lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
sec = None; decided = {}; verified = {}; defaults = []
for raw in lines:
    line = raw.split("#",1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
    if not line.strip(): continue
    m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
    if m:
        sec = m.group(1); continue
    if sec in keys:
        m = re.match(r"^\s+(decided|verified):\s*(.*)$", line)
        if m:
            (decided if m.group(1)=="decided" else verified)[sec] = m.group(2).strip()
        elif sec in decided and decided[sec] in ("", "|", ">", "|-", ">-"):
            decided[sec] = line.strip()  # 複数行の先頭
    elif sec == "accepted_defaults":
        m = re.match(r"^\s*-\s*(.*)$", line)
        if m: defaults.append(m.group(1).strip())
undecided = [k for k in keys if not decided.get(k) or "TODO" in decided.get(k,"") or decided.get(k) in ("null","~")]
unverified = [k for k in keys if k not in undecided and (not verified.get(k) or verified.get(k) in ("null","~") or "TODO" in verified.get(k,""))]
bad_defaults = [d for d in defaults if not d or "TODO" in d]
print("UNDECIDED=" + ",".join(undecided))
print("UNVERIFIED=" + ",".join(unverified))
print("BADDEFAULTS=" + str(len(bad_defaults)))
PY
)
  nf_undecided=$(printf '%s\n' "$nf_out" | sed -n 's/^UNDECIDED=//p')
  nf_unverified=$(printf '%s\n' "$nf_out" | sed -n 's/^UNVERIFIED=//p')
  nf_baddef=$(printf '%s\n' "$nf_out" | sed -n 's/^BADDEFAULTS=//p')
  if [ -n "$nf_undecided" ]; then
    add nonfunctional-decided FAIL "決めていない項目: ${nf_undecided} → nonfunctional.yaml の decided を埋める（「不要」も決定）"
  elif [ "${nf_baddef:-0}" != "0" ]; then
    add nonfunctional-decided FAIL "accepted_defaults に【TODO】が残っている（黙って選ばれた既定値を決定として書くか、項目ごと消す）"
  else
    add nonfunctional-decided PASS
  fi
  if [ -n "$nf_unverified" ]; then
    add nonfunctional-verified WARN "未検証: ${nf_unverified}（公開後に実際に確かめて verified を埋める。recovery/change は「戻す」を一度やる）"
  else
    add nonfunctional-verified PASS
  fi
else
  add nonfunctional-decided FAIL "nonfunctional.yaml が無い → harness-init で配置して埋める"
fi

case "$TARGET" in
  aws-static|aws-ecs)
    if ls "$DIR"/*.tf >/dev/null 2>&1; then
      if command -v terraform >/dev/null 2>&1 \
        && (cd "$DIR" && terraform validate -no-color >/dev/null 2>&1); then
        add tf-validate PASS
      else
        add tf-validate FAIL "terraform 未導入、または terraform validate が通らない"
      fi
      grep -Rqs 'backend[[:space:]]*"s3"' "$DIR"/*.tf \
        && add s3-backend PASS \
        || add s3-backend FAIL "backend \"s3\" 未設定 → tf-state-backend を先に"
    else
      add tf-validate WARN "*.tf 無し（静的成果物直上げ？）"
    fi
    if [ "$TARGET" = "aws-ecs" ]; then
      [ -f "$DIR/Dockerfile" ] && add dockerfile PASS || add dockerfile FAIL "Dockerfile が無い"
      grep -qiE 'HEALTHCHECK|/healthz|/health' "$DIR/Dockerfile" 2>/dev/null \
        && add healthcheck PASS || add healthcheck WARN "ヘルスチェック定義が見当たらない"
    fi
    ;;
  vercel)
    [ -f "$DIR/.vercel/project.json" ] && add vercel-linked PASS \
      || add vercel-linked WARN "vercel 未リンク（.vercel/project.json 無し）"
    ;;
esac

if [ -n "$DOMAIN" ]; then
  route53_script="$(cd "$(dirname "$0")" && pwd)/../../aws-route53/scripts/route53.sh"
  if [ -x "$route53_script" ] && hz="$("$route53_script" zone "$DOMAIN" 2>/dev/null)"; then
    add hosted-zone PASS "$hz for ${DOMAIN%.}"
  else
    add hosted-zone FAIL "Hosted Zone が無い（${DOMAIN%.}）→ aws-route53 / AWS_PROFILE確認"
  fi
  [ "$TARGET" = "aws-static" ] && add acm-region WARN "ACM は us-east-1 で発行のこと"
fi

if [ "$BILLING" = "stripe" ]; then
  miss=""
  for k in STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET NEXT_PUBLIC_STRIPE_PRICE_ID; do
    [ -z "${!k:-}" ] && miss="${miss:+$miss,}$k"
  done
  [ -z "$miss" ] && add stripe-env PASS || add stripe-env WARN "env 未設定: $miss"
fi

result="PASS"; [ ${#blocking[@]} -gt 0 ] && result="FAIL"
printf '{"target":"%s","result":"%s","checks":[%s],"blocking":[%s]}\n' \
  "$(printf '%s' "$TARGET")" "$result" \
  "$(IFS=,; echo "${checks[*]}")" \
  "$(IFS=,; echo "${blocking[*]:-}")"
[ "$result" = "PASS" ]
