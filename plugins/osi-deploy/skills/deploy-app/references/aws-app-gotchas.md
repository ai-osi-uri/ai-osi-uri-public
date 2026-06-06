# AWS サーバレスアプリ — 最小構成と既知のハマりどころ

AI OSI URI のAWSアカウント（ap-northeast-1 / 東京）で、Cowork から Terraform（拡張の `aws_terraform_apply/status/destroy/output`）でWebアプリを公開する時の定番構成と、毎回詰まるポイント。**新規アプリのAWSパスでは着手前にこれを読む。** コロワイドの2アプリ（在庫早期警戒・競合インテリジェンス）で確立。

## 最小構成（このまま流用できる）

- フロント：S3（非公開）+ CloudFront（OAC）。S3に `config.js` を置き `window.API_BASE='<api_endpoint>'` を注入してフロントとAPIを疎結合に。
- API：Lambda（Python 3.12、外部依存なし＝boto3のみ）+ API Gateway HTTP API（`$default` ルート、payload 2.0）。
- データ：DynamoDB 単一テーブル（PK/SK）。プロトタイプにRDSは重い。
- AI：Amazon Bedrock（別ファイル参照不要、`bedrock-app-notes.md` 相当は下記「Bedrock」節）。
- provider 設定：
  ```hcl
  provider "aws" {
    region = var.region
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
  }
  ```

## 既知のハマりどころ（時間を溶かさない）

1. **terraform は darwin_arm64 必須**。Rosettaのx86版はAWS署名で無言ハング（initは通るがapplyで固まる）。拡張のprebuildでarm64を入れている前提。

2. **公開 Lambda Function URL は SCP で禁止**（NONE も AWS_IAM/OAC も 403）。→ 最初から **API Gateway HTTP API** にする。Function URLを試さない。

3. **`$default` ルートは OPTIONS も拾う**（CORSプリフライトがLambdaに来る）。
   - CORSヘッダは **Lambda側で付与**し、`if method == "OPTIONS": return resp(200, {})` を**早期return**。
   - API Gateway 側の `cors_configuration` は**付けない**（Lambda側と二重になりブラウザが弾く）。

4. **lambda_permission の source_arn はアカウントID込みで明示**：
   ```hcl
   source_arn = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.api.id}/*/*"
   ```
   `aws_apigatewayv2_api.api.execution_arn` はアカウントが空で生成され不一致→500になる。

5. **RDSを使う場合**：PostgreSQLはSSL必須（pg8000等はSSLコンテキストを渡す）。プロトタイプは検証なしSSLでよい。VPC内Lambdaはインターネット直アクセス不可（NAT or VPCエンドポイントが要る）。

6. **コスト＝価値の所在**：静的フロント＋DynamoDBは月数十円。費用はBedrock（AI処理）の従量に集中。提案でもこの構造で説明する。

7. **Terraform state を作業フォルダに残さない（最重要・orphan化防止）**。Cowork の `.../outputs/...` は**セッション間で消える揮発領域**。`infra/terraform.tfstate` をそこに置いたままにすると、フォルダ喪失時に**リソースは課金され続けるのにstateが消えて管理・削除不能**になる。→ 新規AWSアプリは**最初から共有S3 backend**にする。`infra/backend.tf` を必ず置く：
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "aiosiuri-tfstate-<ACCOUNT_ID>"   # 無ければ tf-state-backend スキルが作成
       key            = "<namespace>/<project>/terraform.tfstate"
       region         = "ap-northeast-1"
       dynamodb_table = "aiosiuri-tf-lock"
       encrypt        = true
     }
   }
   ```
   初回 apply 前に **`tf-state-backend` スキル**を呼ぶ（state基盤の作成＋backend.tf差し込み）。既存のローカルstateアプリは同スキルの migrate-existing（`aws_terraform_apply` の prebuild で `terraform init -migrate-state -force-copy`）でS3へ移行。**mcpb の `terraform init` は `-migrate-state` を付けない**ので移行は必ず prebuild 側で。state用バケット/ロック（`aiosiuri-tf-lock`）は**手で消さない・destroy対象にしない**。コードとHANDOFFは共有ドライブへ退避（揮発対策）。詳細は `tf-state-backend` スキル参照。

## Bedrock

- **アカウント初期設定**：Anthropicモデルは**アカウント単位で「use case 詳細フォーム」提出が前提**（Bedrock Playgroundで対象モデル初回起動→送信→約15分で有効化）。未提出だと invoke_model も converse も `ResourceNotFoundException`。
- **チャット/生成**は `converse`（system=[{"text"}], messages=[{"role","content":[{"text"}]}], inferenceConfig={"maxTokens"}）。
- **画像(vision)** は `converse` の image コンテンツに bytes を渡す。**formatはマジックバイトで判定**（拡張子を信じない：PNG=`89504E47`, JPEG=`FFD8FF`）。
- IAM：Lambda実行ロールに `bedrock:InvokeModel`（converseも可）。
- **`jp.` 推論プロファイル**（例 `jp.anthropic.claude-haiku-4-5-...`）で東京・データ国内。Bedrockは入出力を学習に使わない・保存しない・ログしない（情シス審査の回答に使える）。

## データ自動更新の定番

EventBridge日次 → Lambda → 外部データ取得 → Bedrock構造化抽出 → DynamoDB。企業サイトはJS描画/Git LFSで取得失敗が多く、**Google News RSS**（`news.google.com/rss/search?q=...&hl=ja&gl=JP&ceid=JP:ja`）が最も堅いソース。
