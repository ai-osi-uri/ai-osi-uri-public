# AWS デプロイパス（Phase 4-W-A）リファレンス

`create-app` スキルが AWS パスを選択した場合の詳細手順。
Vercel+Supabase パスとは異なり、Claude Code によるローカル構築 → Terraform → ECS の流れを取る。

---

## 1. AWS パスの実行手順

### Step 1: Terraform State Backend の準備

**必ず最初に実行する。** orphan state（ローカルにしか state が残らない状態）を防止するため、
`tf-state-backend` スキルで共有 S3 backend を構成する。

```
スキル呼び出し: tf-state-backend
```

- S3 バケット + DynamoDB ロックテーブルを作成
- `backend.tf` の雛形を生成
- **初回 `terraform apply` の前に完了していること**が必須条件

### Step 2: spec.md と infra-decision.md の生成

ユーザーとのヒアリング結果をもとに、以下の2ファイルを生成する。
テンプレートは本ファイル後半のセクションを参照。

| ファイル | 役割 |
|---|---|
| `spec.md` | アプリケーション仕様（エンティティ・認証・機能要件） |
| `infra-decision.md` | インフラ構成の意思決定（VPC・Aurora・ECS・WAF 等） |

生成後、ユーザーに内容を確認してもらい、承認を得る。

### Step 3: Claude Code 起動コマンドの準備

承認後、以下のコマンドをクリップボードにセットし、ユーザーにターミナルでの実行を依頼する。

```bash
git clone <project-template-repo> <PROJECT_NAME> && \
cd <PROJECT_NAME> && \
cp /path/to/spec.md . && \
cp /path/to/infra-decision.md . && \
claude
```

**ユーザーへの指示（明確に伝えること）:**

1. Claude Code が起動したら `/initialize-project` を実行
2. 完了したら `/setup-infra` を実行
3. `/setup-infra` が完了したら **ここで止まる**（次のコマンドは実行しない）
4. **Cowork に戻ってくる**（Phase 4-A 監視に進む）

> `/bootstrap-project` は使わない。`/initialize-project` → `/setup-infra` の順序を守ること。
> `/bootstrap-project` は内部で順序が逆転するため、インフラ構築に失敗する。

### Step 4: Phase 4-A インフラ監視（MCP ポーリング）

ユーザーが Cowork に戻ってきたら、MCP を使って 30 秒間隔でインフラの構築状況をポーリングする。

**監視対象:**

| リソース | 確認方法 | 期待値 |
|---|---|---|
| GitHub リポジトリ | `github_push` / リポ存在確認 | リポジトリが存在し、main ブランチにコードがある |
| GitHub ブランチ | ブランチ一覧取得 | `main`, `develop` 等が存在 |
| Terraform state bucket | S3 バケット確認 | state ファイルが格納されている |
| VPC | AWS API 確認 | VPC + サブネットが作成済み |
| ECR | AWS API 確認 | リポジトリが作成済み |
| Aurora | AWS API 確認 | クラスターが `available` 状態 |

ポーリングは best effort で行い、タイムアウトや一時的なエラーは許容する。
全リソースの確認が取れたら Step 5 に進む。

### Step 5: アプリケーション + CI 構築

再びユーザーにターミナルでの Claude Code 操作を依頼する。

```
Claude Code で `/create-app` を実行
```

`/create-app` 完了後、以下が自動で実行される:

1. `docker build` → ECR へ `docker push`
2. `ecs update-service` で新タスク定義をデプロイ
3. DB マイグレーション（`migration`）の実行
4. 初期データ投入（`seed`）の実行

### Step 6: Phase 5-A アプリ監視（ECS ポーリング）

ECS サービスの `runningCount` を 30 秒間隔でポーリングし、タスクが正常に起動したことを確認する。

**確認項目:**

- `desiredCount` と `runningCount` が一致していること
- タスクのステータスが `RUNNING` であること
- ヘルスチェックが `HEALTHY` であること

### Step 7: 動作確認スモークテスト

ALB のヘルスチェックエンドポイントに対してスモークテストを実行する。

```
ALB_DNS/health → HTTP 200 を期待
```

`app-smoke-test` スキルを呼び出し、以下を検証:

- API エンドポイント: `http://<ALB_DNS>/health` → 200
- フロントエンド: `https://<CLOUDFRONT_DOMAIN>` → 200
- 必要に応じてカスタムパスの検証も追加

---

## 2. spec.md テンプレート

```markdown
# プロジェクト仕様書

## 基本情報

- **PROJECT_NAME**: <プロジェクト名（英数ケバブケース）>
- **概要**: <1〜2文でアプリの目的を記述>
- **業種**: <対象業種（例: 不動産、医療、EC、SaaS）>

## エンティティ

| エンティティ名 | 説明 | 主要フィールド |
|---|---|---|
| User | ユーザー | email, name, role |
| <Entity2> | <説明> | <フィールド> |
| <Entity3> | <説明> | <フィールド> |

## 認証・ロール

| ロール | 権限 | 説明 |
|---|---|---|
| admin | 全権限 | 管理者 |
| <role2> | <権限> | <説明> |

## 機能要件

1. <機能1の説明>
2. <機能2の説明>
3. <機能3の説明>
```

---

## 3. infra-decision.md テンプレート

```markdown
# インフラ構成決定書

## 規模

- **想定ユーザー数**: <初期 / 1年後>
- **想定リクエスト数**: <RPS / 日次>
- **データ量**: <初期 / 1年後>

## ネットワーク

- **VPC CIDR**: 10.0.0.0/16
- **AZ 数**: 2
- **パブリックサブネット**: ALB, NAT Gateway
- **プライベートサブネット**: ECS, Aurora

## データベース

- **Aurora**: PostgreSQL (Serverless v2 / Provisioned)
- **インスタンスクラス**: <db.r6g.large 等>
- **マルチAZ**: <有効 / 無効>
- **バックアップ保持期間**: 7日

## コンピュート

- **ECS**: Fargate
- **タスク CPU / メモリ**: <256/512 等>
- **オートスケーリング**: <min/max/target CPU%>
- **デプロイ戦略**: Rolling update

## セキュリティ・CDN

- **WAF**: <有効 / 無効 / ルールセット>
- **CloudFront**: <フロントエンド配信に使用 / 不使用>
- **ACM 証明書**: <ドメイン>

## サーバーレス

- **Lambda**: <使用する場合の用途（例: 画像リサイズ、バッチ処理）>

## コンプライアンス

- **要件**: <ISMS / HIPAA / PCI-DSS / なし>
- **ログ保持**: <CloudWatch 保持期間>
- **暗号化**: <KMS / デフォルト>

## ドメイン

- **ドメイン名**: <example.com>
- **Route 53**: <使用 / 外部DNS>
- **SSL**: ACM

## terraform.tfvars（参考値）

project_name     = "<PROJECT_NAME>"
environment      = "production"
vpc_cidr         = "10.0.0.0/16"
az_count         = 2
db_instance_class = "db.r6g.large"
ecs_cpu          = 256
ecs_memory       = 512
desired_count    = 2
domain_name      = "<example.com>"
```

---

## 4. AWS パス判定時の追加確認事項

`create-app` オーケストレータが AWS パスを選択した際、ユーザーに追加で確認すべき項目:

| 確認項目 | 質問例 | 影響する構成 |
|---|---|---|
| **規模感** | 「ユーザー数はどのくらいを想定していますか？」 | ECS タスク数、Aurora インスタンスクラス |
| **ロール構成** | 「管理者以外にどんな権限のユーザーがいますか？」 | 認証・認可設計、RLS |
| **コンプライアンス** | 「ISMS や業界固有の規制要件はありますか？」 | WAF、暗号化、ログ保持、VPC 構成 |
| **ドメイン** | 「独自ドメインは用意済みですか？Route 53 で管理しますか？」 | Route 53、ACM、CloudFront |
| **通知メール** | 「アラート通知を受け取るメールアドレスは？」 | SNS、CloudWatch Alarm |

---

## 5. 完了レポートテンプレート（AWS パス）

```markdown
# デプロイ完了レポート

## 公開 URL

| 種別 | URL |
|---|---|
| API（ALB） | http://<ALB_DNS> |
| フロントエンド（CloudFront） | https://<CLOUDFRONT_DOMAIN> |

## リポジトリ

- **GitHub**: https://github.com/<org>/<PROJECT_NAME>

## 構成サマリ

| リソース | 詳細 |
|---|---|
| VPC | 10.0.0.0/16, 2 AZ |
| ECS (Fargate) | CPU: 256, Memory: 512, Tasks: 2 |
| Aurora PostgreSQL | Serverless v2 / db.r6g.large |
| ALB | パブリックサブネット |
| CloudFront | フロントエンド配信 |
| WAF | <有効 / 無効> |
| Route 53 | <ドメイン> |
| Terraform State | S3 + DynamoDB Lock |

## 次にやること

1. **カスタムドメインの設定**: Route 53 にレコードを追加し、ACM 証明書を検証
2. **CI/CD パイプラインの確認**: GitHub Actions のワークフローが正常に動作することを確認
3. **監視・アラートの設定**: CloudWatch Alarm + SNS で異常検知を構成
4. **バックアップの確認**: Aurora の自動バックアップが有効であることを確認
5. **本番データの投入**: 必要に応じて seed データの差し替え・追加
6. **負荷テスト**: 想定トラフィックでの動作確認（任意）
```

---

## 6. 注意事項

- **Claude Code が必要**: AWS パスはローカルの Claude Code でインフラ構築を行う。Cowork 単体では完結しない。ユーザーに Claude Code のインストールと起動を案内すること。
- **`/bootstrap-project` は使わない**: このコマンドは `/setup-infra` → `/initialize-project` の順で実行するため、プロジェクト初期化の前にインフラを構築しようとして失敗する。必ず `/initialize-project` → `/setup-infra` の順序を守ること。
- **MCP 監視は best effort**: AWS リソースの構築状況をポーリングで監視するが、ネットワークの一時的な問題やAPI レートリミットでエラーになる場合がある。数回のリトライで回復しなければ、ユーザーにマネジメントコンソールでの確認を依頼する。
- **Terraform state の orphan 化**: Step 1（`tf-state-backend`）をスキップすると、state がローカルにしか残らず、以降の `terraform plan/apply` が別環境から実行できなくなる。絶対にスキップしない。
- **コスト意識**: Aurora、NAT Gateway、ALB は常時課金が発生する。開発環境では Serverless v2 の最小 ACU を下げる、NAT Gateway をインスタンスに置き換える等のコスト最適化を検討すること。
