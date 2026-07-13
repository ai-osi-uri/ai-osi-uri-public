#!/usr/bin/env bash
# Terraform state 基盤（共有S3バケット + DynamoDBロック）を idempotent に用意する。
# 既に存在すれば作らず、設定だけ冪等に当て直す。AWS認証は環境（拡張/プロファイル）に従う。
#
# 使い方:
#   bash bootstrap_state_backend.sh
# 環境変数:
#   AWS_REGION   既定 ap-northeast-1
#   LOCK_TABLE   既定 aiosiuri-tf-lock
#   BUCKET_PREFIX 既定 aiosiuri-tfstate-   （末尾に AccountId を付ける）
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-1}"
LOCK_TABLE="${LOCK_TABLE:-aiosiuri-tf-lock}"
BUCKET_PREFIX="${BUCKET_PREFIX:-aiosiuri-tfstate-}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET_PREFIX}${ACCOUNT_ID}"
echo "INFO: account=${ACCOUNT_ID} region=${REGION} bucket=${BUCKET} lock=${LOCK_TABLE}"

# ---- S3 バケット（無ければ作成） ----
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "INFO: bucket exists: $BUCKET"
else
  echo "INFO: creating bucket: $BUCKET"
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
fi

# ---- 冪等に設定を当てる ----
aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# ---- DynamoDB ロックテーブル（無ければ作成） ----
if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$REGION" >/dev/null 2>&1; then
  echo "INFO: lock table exists: $LOCK_TABLE"
else
  echo "INFO: creating lock table: $LOCK_TABLE"
  aws dynamodb create-table --table-name "$LOCK_TABLE" --region "$REGION" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
  aws dynamodb wait table-exists --table-name "$LOCK_TABLE" --region "$REGION"
fi

echo "DONE: state backend ready"
echo "{\"state_bucket\":\"${BUCKET}\",\"lock_table\":\"${LOCK_TABLE}\",\"region\":\"${REGION}\",\"account_id\":\"${ACCOUNT_ID}\"}"
