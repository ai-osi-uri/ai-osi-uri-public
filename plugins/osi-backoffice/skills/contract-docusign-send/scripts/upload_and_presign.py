#!/usr/bin/env python3
"""
contract-docusign-send / upload_and_presign.py

Cowork 側にある契約書ファイル（PDF/DOCX）を、DocuSign が remoteUrl 経由で
一度だけ取得できるよう、非公開 S3 バケットにアップロードし、SigV4・
リージョナルの署名付き GET URL を発行して標準出力に1行で返す。

前提:
  - 呼び出し前に AWS-MCP (call_aws) で `aws sts get-federation-token` を
    PutObject/GetObject 限定・短命で発行し、その一時資格情報を環境変数
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN に渡すこと。
  - boto3 が無ければ自動で pip install を試みる。

使い方:
  python3 upload_and_presign.py \
      --file "/path/to/契約書.pdf" \
      --bucket aiosiuri-contract-staging-135728714359 \
      --key "outbound/2026-06/Every-WiLL_NDA_20260624.pdf" \
      --region ap-northeast-1 \
      --expires 1800

出力（成功時、最終行）:
  PRESIGNED_URL=https://....

注意:
  - バケットは「公開アクセス全ブロック＋1日で自動失効」を前提とする。
  - 署名付き URL は推測困難・短命。DocuSign が取得したら役目は終わり。
"""
import argparse
import os
import sys
import subprocess


def ensure_boto3():
    try:
        import boto3  # noqa
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "boto3"],
            check=True,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="アップロードする契約書のローカルパス")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--key", required=True, help="S3 オブジェクトキー（例: outbound/YYYY-MM/相手先_契約名_日付.pdf）")
    ap.add_argument("--region", default="ap-northeast-1")
    ap.add_argument("--expires", type=int, default=1800, help="署名付きURLの有効秒数（既定30分）")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        if not os.environ.get(var):
            print(f"ERROR: env {var} is not set. 先に call_aws で federation token を発行して環境変数に渡してください。", file=sys.stderr)
            sys.exit(3)

    ensure_boto3()
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        region_name=args.region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )

    # content-type を拡張子から軽く推定（DocuSign は fileExtension でも判定可）
    ext = os.path.splitext(args.file)[1].lower()
    ctype = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }.get(ext, "application/octet-stream")

    s3.upload_file(args.file, args.bucket, args.key, ExtraArgs={"ContentType": ctype})

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": args.bucket, "Key": args.key},
        ExpiresIn=args.expires,
    )
    print(f"S3_KEY={args.key}", file=sys.stderr)
    print(f"PRESIGNED_URL={url}")


if __name__ == "__main__":
    main()
