---
name: aws-static-deploy
description: |
  GitHub に push 済みの静的サイト（HTML / Vite / Next.js export）を S3 + CloudFront +
  ACM + Route 53 で公開する。CloudFront OAC で S3 を非公開のまま配信、SPA
  フォールバック、Japan 限定 geo restriction（解除可）まで含めて初回デプロイを完結し
  APP_URL を返す。`create-app` から呼ばれるほか、単体で「AWS で LP 公開して」「S3 +
  CloudFront でデプロイ」「Vercel じゃなくて AWS に上げて」で発動。Next.js SSR / API
  Routes / 認証付き SaaS には使わない。
version: 0.1.0
---

# AWS 静的サイトデプロイ（atomic）

`gh-create-repo-and-push` で push 済みの GitHub リポジトリ（または直接アップロードされた
ビルド成果物フォルダ）を受け取り、S3 + CloudFront + ACM + Route 53 で公開する。
**「Vercel の代わりに AWS で静的サイトをホスト」**するための atomic スキル。

このスキルは **GitHub への push** と **動的バックエンド**（Lambda, API Gateway, RDS 等）
は扱わない。S3 にアップロードして CloudFront で配信するだけ。

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `PROJECT_NAME` | ✅ | バケット名・CloudFront コメント・ACM タグに使う。英数字とハイフンのみ |
| `INPUT_DIR` | ✅ | アップロード対象。`index.html` を含む静的ファイル群のローカルパス |
| `DOMAIN` | 任意 | カスタムドメイン（例: `unics.example.jp`）。空なら `*.cloudfront.net` のみ |
| `ROUTE53_ZONE_ID` | 任意 | DOMAIN 指定時のみ使う。`AWS_ROUTE53_HOSTED_ZONE_ID` から自動取得可 |
| `GEO_RESTRICT_JP` | 任意 | デフォルト `false`。`true` なら日本国内に限定（医療系想定） |
| `CACHE_INVALIDATE_PATHS` | 任意 | デフォルト `/*`。デプロイ後の Invalidation 対象 |

`AWS_PROFILE`、`AWS_REGION`、`AWS_ROUTE53_HOSTED_ZONE_ID` は **環境変数を優先**して取得する（AWS 認証は `.mcpb` 拡張の対象外。`AWS_PROFILE` はローカルの `~/.aws` プロファイル名）。
共有ドライブの `.deploy-credentials/.env` は **任意フォールバック**としてのみ参照する。

---

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| `AWS_PROFILE` が利用可能 | 環境変数 or AWS MCP、無ければ任意 `.env` | `AWS_PROFILE` の設定を案内 |
| AWS_PROFILE が `aws sts get-caller-identity` で通る | Step 1 で検証 | プロファイル名の入力やり直し |
| INPUT_DIR が存在し index.html を含む | Step 2 で検証 | ユーザーに指定し直しを依頼 |
| DOMAIN 指定時、ROUTE53_ZONE_ID が解決可能 | Step 3-4 で検証 | DNS 自前管理か、AWS への移管を案内 |

---

## ワークフロー

```
1. AWS 認証の解決（環境変数優先・.env は任意）・AWS 認証検証
2. INPUT_DIR 検証（index.html 存在確認）
3. バケット名重複チェック・命名衝突時のサフィックス採番
4. ACM 証明書の発行（DOMAIN 指定時、us-east-1 必須）
5. S3 バケット作成（Versioning, 暗号化, Public Access Block）
6. CloudFront OAC 作成・ディストリビューション作成
7. S3 バケットポリシー更新（OAC からの GetObject のみ許可）
8. Route 53 レコード作成（DOMAIN 指定時）
9. aws s3 sync で INPUT_DIR をアップロード
10. CloudFront キャッシュ Invalidation
11. APP_URL を state.json に追記して返す
```

---

## Step 1: 認証情報の読み込み

```bash
# AWS 認証は .mcpb 拡張の対象外。AWS_PROFILE 等は環境変数を優先し、無ければ共有 .env を任意フォールバック
if [ -z "${AWS_PROFILE:-}" ]; then
  ENV_PATH="/sessions/<session-id>/mnt/AI OSI URI/.deploy-credentials/.env"
  [ -f "$ENV_PATH" ] && { set -a; source "$ENV_PATH"; set +a; }
fi
: "${AWS_PROFILE:?AWS_PROFILE 未設定。環境変数 AWS_PROFILE を設定するか ~/.aws を構成してください}"
: "${AWS_REGION:=ap-northeast-1}"

# 認証検証
ID_JSON=$(aws sts get-caller-identity --profile "$AWS_PROFILE" 2>&1)
if [ $? -ne 0 ]; then
  echo "ERROR: AWS 認証失敗: $ID_JSON" >&2
  exit 1
fi
AWS_ACCOUNT=$(echo "$ID_JSON" | jq -r .Account)
echo "INFO: AWS Account=$AWS_ACCOUNT, Region=$AWS_REGION"
```

---

## Step 2: INPUT_DIR 検証

```bash
: "${INPUT_DIR:?INPUT_DIR 未指定}"
[ ! -d "$INPUT_DIR" ] && { echo "ERROR: INPUT_DIR が存在しない: $INPUT_DIR" >&2; exit 1; }
[ ! -f "$INPUT_DIR/index.html" ] && {
  echo "WARN: $INPUT_DIR/index.html が見つかりません" >&2
  echo "INFO: 続行しますが、CloudFront のデフォルトルートオブジェクトが 404 になります" >&2
}
```

---

## Step 3: バケット名の確定

S3 バケット名はグローバルでユニーク。`PROJECT_NAME` + `-prod` + `-<アカウント ID 下4桁>`
の命名で衝突を回避する。

```bash
: "${PROJECT_NAME:?PROJECT_NAME 未指定}"
ACCOUNT_SUFFIX="${AWS_ACCOUNT: -4}"
BASE_BUCKET="${PROJECT_NAME}-prod-${ACCOUNT_SUFFIX}"

# サフィックス採番（最大 5 回）
BUCKET_NAME="$BASE_BUCKET"
for i in 1 2 3 4 5; do
  HEAD=$(aws s3api head-bucket --bucket "$BUCKET_NAME" --profile "$AWS_PROFILE" 2>&1)
  if [ $? -ne 0 ]; then
    break  # NoSuchBucket 系なら使える
  fi
  BUCKET_NAME="${BASE_BUCKET}-$(printf '%03d' $i)"
done
echo "INFO: BUCKET_NAME=$BUCKET_NAME"
```

---

## Step 4: ACM 証明書の発行（DOMAIN 指定時）

CloudFront 用の証明書は **必ず us-east-1** で発行する。

```bash
if [ -n "$DOMAIN" ]; then
  CERT_ARN=$(aws acm request-certificate \
    --domain-name "$DOMAIN" \
    --validation-method DNS \
    --region us-east-1 \
    --profile "$AWS_PROFILE" \
    --query CertificateArn --output text)

  # DNS 検証レコードを取得（少し待つ）
  for i in $(seq 1 30); do
    sleep 2
    VAL_NAME=$(aws acm describe-certificate --certificate-arn "$CERT_ARN" \
      --region us-east-1 --profile "$AWS_PROFILE" \
      --query "Certificate.DomainValidationOptions[0].ResourceRecord.Name" --output text)
    [ "$VAL_NAME" != "None" ] && break
  done
  VAL_VALUE=$(aws acm describe-certificate --certificate-arn "$CERT_ARN" \
    --region us-east-1 --profile "$AWS_PROFILE" \
    --query "Certificate.DomainValidationOptions[0].ResourceRecord.Value" --output text)

  # Route 53 に検証レコード追加
  : "${ROUTE53_ZONE_ID:=$AWS_ROUTE53_HOSTED_ZONE_ID}"
  if [ -n "$ROUTE53_ZONE_ID" ]; then
    aws route53 change-resource-record-sets --hosted-zone-id "$ROUTE53_ZONE_ID" \
      --profile "$AWS_PROFILE" \
      --change-batch "{\"Changes\":[{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"$VAL_NAME\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$VAL_VALUE\"}]}}]}"
    aws acm wait certificate-validated --certificate-arn "$CERT_ARN" \
      --region us-east-1 --profile "$AWS_PROFILE"
  else
    echo "WARN: ROUTE53_ZONE_ID 未設定。手動で CNAME $VAL_NAME → $VAL_VALUE を設定してから続行してください" >&2
    exit 1
  fi
fi
```

---

## Step 5: S3 バケット作成

```bash
aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$AWS_REGION" \
  --create-bucket-configuration LocationConstraint="$AWS_REGION" \
  --profile "$AWS_PROFILE"

aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled \
  --profile "$AWS_PROFILE"

aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
  --profile "$AWS_PROFILE"

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  --profile "$AWS_PROFILE"
```

---

## Step 6: CloudFront OAC + ディストリビューション作成

```bash
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config "{\"Name\":\"${BUCKET_NAME}-oac\",\"SigningProtocol\":\"sigv4\",\"SigningBehavior\":\"always\",\"OriginAccessControlOriginType\":\"s3\"}" \
  --profile "$AWS_PROFILE" \
  --query "OriginAccessControl.Id" --output text)

GEO_BLOCK=""
if [ "$GEO_RESTRICT_JP" = "true" ]; then
  GEO_BLOCK='"GeoRestriction":{"RestrictionType":"whitelist","Quantity":1,"Items":["JP"]}'
else
  GEO_BLOCK='"GeoRestriction":{"RestrictionType":"none","Quantity":0}'
fi

ALIASES_BLOCK='"Aliases":{"Quantity":0}'
VIEWER_CERT='"ViewerCertificate":{"CloudFrontDefaultCertificate":true,"MinimumProtocolVersion":"TLSv1"}'
if [ -n "$DOMAIN" ]; then
  ALIASES_BLOCK="\"Aliases\":{\"Quantity\":1,\"Items\":[\"$DOMAIN\"]}"
  VIEWER_CERT="\"ViewerCertificate\":{\"ACMCertificateArn\":\"$CERT_ARN\",\"SSLSupportMethod\":\"sni-only\",\"MinimumProtocolVersion\":\"TLSv1.2_2021\"}"
fi

cat > /tmp/cf_config.json <<EOF
{
  "CallerReference": "$(date +%s)-$BUCKET_NAME",
  "Comment": "AI OSI URI $PROJECT_NAME static site",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  $ALIASES_BLOCK,
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "s3-$BUCKET_NAME",
      "DomainName": "$BUCKET_NAME.s3.$AWS_REGION.amazonaws.com",
      "OriginAccessControlId": "$OAC_ID",
      "S3OriginConfig": {"OriginAccessIdentity": ""}
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-$BUCKET_NAME",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "Compress": true,
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {"ErrorCode": 403, "ResponseCode": "200", "ResponsePagePath": "/index.html", "ErrorCachingMinTTL": 0},
      {"ErrorCode": 404, "ResponseCode": "200", "ResponsePagePath": "/index.html", "ErrorCachingMinTTL": 0}
    ]
  },
  "PriceClass": "PriceClass_200",
  "Restrictions": {$GEO_BLOCK},
  $VIEWER_CERT
}
EOF

DIST_JSON=$(aws cloudfront create-distribution \
  --distribution-config "file:///tmp/cf_config.json" \
  --profile "$AWS_PROFILE")

DIST_ID=$(echo "$DIST_JSON" | jq -r ".Distribution.Id")
DIST_DOMAIN=$(echo "$DIST_JSON" | jq -r ".Distribution.DomainName")
DIST_ARN=$(echo "$DIST_JSON" | jq -r ".Distribution.ARN")
echo "INFO: DIST_ID=$DIST_ID, DOMAIN=$DIST_DOMAIN"
```

---

## Step 7: S3 バケットポリシー（OAC 限定）

```bash
cat > /tmp/bucket_policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontServicePrincipal",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::$BUCKET_NAME/*",
    "Condition": {"StringEquals": {"AWS:SourceArn": "$DIST_ARN"}}
  }]
}
EOF

aws s3api put-bucket-policy --bucket "$BUCKET_NAME" \
  --policy "file:///tmp/bucket_policy.json" --profile "$AWS_PROFILE"
```

---

## Step 8: Route 53 レコード（DOMAIN 指定時）

```bash
if [ -n "$DOMAIN" ] && [ -n "$ROUTE53_ZONE_ID" ]; then
  aws route53 change-resource-record-sets --hosted-zone-id "$ROUTE53_ZONE_ID" \
    --profile "$AWS_PROFILE" \
    --change-batch "{
      \"Changes\": [{
        \"Action\": \"UPSERT\",
        \"ResourceRecordSet\": {
          \"Name\": \"$DOMAIN\",
          \"Type\": \"A\",
          \"AliasTarget\": {
            \"HostedZoneId\": \"Z2FDTNDATAQYW2\",
            \"DNSName\": \"$DIST_DOMAIN\",
            \"EvaluateTargetHealth\": false
          }
        }
      }]
    }"
fi
```

---

## Step 9: ファイル同期

```bash
aws s3 sync "$INPUT_DIR" "s3://$BUCKET_NAME/" \
  --delete --profile "$AWS_PROFILE" \
  --exclude ".git/*" --exclude "node_modules/*" --exclude ".env*"

# HTML は短いキャッシュ
aws s3 cp "s3://$BUCKET_NAME/" "s3://$BUCKET_NAME/" \
  --recursive --exclude "*" --include "*.html" \
  --metadata-directive REPLACE --cache-control "max-age=300, public" \
  --content-type "text/html; charset=utf-8" \
  --profile "$AWS_PROFILE" 2>/dev/null || true
```

---

## Step 10: CloudFront キャッシュ Invalidation

```bash
INV_PATHS="${CACHE_INVALIDATE_PATHS:-/*}"
INV_ITEMS=$(echo "$INV_PATHS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')
INV_QUANTITY=$(echo "$INV_PATHS" | awk -F',' '{print NF}')

aws cloudfront create-invalidation --distribution-id "$DIST_ID" \
  --invalidation-batch "{\"Paths\":{\"Quantity\":$INV_QUANTITY,\"Items\":$INV_ITEMS},\"CallerReference\":\"$(date +%s)\"}" \
  --profile "$AWS_PROFILE" >/dev/null 2>&1 || true
```

---

## Step 11: state.json 返却

```bash
if [ -n "$DOMAIN" ]; then
  APP_URL="https://$DOMAIN"
else
  APP_URL="https://$DIST_DOMAIN"
fi

cat <<EOF
{
  "APP_URL": "$APP_URL",
  "BUCKET_NAME": "$BUCKET_NAME",
  "CLOUDFRONT_ID": "$DIST_ID",
  "CLOUDFRONT_DOMAIN": "$DIST_DOMAIN",
  "ACM_CERT_ARN": "${CERT_ARN:-}",
  "REGION": "$AWS_REGION",
  "AWS_ACCOUNT": "$AWS_ACCOUNT"
}
EOF
```

---

## ロールバック責務マップ

| 失敗箇所 | 既作成リソース | ロールバック方針 |
| --- | --- | --- |
| Step 4 ACM 失敗 | なし | エラー表示して中断 |
| Step 4 DNS 検証タイムアウト | ACM 証明書 | ARN 表示、手動削除コマンド案内 |
| Step 5 S3 作成失敗 | ACM 証明書 | 同上 |
| Step 6 CloudFront 作成失敗 | ACM 証明書, S3 バケット | バケット名表示、削除コマンド案内 |
| Step 7 バケットポリシー失敗 | + CloudFront | CloudFront ID 表示、削除手順案内 |
| Step 8 Route 53 失敗 | 全部 | レコードのみ手動追加を案内 |
| Step 9 sync 失敗 | 全部 | 再実行可能。エラーログ表示 |

**自動削除はしない**（コスト発生中のリソースなので、ユーザーの明示的判断を仰ぐ）。

---

## エラー時の挙動

| エラー | 原因 | 対応 |
| --- | --- | --- |
| AWS 認証 401 | AWS_PROFILE 不正 | setup-deploy-environment 再実行 |
| バケット作成 409 | グローバル名前重複 | 5 回サフィックス採番、失敗時中断 |
| ACM 検証タイムアウト | DNS 反映遅延 | Step 4 で 5 分待機、超過なら ARN 表示 |
| Route 53 NoSuchHostedZone | ZONE_ID 不正 | 入力やり直し、DOMAIN なしで再実行 |
| CloudFront Throttling | レート制限 | exponential backoff で 3 回再試行 |

---

## 注意事項

- このスキルは **静的サイト専用**。Next.js SSR / API Routes が必要なら `aws-amplify-deploy` (Phase B) を使うこと
- CloudFront ディストリビューションは **削除完了まで 30 分以上**かかる
- ACM 証明書は **us-east-1 限定**（CloudFront の制約）
- カスタムドメイン使用時、Route 53 Hosted Zone は **同じアカウントにある**こと
- `GEO_RESTRICT_JP=true` は医療系想定オプション、一般 LP では `false`（デフォルト）
- 再デプロイは `aws s3 sync` + Invalidation だけで済むので、将来 `aws-static-redeploy` を切り出す予定
