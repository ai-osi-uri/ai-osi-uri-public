---
name: tf-state-backend
description: |
  Terraform state を、揮発する作業フォルダではなく自社 AWS の共有 S3 バケット（+
  DynamoDB ロック）で一元管理する。バケット/ロックテーブルの冪等作成、`backend "s3"`
  の差し込み、既存ローカル state の `-migrate-state` 移行、S3 格納の検証まで。
  「tfstate が消えると困る」「Terraform state を S3 に」「リモート backend に移行」
  「orphan 化が心配」「別セッションでも terraform を続けたい」で発動。新規は
  `create-app` の初回 apply 前、既存アプリは移行として使う。
version: 0.1.0
---

# Terraform state の共有S3 backend 管理（atomic）

Cowork のセッション作業フォルダ（`.../outputs/...`）は**セッション間でクリアされる揮発領域**。
ここに `terraform.tfstate` を置いたままにすると、フォルダが消えた時に **AWSリソースは動き続ける
（課金も続く）のに state が失われ、Terraform できれいに管理・削除できなくなる**（orphan化）。

本スキルは state を **自社AWSアカウントの共有S3バケット（DynamoDBロック付き）** に置き、
セッション/フォルダから独立させる。これにより**どのセッションからでも `terraform init` だけで
同じ state を参照**できる。

> アプリ本体（S3+CloudFront / Lambda / DynamoDB 等）の作成は `aws-static-deploy` / `create-app`（旧 deploy-app）。
> 本スキルは **state の置き場所だけ**を扱う atomic スキル。

---

## 定数（AI OSI URI 既定）

| 項目 | 値 |
| --- | --- |
| stateバケット | `aiosiuri-tfstate-<ACCOUNT_ID>`（例: `aiosiuri-tfstate-135728714359`） |
| リージョン | `ap-northeast-1`（東京・データ所在地を国内に統一） |
| ロックテーブル(DynamoDB) | `aiosiuri-tf-lock`（HASHキー `LockID`, type S） |
| state キー命名 | `<namespace>/<project>/terraform.tfstate`（例: `colowide/fair-detector/terraform.tfstate`） |
| バケット設定 | バージョニング有効・AES256暗号化・パブリックアクセス全ブロック |

`<namespace>` は案件/事業の束（例: `colowide`）、`<project>` はアプリ名（リポ名）。

---

## 入力契約

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `REPO_DIR` | ✅ | 対象アプリのローカル絶対パス（`infra/` を含む） |
| `NAMESPACE` | ✅ | state キーの第1階層（案件束。例 `colowide`） |
| `PROJECT` | ✅ | state キーの第2階層（アプリ名。例 `fair-detector`） |
| `MODE` | 任意 | `auto`（既定）/`bootstrap-new`/`migrate-existing`。autoは既存stateの有無で自動判定 |

AWS 認証は **「AI OSI URI Deploy」拡張**が保持（チャットに鍵は出さない）。
bucket/lock の作成は AWS API（`call_aws` 等）で、移行は拡張の `aws_terraform_apply`(prebuild) で行う。

---

## ワークフロー

```
1. アカウントID取得（aws sts get-caller-identity）→ バケット名確定
2. state基盤の bootstrap（idempotent）：バケット/ロックが無ければ作成、設定を適用
3. infra/backend.tf を生成（S3 backend 定義）
4. state を S3 へ：
   - 新規(bootstrap-new)：そのまま deploy-app/apply に進む（初回 init でS3に作られる）
   - 既存(migrate-existing)：terraform init -migrate-state -force-copy でローカル→S3へコピー
5. S3 に state が格納されたか検証
6. コード一式＋HANDOFF を共有ドライブへ退避（揮発対策）
7. 結果サマリ（バケット/キー/ロック/URL）を返す
```

---

## Step 1-2: state基盤の bootstrap（idempotent）

`scripts/bootstrap_state_backend.sh` を使う。**既にあれば作らない**ので何度実行しても安全。

```bash
# 例：call_aws / aws CLI が使える環境で
bash scripts/bootstrap_state_backend.sh
# → ACCOUNT_ID を取得し、aiosiuri-tfstate-<ACCOUNT_ID> と aiosiuri-tf-lock を確認/作成
```

Cowork で `call_aws`（aws-api MCP）しか無い場合は、スクリプトの各 `aws` 行を `call_aws` で
1コマンドずつ実行してもよい（順序は同じ）。バケット作成→versioning→encryption→public-access-block→
DynamoDB ロックテーブルの順。

> インライン JSON を渡す `put-bucket-encryption` は、バッチではなく**単発**で実行する
> （配列で渡すと一部CLIラッパでパースに失敗することがある）。

---

## Step 3: backend.tf を生成

`infra/backend.tf` を作る（`<ACCOUNT_ID>`/`<NAMESPACE>`/`<PROJECT>` を埋める）。

```hcl
# state は揮発する作業領域ではなく、自社AWSの共有S3で一元管理（DynamoDBでロック）。
# これによりセッション/フォルダから独立し、別セッションでも同じ state を参照できる。
terraform {
  backend "s3" {
    bucket         = "aiosiuri-tfstate-<ACCOUNT_ID>"
    key            = "<NAMESPACE>/<PROJECT>/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "aiosiuri-tf-lock"
    encrypt        = true
  }
}
```

`provider "aws"` に `skip_credentials_validation = true` 等が付いていてもS3 backendは動く
（backendは拡張のAWS認証を使う）。

---

## Step 4: state を S3 へ

### 4-a. 新規アプリ（bootstrap-new）
backend.tf を入れた状態で **deploy-app / aws_terraform_apply をそのまま実行**すれば、
初回 `terraform init` がS3 backendを初期化し、state は最初からS3に作られる。**migrate不要**。

### 4-b. 既存アプリ（migrate-existing）
既にローカル `infra/terraform.tfstate` がある場合は、拡張の `aws_terraform_apply` の
**`prebuild` で migrate を実行**する（prebuildは拡張のAWS認証付きでterraformを動かせる）。

```
aws_terraform_apply(
  repo_dir = REPO_DIR,
  prebuild = "cd infra && terraform init -migrate-state -force-copy -input=false -no-color"
)
```

`-migrate-state -force-copy` でローカルstateをS3へコピー（プロンプトなし）。その後ツール本体の
`terraform init`→`apply` が走り、**「No changes / 0 destroyed」**になればS3 state と実リソースが
一致＝移行成功。

> 注意：mcpb の `terraform init` は `-migrate-state` を付けないため、**移行は必ず prebuild 側で**行う。

---

## Step 5: S3 格納の検証

```bash
aws s3 ls s3://aiosiuri-tfstate-<ACCOUNT_ID>/<NAMESPACE>/ --recursive
# → <NAMESPACE>/<PROJECT>/terraform.tfstate が出れば成功
```

---

## Step 6: 揮発対策（コード退避＋HANDOFF）

state はS3で安全になったが、**backend.tf を含む infra コードが揮発フォルダだけにあると
復旧時にバケット/キーが分からなくなる**。コード一式を共有ドライブの案件フォルダへ退避する。

```bash
EXC="--exclude=.terraform --exclude=.terraform.lock.hcl --exclude=.tfrun \
     --exclude=terraform.tfstate --exclude=terraform.tfstate.backup \
     --exclude=.git --exclude=node_modules --exclude=__pycache__ --exclude=.build"
rsync -a $EXC "$REPO_DIR/" "<Drive案件フォルダ>/aws-repo-<PROJECT>/"
```

`terraform.tfstate*` は **退避しない**（S3が正本。古いローカルstateをDriveに置くと混乱の元）。
あわせて案件フォルダ直下に `HANDOFF_AWS管理.md`（URL・バケット・キー・ロック・手順）を残す。
雛形は `references/handoff-template.md` を使う。

---

## ガードレール（絶対厳守）

- state用バケット `aiosiuri-tfstate-*` と DynamoDB `aiosiuri-tf-lock` は **state管理専用**。
  中身を手で消さない（消すと全アプリの state を喪失）。`aws_terraform_destroy` の対象にもしない。
- アプリを撤去する時は、対象リポで `aws_terraform_destroy`（confirm必須）。**state基盤は残す**。
  全アプリ撤去後に基盤を畳む場合のみ、最後に手動でバケット/テーブルを削除。
- 認証鍵（AWSシークレット）は**チャットに出さない**。bucket作成も移行も拡張/aws-api MCP経由で。
- 移行後、各リポのローカル `infra/terraform.tfstate*` はもう正本ではない。残っていてもinit時はS3優先で
  問題ないが、混乱回避のため削除可。

---

## 完了時の返却（例）

```json
{
  "state_bucket": "aiosiuri-tfstate-135728714359",
  "state_key": "colowide/fair-detector/terraform.tfstate",
  "lock_table": "aiosiuri-tf-lock",
  "region": "ap-northeast-1",
  "mode": "migrate-existing",
  "verified_in_s3": true,
  "code_persisted_to": "02.食材在庫早期警戒システム/aws-repo-fair-detector/"
}
```

---

## このスキルが呼ばれる場面

- `create-app`（旧 deploy-app） の **AWSパス初回 apply 前**（bootstrap-new）：新規アプリを最初からS3 backendに。
- 既にローカルstateで動いている**既存アプリの移行**（migrate-existing）：単体で発動。
- 「stateどこ？」「orphanが怖い」「別セッションで続けたい」等の**state保全の相談**。
