# セットアップ・前提コネクタ（contract-docusign-send を使う前に）

このスキルを使うメンバーが最初に1回だけ整える項目。**2つのコネクタ**と、**S3ステージング**の確認が必要。

## 1. DocuSign コネクタ（必須）

- Cowork の「コネクタを追加」から **DocuSign** を接続（OAuth ログイン）。
- アカウントは自動取得（スキルが `getUserInfo` で `account_id` を解決する）。現状の本番は `jp1.docusign.net`。
- 権限：封筒の作成・取得・更新（送信は人が DocuSign 画面で行うため、最低限「下書き作成」ができれば可）。
- 確認：チャットで「DocuSign のアカウント情報を見せて」と言って `getUserInfo` が通れば OK。

## 2. AWS（aws-api-mcp）コネクタ（必須）

契約書PDFを DocuSign に渡すための一時公開URL発行に使う。

- Cowork に **aws-api-mcp（AWS API）** コネクタを接続し、AWS 認証情報を設定する。
- 既定リージョン：`ap-northeast-1`。
- 必要な IAM 権限（最小）：
  - `sts:GetFederationToken`（一時資格情報の発行）
  - ステージングバケットに対する `s3:PutObject` / `s3:GetObject`
  - （バケットを新規に作る場合のみ）`s3:CreateBucket` / `s3:PutBucketPublicAccessBlock` / `s3:PutLifecycleConfiguration` / `s3:DeleteObject`
- 確認：チャットで「`aws sts get-caller-identity` を実行して」で 200 が返れば OK。

## 3. S3 ステージングバケット（共用・1回だけ）

- 既定バケット：`aiosiuri-contract-staging-135728714359`（AWSアカウント `135728714359` / ap-northeast-1）。
  - 設定：公開アクセス全ブロック＋**1日でオブジェクト自動失効**。
- **同じ AWS アカウントを使うメンバー**は、上記バケットへの Put/Get 権限があればそのまま使える（作成不要）。
- **別の AWS アカウント**を使う場合は、同等設定でバケットを作り、`references/docusign-and-s3.md` のバケット名を置き換える：
  ```bash
  aws s3api create-bucket --bucket <name> --region ap-northeast-1 --create-bucket-configuration LocationConstraint=ap-northeast-1
  aws s3api put-public-access-block --bucket <name> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-lifecycle-configuration --bucket <name> --lifecycle-configuration '{"Rules":[{"ID":"expire-1d","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":1}}]}'
  ```

## 4. その他

- Cowork の Linux サンドボックスで `pandoc` / `soffice`（docx→PDF）と `python3`/`pip` が使える前提（既定で利用可）。`boto3` はスクリプトが自動インストールする。
- Drive（共有ドライブ `30.契約管理/`）がマウントされていること（格納先）。

## 動作テストの仕方（安全）

1. 適当な契約書（または自社NDA）をアップロードする。
2. 「この契約書をチェックして DocuSign のドラフトを作って。送付は自分宛（自分のメール）でテスト」と依頼。
3. スキルが：内容チェック表 → 署名者確認 → S3一時アップ → DocuSign **ドラフト**作成、まで実行。
4. DocuSign の「下書き(Drafts)」を開いて中身を確認 → そこで送信（または破棄）。
   - ＝ Claude は送信しない。送信操作は必ず人が DocuSign 上で行う。

## つまずきポイント

| 症状 | 対処 |
|---|---|
| `getUserInfo` でアカウントが出ない | DocuSign 未接続/再ログイン |
| `get-caller-identity` が失敗 | aws-api-mcp 未接続/認証情報未設定 |
| `AccessDenied`（PutObject 等） | IAM 権限不足。上記の最小権限を付与 |
| 署名付きURLで 307/403 | URL生成はスクリプト（boto3, SigV4, リージョナル）で行う。`aws s3 presign` は使わない |
| DocuSign が文書を取り込めない | 署名付きURLの有効期限切れ。発行から数分以内に封筒作成する |
