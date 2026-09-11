#!/usr/bin/env bash
# route53.sh — AI OSI URI 用 Route 53 レコード操作ヘルパ（冪等 UPSERT）
# 認証は AWS_PROFILE（既定 ai-osi-uri）。Route 53 はグローバルなのでリージョン不要。
#
# 使い方:
#   route53.sh zone <domain>                         # domain の Hosted Zone ID を逆引き
#   route53.sh list <zone_id>                         # レコード一覧
#   route53.sh get  <zone_id> <name> <type>           # 特定レコードの現在値
#   route53.sh upsert <zone_id> <name> <type> <value> [--ttl N]
#   route53.sh upsert <zone_id> <name> A --alias <target_dns> <target_zone_id>
#   route53.sh delete <zone_id> <name> <type> --yes
#   route53.sh wait  <change_id>                       # INSYNC まで待機
#
# upsert / delete は change_id を stdout に出す（wait に渡せる）。
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-ai-osi-uri}"

die() { echo "ERROR: $*" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || die "python3 が必要です"

cmd="${1:-}"; shift || true

normalize_zone_id() {
  printf '%s' "${1#/hostedzone/}"
}

apply() {
  local action="$1" zone="$2" name="$3" type="$4"; shift 4
  local ttl=300 alias_target="" alias_zone="" evaluate_health=false
  local -a values=()
  zone="$(normalize_zone_id "$zone")"
  type="$(printf '%s' "$type" | tr '[:lower:]' '[:upper:]')"
  case "$type" in
    A|AAAA|CAA|CNAME|MX|NAPTR|NS|PTR|SOA|SPF|SRV|TXT) ;;
    *) die "未対応のレコード種別です: $type" ;;
  esac
  while [ $# -gt 0 ]; do
    case "$1" in
      --ttl)   [ $# -ge 2 ] || die "--ttl に値が必要"; ttl="$2"; shift 2 ;;
      --alias) [ $# -ge 3 ] || die "--alias に target_dns と target_zone_id が必要"; alias_target="$2"; alias_zone="$3"; shift 3 ;;
      --evaluate-target-health) evaluate_health=true; shift ;;
      --value) [ $# -ge 2 ] || die "--value に値が必要"; values+=("$2"); shift 2 ;;
      --*) die "不明なオプションです: $1" ;;
      *) values+=("$1"); shift ;;
    esac
  done
  [[ "$ttl" =~ ^[0-9]+$ ]] || die "TTL は0以上の整数で指定してください"

  local batch
  if [ -n "$alias_target" ]; then
    [ -n "$alias_zone" ] || die "--alias には target_dns と target_zone_id の両方が必要"
    [ ${#values[@]} -eq 0 ] || die "alias と通常値は同時に指定できません"
    case "$type" in A|AAAA) ;; *) die "alias は A または AAAA で指定してください" ;; esac
  else
    [ ${#values[@]} -gt 0 ] || die "value が空です"
  fi

  local -a python_args=("$action" "$name" "$type" "$ttl" "$alias_target" "$alias_zone" "$evaluate_health")
  if [ ${#values[@]} -gt 0 ]; then
    python_args+=("${values[@]}")
  fi
  batch="$(
    python3 - "${python_args[@]}" <<'PY'
import json
import sys

action, name, record_type, ttl, alias_target, alias_zone, evaluate_health, *values = sys.argv[1:]
if alias_target:
    record_set = {
        "Name": name,
        "Type": record_type,
        "AliasTarget": {
            "HostedZoneId": alias_zone,
            "DNSName": alias_target,
            "EvaluateTargetHealth": evaluate_health == "true",
        },
    }
else:
    if record_type == "TXT":
        values = [
            value if value.startswith('"') and value.endswith('"')
            else '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
            for value in values
        ]
    record_set = {
        "Name": name,
        "Type": record_type,
        "TTL": int(ttl),
        "ResourceRecords": [{"Value": value} for value in values],
    }
print(json.dumps({"Changes": [{"Action": action, "ResourceRecordSet": record_set}]}))
PY
  )"
  aws route53 change-resource-record-sets \
    --hosted-zone-id "$zone" --change-batch "$batch" \
    --query 'ChangeInfo.Id' --output text
}

case "$cmd" in
  zone)
    dom="${1:?domain}"; dom="${dom%.}"
    aws route53 list-hosted-zones --output json | python3 -c '
import json
import sys

domain = sys.argv[1].rstrip(".").lower()
zones = [
    zone for zone in json.load(sys.stdin).get("HostedZones", [])
    if domain == zone["Name"].rstrip(".").lower()
    or domain.endswith("." + zone["Name"].rstrip(".").lower())
]
if not zones:
    raise SystemExit(f"ERROR: {domain} に一致する Hosted Zone がありません")
longest = max(len(zone["Name"]) for zone in zones)
matches = [zone for zone in zones if len(zone["Name"]) == longest]
if len(matches) != 1:
    raise SystemExit("ERROR: 同名の Hosted Zone が複数あります。ZONE_ID を直接指定してください")
print(matches[0]["Id"].removeprefix("/hostedzone/"))
' "$dom"
    ;;
  list)
    zone="$(normalize_zone_id "${1:?zone_id}")"
    aws route53 list-resource-record-sets --hosted-zone-id "$zone" \
      --query 'ResourceRecordSets[].{Name:Name,Type:Type,TTL:TTL,Value:ResourceRecords[0].Value,Alias:AliasTarget.DNSName}' \
      --output table
    ;;
  get)
    zone="$(normalize_zone_id "${1:?zone_id}")"; name="${2:?name}"
    type="$(printf '%s' "${3:?type}" | tr '[:lower:]' '[:upper:]')"
    aws route53 list-resource-record-sets --hosted-zone-id "$zone" \
      --query "ResourceRecordSets[?Name=='${name%.}.' && Type=='$type']" --output json
    ;;
  upsert) apply UPSERT "$@" ;;
  delete)
    zone="$(normalize_zone_id "${1:?zone_id}")"; name="${2:?name}"
    type="$(printf '%s' "${3:?type}" | tr '[:lower:]' '[:upper:]')"
    [ "${4:-}" = "--yes" ] || die "delete は現在値確認後に --yes を付けて実行してください"
    echo "DELETE 対象を確認してください（現在値）:" >&2
    current="$("$0" get "$zone" "$name" "$type")"
    printf '%s\n' "$current" >&2
    batch="$(
      printf '%s' "$current" | python3 -c '
import json
import sys

records = json.load(sys.stdin)
if len(records) != 1:
    raise SystemExit(f"ERROR: 削除対象は1件必要です（検出: {len(records)}件）")
print(json.dumps({"Changes": [{"Action": "DELETE", "ResourceRecordSet": records[0]}]}))
'
    )"
    aws route53 change-resource-record-sets \
      --hosted-zone-id "$zone" --change-batch "$batch" \
      --query 'ChangeInfo.Id' --output text
    ;;
  wait)
    cid="${1:?change_id}"
    aws route53 wait resource-record-sets-changed --id "$cid" && echo "INSYNC"
    ;;
  *) die "unknown command: '$cmd'（zone|list|get|upsert|delete|wait）" ;;
esac
