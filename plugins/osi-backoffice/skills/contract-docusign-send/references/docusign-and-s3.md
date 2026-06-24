# DocuSign 送付と S3 一時公開の仕組み（詳細）

## なぜ S3 が要るのか
DocuSign の `createEnvelope` は **base64 アップロードを受け付けない**。ドキュメントは
`remoteUrl`（公開HTTP(S) URL、生のファイルバイトを返すもの）経由でのみ取り込める。
Cowork にアップした任意の契約書を送るには、DocuSign が一度だけ取得できる URL を用意する必要がある。
そこで非公開 S3 に一時的に置き、**短命・推測困難な署名付きURL**で取得させる。

## 専用バケット
- 名前：`aiosiuri-contract-staging-135728714359`
- リージョン：`ap-northeast-1`
- 設定：**公開アクセス全ブロック**（BlockPublic* 全て true）＋ **ライフサイクルで1日後に自動失効**。
- アカウント：`135728714359`（IAMユーザー `yuhe.nagisa`）。

> バケットが消えている／別アカウントの場合は、同等設定で作り直す：
> ```
> aws s3api create-bucket --bucket <name> --region ap-northeast-1 --create-bucket-configuration LocationConstraint=ap-northeast-1
> aws s3api put-public-access-block --bucket <name> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
> aws s3api put-bucket-lifecycle-configuration --bucket <name> --lifecycle-configuration '{"Rules":[{"ID":"expire-1d","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":1}}]}'
> ```

## ファイルの橋渡し（重要）
3つのファイルシステムが分かれている：
- **Cowork bash サンドボックス**：契約書PDFがある／ネットワーク到達可／aws CLI なし・creds なし。
- **AWS-MCP（call_aws）**：creds を持つが、作業ディレクトリ `/tmp/aws-api-mcp/workdir` 外のファイルを読めない。
- **file tools（Mac）**：outputs と共有ドライブのみ書ける。

→ よって「call_aws で直接 `s3 cp`」はできない（workdir外を拒否される）。
**短命の federation token を call_aws で発行し、その creds を bash に渡して boto3 でアップロード**する方式を採る。
（検証済み：この経路で SigV4・リージョナルの署名付きURLを生成し、外部から HTTP 200 で取得できることを確認済み。）

## 手順

### 1. 一時資格情報（federation token）を発行（call_aws）
PutObject + GetObject だけに絞り、短命にする。
```
aws sts get-federation-token --name osi-ds-io --duration-seconds 3600 \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:PutObject","s3:GetObject"],"Resource":"arn:aws:s3:::aiosiuri-contract-staging-135728714359/*"}]}'
```
返り値の `Credentials.{AccessKeyId,SecretAccessKey,SessionToken}` を使う。

### 2. アップロード＋署名付きURL生成（bash）
```bash
export AWS_ACCESS_KEY_ID=<AccessKeyId>
export AWS_SECRET_ACCESS_KEY=<SecretAccessKey>
export AWS_SESSION_TOKEN=<SessionToken>
python3 <skill>/scripts/upload_and_presign.py \
  --file "<送付用PDF>" \
  --bucket aiosiuri-contract-staging-135728714359 \
  --key "outbound/$(date +%Y-%m)/<相手先>_<契約名>_<YYYYMMDD>.pdf" \
  --expires 1800
```
最終行 `PRESIGNED_URL=...` を取得する。`generate_presigned_url` は SigV4・リージョナル・virtual-host
形式で出るため、グローバルendpointのリダイレクト(307)問題は起きない。

> 注意：`aws s3 presign`（CLI）は旧 SigV2＋グローバルendpointのURLを出し、ap-northeast-1 では
> 307 リダイレクトで壊れる。**必ず boto3（本スクリプト）側で生成する。**

### 3. DocuSign 封筒を作成（まずドラフト）
```
getUserInfo()                      # account_id を取得
createEnvelope(accountId, { status:"created", emailSubject, documents:[{documentId,name,remoteUrl:<PRESIGNED_URL>}], recipients:{signers:[...]} })
getEnvelope(accountId, envelopeId) # 内容確認 → 人に提示
```
人の承認後：
```
updateEnvelope(accountId, envelopeId, { status:"sent" })   # 送信
# 取消は { status:"voided", voidedReason:"..." }
```

## 署名タブ（signHereTabs）の置き方
- 署名欄の **会社名 or 代表者名を anchorString** にして配置するのが安定。
  - 乙：`anchorString:"AI OSI URI"`（または "渚 有瓶"）
  - 甲：相手先の会社名 or 代表者名
- `anchorYOffset`（pixels）で署名線の位置を微調整。実物のドラフトを `getEnvelope` で確認して調整する。
- 自動配置に不安があれば、ドラフトのまま DocuSign Web で目視確認 → 送信、も可（誤配置の保険）。

## セキュリティ
- 一時資格情報・生の署名付きURLを **チャットや保存ファイルに残さない**（メタにはS3キーと有効期限のみ）。
- バケットは公開ブロック＋1日失効。署名付きURLは短命（既定30分）。DocuSign取得後は実質無効化される。
- federation token は PutObject/GetObject の対象バケットのみに限定する（他リソースへ広げない）。
