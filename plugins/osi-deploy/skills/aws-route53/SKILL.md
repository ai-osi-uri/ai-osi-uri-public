---
name: aws-route53
description: AI OSI URI の AWS アカウント上の Route 53 ホストゾーンに対して、アプリの初回デプロイとは独立に DNS レコードを操作する atomic スキル。親ドメインを含むホストゾーンの検索、任意レコード（A / AAAA / CNAME / TXT / MX / NS / CAA / alias）の追加・更新・削除、サブドメインの発行、メール系レコード（SPF / DKIM / DMARC）、ドメイン所有権確認用 TXT、他サービスへ向ける CNAME、CloudFront / ALB への alias、変更の反映待ち（INSYNC）と `dig` 検証までを行う。同梱の `scripts/route53.sh`（zone / list / get / upsert / delete / wait）で実働し、追加・更新は冪等な UPSERT、削除は現在値の取得と明示確認を必須にする。「サブドメインを追加して」「◯◯.example.com を作って」「Route53 にレコードを足して」「TXT レコードで所有権確認したい」「SPF/DKIM を設定して」「このドメインを別サービスに向けたい」「CNAME を張って」「DNS を書き換えて」「ネームサーバーを確認して」「反映されたか確認して」など、既存ホストゾーンへの DNS 操作全般で発動する。ホストゾーン（ドメイン）自体の新規購入・移管は対象外。アプリ初回公開時の自ドメイン用 ACM 検証 + alias 作成は `aws-static-deploy` / `create-app` が内部で行うので、そちらの初回フローと混同しないこと（本スキルは「既にあるゾーンへ独立にレコードを足す/直す」専用）。認証（AWS_PROFILE）の登録は `setup-deploy-environment` の役割。日本語の AI OSI URI デプロイ運用に特化。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
---

# Route 53 DNS 管理（atomic）

自社 AWS アカウントの **既存ホストゾーン**に対して、アプリのデプロイとは切り離して
DNS レコードを操作する atomic スキル。`aws-static-deploy` が「新規サイトを公開する
ついでに自ドメインの ACM 検証 CNAME と alias を張る」のに対し、本スキルは

- 追加のサブドメイン発行（`api.example.com` → ALB、`docs.example.com` → CloudFront 等）
- 他サービス連携用レコード（Google/Microsoft の所有権確認 TXT、SendGrid の CNAME 等）
- メール認証（SPF / DKIM / DMARC）
- 既存レコードの付け替え・削除

といった **「もう存在するゾーンへ、独立にレコードを足す／直す／消す」** を担当する。

> ゾーン（ドメイン）そのものの新規取得・レジストラ移管は扱わない。
> レコードは常に **UPSERT（冪等）**。同じ内容を何度流しても安全。

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `DOMAIN` または `ZONE_ID` | ✅ | どちらかでゾーンを特定。`DOMAIN` 指定時は自動で Hosted Zone を逆引き |
| `ACTION` | ✅ | `zone` / `list` / `get` / `upsert` / `delete` / `wait` のいずれか |
| `RECORD_NAME` | upsert/delete で必須 | 例 `api.example.com`（末尾ドットは不要） |
| `RECORD_TYPE` | upsert/delete で必須 | `A` / `AAAA` / `CNAME` / `TXT` / `MX` / `CAA` / `NS` |
| `RECORD_VALUE` | upsert で必須 | 値。TXT は自動で `"..."` 引用。複数値は `--value` を繰り返す |
| `TTL` | 任意（既定 300） | alias の場合は無視 |
| `ALIAS_TARGET` / `ALIAS_ZONE_ID` | alias 時 | CloudFront（`Z2FDTNDATAQYW2`）や ALB へ向ける場合 |

認証は AWS プロファイル `ai-osi-uri`（`~/.aws`）を使用。Route 53 は**グローバル**なので
リージョン指定は不要。破壊的操作（`delete`）は必ず対象レコードを表示して確認を取る。

---

## 手順

### Step 0: 認証とゾーン特定
```bash
export AWS_PROFILE=ai-osi-uri
aws sts get-caller-identity --query Account --output text   # どのアカウントか明示

# DOMAIN からゾーンを逆引き（親ドメインを含めて最長一致）
HZID=$(scripts/route53.sh zone "$DOMAIN")
```
`NoSuchHostedZone` / 空の場合は「このアカウントに `$DOMAIN` のゾーンが無い」ことを
明示し、`ZONE_ID` を直接もらうか、ゾーンを持つアカウントかを確認する。

### Step 1: 現状確認（何を触るか見せる）
```bash
scripts/route53.sh list "$HZID"                 # 既存レコード一覧
scripts/route53.sh get "$HZID" "$RECORD_NAME" "$RECORD_TYPE"   # 対象の現在値
```
**upsert / delete の前に必ず現在値を提示**し、上書き・削除して良いか確認する。

### Step 2: 変更適用（冪等 UPSERT）
```bash
# 例: api サブドメインを ALB へ alias
scripts/route53.sh upsert "$HZID" "api.example.com" A \
  --alias "$ALB_DNS" "$ALB_ZONE_ID"

# 例: 所有権確認 TXT
scripts/route53.sh upsert "$HZID" "example.com" TXT "google-site-verification=xxxx"

# 例: 外部サービスへ CNAME
scripts/route53.sh upsert "$HZID" "mail.example.com" CNAME "sendgrid.net" --ttl 300

# 例: 複数の MX 値
scripts/route53.sh upsert "$HZID" "example.com" MX \
  --value "10 mx1.example.net" --value "20 mx2.example.net" --ttl 300
```

削除は Step 1 で表示した現在値についてユーザーの明示承認を得てから実行する。
```bash
scripts/route53.sh delete "$HZID" "old.example.com" CNAME --yes
```

### Step 3: 反映待ちと検証
```bash
scripts/route53.sh wait "$CHANGE_ID"            # ステータスが INSYNC になるまで
dig +short "$RECORD_NAME" "$RECORD_TYPE" @1.1.1.1   # 公開DNSで実際に引けるか
```
TXT / MX は伝播に数分かかる。`dig` が期待値を返したら完了とみなす。

### Step 4: 出力
以下の JSON を返す。
```json
{
  "zone_id": "Z...",
  "action": "upsert",
  "record": { "name": "api.example.com", "type": "A", "value": "<alias:ALB>" },
  "change_id": "/change/C...",
  "status": "INSYNC",
  "verified_by_dig": true
}
```

---

## やらないこと（境界）

- **ドメインの新規購入 / レジストラ移管** … Route 53 Domains は別領域。人間に依頼。
- **アプリ初回公開の自ドメイン設定** … ACM 発行 + CloudFront alias は
  `aws-static-deploy` / `create-app` が初回フローで実施する。二重に張らない。
- **ゾーンの削除** … 事故が重いので本スキルでは行わない（必要時は個別に人間確認）。
- **他アカウントのゾーン操作** … `AWS_PROFILE` のアカウント内のみ。

## 落とし穴

| 事象 | 原因 | 対処 |
| --- | --- | --- |
| `dig` に出ない | 伝播遅延 / TTL | `wait` で INSYNC 確認後、数分待って再確認 |
| CNAME を apex に張れない | 仕様（apex は CNAME 不可） | apex は **alias A** を使う（`--alias`） |
| alias が効かない | `ALIAS_ZONE_ID` 誤り | CloudFront は固定 `Z2FDTNDATAQYW2`、ALB はリージョン別 |
| TXT が壊れる | 引用不足 | 値は必ず `"..."` で囲む（スクリプトが自動処理） |
