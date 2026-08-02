---
name: gcp-ops
description: |
  Cowork から GCP を REST 経由で操作する（gcp_health_check / gcp_api / bq_query）。
  BigQuery 検証・Cloud Run デプロイ・API 有効化・IAM・Resource Manager などを CLI
  不要で実行する。「BigQuery を叩いて」「Cloud Run にデプロイ」「API を有効化して」
  「gcloud 相当のことをして」で発動。破壊的呼び出しは confirm:true、bq は既定
  read-only。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
---

# GCP 操作（atomic・REST / CLI 不要）

「AI OSI URI Deploy」拡張（v1.11.0 以降）が提供する GCP ツールで、Cowork から GCP を直接操作する。
拡張内で SA 鍵から OAuth トークンを発行し **REST API を直接叩く**ため、gcloud/bq/terraform の
インストールは不要。GitHub/Vercel と同じ「鍵を入れたら即動く」運用。

> 認証は **拡張設定**（`GCP サービスアカウント JSON` と `GCP プロジェクト ID`）に入力済みである前提。
> 未設定なら「セットアップ」節を案内する。鍵はチャットに貼らない（キーチェーン保存）。

---

## 使えるツール（拡張が提供）

| ツール | 用途 | 安全ゲート |
| --- | --- | --- |
| `gcp_health_check` | 認証疎通・SA・既定プロジェクト確認 | 読み取りのみ |
| `gcp_api` | 任意の Google REST API を直接呼ぶ汎用ツール（Cloud Run / Service Usage / IAM / Resource Manager 等） | DELETE・`:delete`/`:stop`/`:disable` は `confirm:true` 必須 |
| `bq_query` | BigQuery クエリ（集計・数字一致の検証） | 既定 read-only。DML/DDL は `allow_write:true` |

MCP 名は `mcp__AI_OSI_URI_Deploy__gcp_health_check` / `gcp_api` / `bq_query`。

---

## 標準ワークフロー

```
1. gcp_health_check で認証とプロジェクトを確認（未設定ならセットアップへ誘導）
2. 目的に応じて:
   - データ検証     → bq_query（SELECT で数字一致を確認）
   - 単発の REST 操作 → gcp_api（API 有効化 / Cloud Run デプロイ / リソース取得）
3. 破壊的操作（DELETE 等）は対象を提示し、ユーザーの明示承認 → confirm:true
4. 結果（URL・件数・レスポンス）を要約して返す
```

---

## gcp_api の使い方（汎用なので「叩き先」を知っておく）

`gcp_api` は URL を指定して任意の Google REST API を呼ぶ。`{project}` は GCP_PROJECT に置換される。
よく使う代表エンドポイント:

**API を有効化する（Service Usage）**
```
gcp_api(method="POST",
  url="https://serviceusage.googleapis.com/v1/projects/{project}/services/run.googleapis.com:enable")
```
（BigQuery=bigquery.googleapis.com、Cloud Run=run.googleapis.com、Vertex=aiplatform.googleapis.com 等）

**Cloud Run サービス一覧 / 取得（Run Admin v2）**
```
gcp_api(url="https://run.googleapis.com/v2/projects/{project}/locations/asia-northeast1/services")
```

**Cloud Run にデプロイ（イメージ指定で作成・更新）**
```
gcp_api(method="POST",
  url="https://run.googleapis.com/v2/projects/{project}/locations/asia-northeast1/services",
  query={ "serviceId": "my-api" },
  body={ "template": { "containers": [ { "image": "asia-northeast1-docker.pkg.dev/{project}/repo/my-api:latest" } ] } })
```
（更新は同 URL の services/my-api に PATCH。公開にするなら IAM の run.invoker を allUsers に付与）

**BigQuery データセット作成**
```
gcp_api(method="POST",
  url="https://bigquery.googleapis.com/bigquery/v2/projects/{project}/datasets",
  body={ "datasetReference": { "datasetId": "my_dataset" }, "location": "asia-northeast1" })
```

**プロジェクト確認（Resource Manager）**
```
gcp_api(url="https://cloudresourcemanager.googleapis.com/v1/projects/{project}")
```

> 迷ったら「GET で一覧/取得 → 中身を見て → POST/PATCH で作成/更新」。削除は最後、必ず confirm:true。

---

## bq_query の使い方

```
bq_query(sql="SELECT SUM(revenue) AS sales FROM `{project}.my_dataset.kpi_weekly`")
```
- 既定 **read-only**。集計・検証はこれで足りる。
- 書き込み/DDL（CREATE VIEW 等）は `allow_write:true` を明示し、理由を述べてから。
- `max_bytes_billed` で課金スキャン量に上限（既定 1GB）。

---

## ガードレール（絶対厳守）

- **破壊的呼び出し（DELETE / `:delete` / `:stop` / `:disable`）は対象を列挙して承認 → `confirm:true`**。無断で消さない。
- **bq_query は既定 read-only**。書き込みは `allow_write:true` を明示し最小限。
- **本番データは機密として扱う**。生データを丸ごとチャットに展開しない。スキーマ＋集計結果で扱う。
- **最小権限の SA**。広すぎる権限を付けない（下記セットアップ参照）。本番は絞り直す。
- 認証鍵は拡張（キーチェーン）経由のみ。チャット・ログに出さない。

---

## 当てはめ例：データ分析基盤プロジェクト

| 作業 | このスキルでの叩き方 |
| --- | --- |
| API 有効化（前準備） | `gcp_api` で BigQuery / Run / Vertex の各 API を `:enable` |
| 共通データセット（セマンティック層） | `gcp_api` で BigQuery データセット/ビューを作成 → `bq_query` で「定義通りの数字が出るか」検証 |
| 集計 API（Cloud Run） | コンテナを Artifact Registry に push 後、`gcp_api` で Cloud Run へデプロイ |
| BI フロント本番接続 | フロントを集計 API に結線し `gcp_api` で Cloud Run 配信 |
| 複数データソースの写像 | 各データセットを `bq_query` で確認し、写像 SQL を適用（allow_write は最小限） |

---

## セットアップ（未設定時のみ）

「AI OSI URI Deploy」拡張（v1.11.0+）の設定欄に入力（キーチェーン保存）。

| 欄 | 取得元 |
| --- | --- |
| `GCP サービスアカウント JSON` | GCP IAM で最小権限 SA を作成 → JSON 鍵を発行し丸ごと貼る |
| `GCP プロジェクト ID` | 対象プロジェクト ID（例: my-gcp-project） |

最小権限の目安（PoC・プロジェクト限定）：
`roles/bigquery.dataEditor`・`roles/bigquery.jobUser`（BigQuery）／`roles/run.admin`・
`roles/iam.serviceAccountUser`（Cloud Run）／`roles/serviceusage.serviceUsageAdmin`（API 有効化）。
入力後 `gcp_health_check` で `service_account` と `project` が返れば準備完了。

---

## エラー時の挙動

| 症状 | 原因 | 対応 |
| --- | --- | --- |
| health_check で「未設定」 | SA 鍵/プロジェクト未入力 | 拡張設定で入力し直す |
| `PERMISSION_DENIED` (403) | SA のロール不足 | 不足ロールを提示し付与を依頼 |
| `... API has not been used / disabled` | API 未有効化 | `gcp_api` で該当 API を `:enable` |
| `Quota exceeded: bytes billed` | スキャン量超過 | `max_bytes_billed` を上げるか SQL を絞る |
| `401 UNAUTHENTICATED` | 鍵が無効/失効 | SA 鍵を再発行し拡張設定を更新 |
