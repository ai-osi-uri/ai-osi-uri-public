---
name: deploy-preflight
description: |
  デプロイを実行する **前** に、失敗しやすい前提条件を機械チェックするゲート。AWS
  認証とアカウント ID、GitHub / Vercel 認証の有無、Terraform validate と **S3 リモート
  backend の有無**（ローカル state だけの orphan 検出）、Dockerfile とヘルスチェック、
  Stripe 鍵、親 Hosted Zone の実在、git の upstream 同期、ACM が us-east-1 か、を
  PASS/FAIL/WARN で返し **FAIL があれば止める**。「デプロイ前チェック」
  「プリフライト」「apply する前に確認して」「なぜデプロイが失敗するか事前に知りたい」
  で発動。read-only で実際のデプロイはしない。デプロイ後の HTTP 確認は
  `app-smoke-test`。
version: 0.2.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
---

# デプロイ前プリフライト検証（atomic・read-only）

`create-app` / `aws-static-deploy` / `update-deploy` を走らせる前に、**「これで apply したら
高確率でコケる／課金が orphan 化する」前提**を機械的に洗い出すゲート。

このスキルは **一切デプロイしない**（read-only）。`app-smoke-test` が「公開後に URL を叩く」
のに対し、本スキルは「公開前に足回りを検査する」。**FAIL が 1 つでもあれば、その原因を
提示してデプロイを止める**（ユーザーが明示的に無視を選んだ場合のみ続行）。

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `TARGET` | ✅ | `aws-static` / `aws-ecs` / `vercel` のいずれか（デプロイ経路） |
| `PROJECT_DIR` | ✅ | Terraform / アプリのルート（`main.tf` や `Dockerfile` を探す） |
| `DOMAIN` | 任意 | カスタムドメイン。指定時は Hosted Zone 実在を確認 |
| `BILLING` | 任意 | `stripe` 等。指定時は決済系の鍵/Webhook を確認 |
| `CREDENTIALS_FILE` | 任意 | `.deploy-credentials/.env`。`--credentials` または `DEPLOY_CREDENTIALS_FILE` で指定 |

---

## 動作要件

必要 mcpb（AI OSI URI Deploy）: >= 1.23.0

## チェック項目（経路別）

### 共通
0. **mcpb バージョン整合** — `health_check` の `server_version` が上の「必要 mcpb」以上か。
   未満（または `server_version` 欠落＝1.22 以前）は **FAIL** としてポータルからの更新を案内。
   `update.status: "update_available"` は **WARN**（`update.notice` を表示）、
   `unreachable` は判定に含めない。設計: docs/mcpb-update-notification-design.md
1. **AWS 認証とアカウント一致** — AWS 経路または `DOMAIN` 指定時に
   `aws sts get-caller-identity`。`EXPECTED_AWS_ACCOUNT_ID` 指定時は一致も検証する。
2. **認証情報の保存** — `setup-deploy-environment` の成果（全経路の GitHub PAT /
   GitHub username、Vercel 経路の Vercel Token）が指定ファイルまたは環境変数にあるか。
3. **git 状態** — ブランチがクリーンで、`origin` に push 済みか（未push は
   `gh-create-repo-and-push` へ誘導）。
4. **非機能の決定** — `nonfunctional.yaml`（harness-init が配置）の 6 項目の `decided` が
   すべて埋まっているか。空欄・`【TODO】`・`null` は「決めていない」＝ **FAIL**
   （`nonfunctional-decided`）。`accepted_defaults` に `【TODO】` が残っていても FAIL。
   `verified` が `null` の項目は **WARN**（`nonfunctional-verified`）。初回公開前は WARN で
   よいが、公開後に実際に確かめて埋める。recovery / change は「戻す」を一度やるまで PASS にならない。

### `aws-static`（S3 + CloudFront）
4. `terraform validate` が通る／または静的ビルド成果物が存在する。
5. **S3 リモート backend が設定済み**（`backend "s3"` あり）。ローカルstateのみなら
   `tf-state-backend` を先に実行するよう **警告**（orphan 化リスク）。
6. `DOMAIN` 指定時：**ACM は us-east-1** で発行される設定か、Hosted Zone がアカウント内に実在するか
   （`aws-route53 zone <domain>` で逆引き、空なら FAIL）。

### `aws-ecs`（コンテナ / Fargate）
4. **Dockerfile 実在**、`HEALTHCHECK` またはヘルス用パス（例 `/healthz`）が定義されている。
5. Terraform の S3 backend（共通5と同じ）。
6. `BILLING=stripe` 時：`STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` /
   `NEXT_PUBLIC_STRIPE_PRICE_ID` が env に揃っているか（本番は `switch-to-live-mode` 前提）。

### `vercel`
4. `vercel` プロジェクトがリンク済み（`.vercel/project.json`）か。
5. Vercel Token が指定ファイルまたは環境変数に存在するか。

---

## 手順

```bash
export AWS_PROFILE=ai-osi-uri
# 機械判定できる項目を一括実行（read-only）
args=("$TARGET" "$PROJECT_DIR")
[ -n "${DOMAIN:-}" ] && args+=(--domain "$DOMAIN")
[ -n "${BILLING:-}" ] && args+=(--billing "$BILLING")
[ -n "${CREDENTIALS_FILE:-}" ] && args+=(--credentials "$CREDENTIALS_FILE")
scripts/preflight.sh "${args[@]}"
```
スクリプトが判定できない項目（例: Vercel の env が業務要件を満たすか）は、内容を提示して
人間に確認する。

## 出力

```json
{
  "target": "aws-static",
  "result": "FAIL",
  "checks": [
    { "id": "aws-auth",      "status": "PASS", "detail": "account 1234... (ai-osi-uri)" },
    { "id": "tokens",        "status": "PASS" },
    { "id": "git-pushed",    "status": "PASS", "detail": "main @ origin up-to-date" },
    { "id": "tf-validate",   "status": "PASS" },
    { "id": "s3-backend",    "status": "FAIL", "detail": "backend \"s3\" 未設定 → tf-state-backend を先に" },
    { "id": "hosted-zone",   "status": "PASS", "detail": "Z0123... for example.com" },
    { "id": "acm-region",    "status": "WARN", "detail": "ACM は us-east-1 で発行のこと" }
  ],
  "blocking": ["s3-backend"],
  "next": "tf-state-backend を実行してから create-app を再開"
}
```

- `result: PASS` … そのまま呼び出し元（`create-app` 等）へ制御を戻す。
- `result: FAIL` … `blocking` の各項目の直し方（該当スキル名）を提示して**停止**。
- `WARN` … ブロックしないが必ずユーザーに見せる。

---

## やらないこと（境界）

- **デプロイ・リソース作成・state変更** … 一切しない（read-only 検証のみ）。
- **公開後の動作確認** … `app-smoke-test` の役割。
- **認証情報の新規取得** … `setup-deploy-environment` の役割（本スキルは「揃っているか」だけ見る）。
- **実カード決済の E2E** … 対象外（人間に依頼）。
