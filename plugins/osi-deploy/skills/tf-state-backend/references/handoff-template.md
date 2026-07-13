# {案件名} AWSアプリ 引き継ぎメモ（次セッション用）

最終更新: {YYYY-MM-DD} / 作成: Cowork セッション

新しいセッションを始めるときは、冒頭でこのファイルを Claude に貼るか「このHANDOFFを読んで」と
伝えれば、状態を把握して続きから作業できます。

---

## 0. 結論

- 稼働中のAWSアプリは Terraform で管理、**state は共有S3 backend で一元管理**済み（揮発しない）。
- **state の正本 = S3 `aiosiuri-tfstate-{ACCOUNT_ID}`**（東京 / バージョニング・暗号化・非公開・DynamoDBロック）。
- セッションの作業フォルダが消えても、**Driveのコード一式 + S3のstate + 拡張のAWS認証があれば完全復旧できる**。

## 1. 稼働中アプリ

| アプリ | 公開URL | CloudFront ID | コード(永続) |
| --- | --- | --- | --- |
| {アプリ名} | {url} | {dist_id} | {Drive相対パス}/aws-repo-{project}/ |

## 2. Terraform state

| 項目 | 値 |
| --- | --- |
| stateバケット | `aiosiuri-tfstate-{ACCOUNT_ID}`（ap-northeast-1） |
| state キー | `{namespace}/{project}/terraform.tfstate` |
| ロックテーブル | `aiosiuri-tf-lock`（HASHキー `LockID`） |

各リポの `infra/backend.tf` にS3 backend定義あり。新セッションは `terraform init` でS3 stateを参照。

## 3. 新セッションでの作業手順

1. Driveのコードを作業領域（outputs等のローカル）へコピーして使う（DriveのままTerraformを回すとFUSEで不具合）。
2. デプロイは拡張 `aws_terraform_apply`（repo_dir, prebuild）。進捗は `aws_terraform_status`。
3. フロント更新後は CloudFront を invalidate（該当 Distribution ID の `/index.html`）。
4. backend.tf によりstateは自動でS3参照（migrate-stateは移行済みなので不要）。

## 4. 触ってはいけない

- state用S3バケットとDynamoDBロックは **state管理専用**。手で消さない。destroy対象にもしない。
- 撤去は対象リポで `aws_terraform_destroy`（confirm必須）。state基盤は残す。
