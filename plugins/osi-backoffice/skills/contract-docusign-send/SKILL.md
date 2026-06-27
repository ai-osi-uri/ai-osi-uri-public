---
name: contract-docusign-send
description: >
  AI OSI URI のバックオフィス向け「契約書を内容チェックして DocuSign で署名依頼を送る」スキル。
  Cowork にアップロードされた契約書（PDF / docx）を読み取り、(1) 基本項目の整合・(2) 金額/期間/条件・
  (3) リスク条項・(4) 自社雛形との差分、の4観点でチェックして人レビュー用に提示し、承認後に署名者を
  契約書から抽出して確認したうえで、DocuSign の封筒（Envelope）を作成して送付する。送った契約書は
  Drive の `30.契約管理/` に格納し、送付メタ（envelope ID・署名者・日時）を記録する。
  「契約書をアップしたのでチェックして DocuSign で送って」「この契約書を署名依頼に回して」
  「○○社の契約書を内容確認して送付」「NDA を DocuSign で送りたい」「業務委託契約を電子署名で送って」
  「契約書レビューして署名依頼」など、契約書の内容確認 → 電子署名送付に関わるリクエストで発動する。
  送付方向は選択式：自社から DocuSign で送る場合と、先方が送付する（自社は内容チェックのみ）場合の両方に対応する。
  ※ 契約書そのものを新規作成するのは nda-creation 等の役割。受領契約 → 請求スケジュール化は
  osi-finance の keiri-contract-intake。本スキルは「手元の契約書をチェックして送る」ことに特化する。
requires_connectors:
  - server: docusign
    provision: user-install
---

# contract-docusign-send（契約書チェック → DocuSign 送付）

契約書を「丸腰で送らない」ためのバックオフィス・ゲート。アップロードされた契約書を
**人がレビューしやすい形に整理 → 承認 → 署名者確認 → DocuSign 送付 → Drive 格納**まで一気通貫で行う。

契約は重要文書なので、**誤送信を絶対に起こさない設計**を最優先する。DocuSign 送付は必ず
2段階（まず `status=created` でドラフト作成 → 人が最終確認 → 送信）で行う。

## 役割と非役割

- やる：契約書の取り込み → 4観点チェックの提示 → 署名者抽出・確認 → DocuSign 封筒作成（ドラフト→送信）→ Drive 格納＋メタ記録。
- やらない：契約書の新規作成（= `nda-creation` 等）／受領契約の請求スケジュール化（= `osi-finance/keiri-contract-intake`）／法的助言（弁護士ではない旨を添える）。

## 最重要ルール：送信は人が DocuSign から行う（Claude は送信しない）

**Claude は契約書を送信しない。** 封筒の最終送信は必ず人が DocuSign 上で行う。これが本スキルの絶対原則。

- 封筒は必ず `status:"created"`（ドラフト）で作り、**そこで止める**。`status:"sent"` への自動更新はしない。
- DocuSign は封筒作成（ドラフト）時点で remoteUrl から PDF を取り込み、自前で保存する。**そのため署名付き URL が失効した後でも、人は DocuSign 上でいつでも送信できる。**
- Claude はドラフト作成後、**署名者・件名・添付・署名欄位置を提示し、「DocuSign の下書き（Drafts）を開いて内容を確認 → 送信してください」と案内する**。
- 例外：人が「API から送信まで実行して」と**明示的に依頼した場合に限り**、`AskUserQuestion` で最終確認を取ったうえで `updateEnvelope status:"sent"` を行ってよい。依頼が無ければ送信しない。
- 宛先メールは人が確認・確定する（推測で送らない）。テスト時は相手先ではなく自分宛など安全な宛先を使う。

## 前提コネクタ・環境

- **DocuSign**（必須）：`getUserInfo` / `createEnvelope` / `getEnvelope` / `updateEnvelope`。
  - アカウント取得：`getUserInfo` → `accounts[0].account_id` を使う（現状 `4b9f3d90-07bf-4f81-8041-a5c43b6e2bda`、base `jp1.docusign.net`）。
- **AWS（aws-api-mcp の `call_aws`）**（必須）：契約書をDocuSignへ渡すための一時公開URL発行に使う。詳細は `references/docusign-and-s3.md`。
  - 専用バケット：`aiosiuri-contract-staging-135728714359`（ap-northeast-1 / 公開アクセス全ブロック / 1日で自動失効）。
- **Cowork bash**：S3 へのアップロードと署名付きURL生成（`scripts/upload_and_presign.py`）に使う。
- **Drive（マウント済み共有ドライブ）**：格納先 `30.契約管理/`。書き込みはマウント経由で Drive に同期される。

> なぜ S3 が要るか：DocuSign の `createEnvelope` は base64 アップロード不可で、**公開HTTP URL（remoteUrl）経由でしか**
> ドキュメントを取り込めない。任意のアップロード契約書を送るため、非公開S3に一時的に置き、推測困難・短命の
> 署名付きURLで一度だけ取得させる（DocuSignが取得したら役目終了、1日で自動失効）。

## ワークフロー

### Step 0. 参照情報（自社情報）の確認 — 初回必須・汎用配布対応

このスキルは複数の組織・担当者に配布される前提。**契約処理に入る前に、必ず `references/issuer-info.md` の「設定状態」を確認する。**

- 「設定状態」が `未設定`、空欄、またはプレースホルダ（例：`<法人番号を記入>` 等）のまま →
  **そこで停止**し、利用者に自社情報（正式法人名・法人番号・本店所在地・代表者・電話・インボイス番号）を確認する。
  可能なら法人番号公表サイト（https://www.houjin-bangou.nta.go.jp/）または gBizINFO（https://info.gbiz.go.jp/）で
  **法人番号と社名・住所を照合**し、一致を確認したうえで `issuer-info.md` を更新（`設定状態: 確認済み（YYYY-MM-DD / 出典）`）してから先へ進む。
- 「設定状態」が `確認済み` → 通常どおり Step 1 へ進む。ただし契約書の自社欄と issuer-info が食い違う場合は「要確認」で人に提示する（既存ルールどおり）。

> 目的：配布先が初期設定なしで使い始め、他社名のまま契約書を作ってしまう事故を防ぐ。社名は表記ゆれ（全角/半角・スペース・ハイフン）に特に注意。

### Step 1. 契約書の取り込み
- アップロードファイルは `uploads/` にある。パスが不明なら直近のアップロードを使う。
- 形式が docx の場合、**チェック用のテキスト**を pandoc で抽出し、**送付用の PDF**を生成する（署名欄の見た目を安定させるため）。
  ```bash
  # テキスト抽出（チェック用）
  pandoc "<契約書.docx>" -t plain
  # PDF化（送付用。libreoffice があれば優先、無ければ後述の代替）
  soffice --headless --convert-to pdf --outdir <作業ディレクトリ> "<契約書.docx>"
  ```
  - PDF化できない環境では docx のまま送付してよい（`createEnvelope` は fileExtension 自動判定）。ただし署名欄位置の確実性は PDF が上。
- すでに PDF ならそのまま使う。

### Step 2. 内容チェック（4観点）→ 人レビュー提示
`references/contract-checklist.md` のチェックリストに沿って読み取り、**表形式で論点を提示**する。
最低限、次を必ず確認・提示する。

1. **基本項目の整合**：当事者（甲/乙）の正式名称・住所・代表者、自社情報（`references/issuer-info.md` と一致するか）、契約日、署名欄の有無。
2. **金額・期間・条件**：報酬額・契約期間・更新条件・支払条件などの数値と抜け漏れ。
3. **リスク条項**：責任制限・損害賠償・解約・知財帰属・秘密保持・準拠法/管轄など、自社に不利な点。
4. **雛形との差分**：自社標準雛形（`30.契約管理/01.契約書雛形/`）と比較し、変更・追加・削除箇所。NDAなら `（雛形）機密保持契約書_*.docx`、業務委託なら `00.業務委託契約書雛形/`。

> 出力は「問題なし／要確認／要修正」のラベル付きで簡潔に。Claude は弁護士ではないため、
> リスク指摘は「確認を促す」トーンに留め、最終判断は人に委ねる。

### Step 3. 署名者の抽出と確認（必須ゲート）
- 契約書末尾の署名欄（甲・乙ブロック）から**署名者の氏名・会社名・肩書**を抽出する。
  - 例：甲＝相手先（代表取締役 氏名）、乙＝AI OSI URI 株式会社（代表取締役 渚 有瓶）。
- **メールアドレスは契約書に無い**ため、`AskUserQuestion` で各署名者のメールを確認する（営業管理表があれば候補提示）。
- 署名順（routingOrder）・CC（社内控え等）も確認する。既定は 甲→乙 の順、または同時。

### Step 3.5. 送付方法の選択（必須）
契約は「自社から送る」場合と「先方が送ってくれる」場合がある。`AskUserQuestion` で送付方向を確認する。

- **自社から送付（DocuSign）**：Step 4・5 に進む（S3 → DocuSign ドラフト作成 → 人が DocuSign で送信）。
- **先方が送付**：自社は電子署名の発信者にならない。**DocuSign 封筒・S3 アップロードは行わない。**
  - Step 2 のチェック結果と Step 3 の署名者情報を整理して人に渡す。
  - 必要なら「先方に送付を依頼する文面（メール下書き）」を作る（誰が・どのアドレスに送るか、署名者は誰か）。
  - 受領後の契約は `30.契約管理/` への格納（または `osi-finance/keiri-contract-intake`）で扱う。Step 6（格納）は受領後に実施。
  - この場合は Step 4・5 を**スキップ**して Step 6/7 へ。

### Step 4. S3 へアップロードして署名付きURLを発行（自社送付の場合のみ）
詳細手順は `references/docusign-and-s3.md`。要点：

1. `call_aws` で **PutObject+GetObject 限定・短命（例 3600秒）**の federation token を発行：
   ```
   aws sts get-federation-token --name osi-ds-io --duration-seconds 3600 \
     --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:PutObject","s3:GetObject"],"Resource":"arn:aws:s3:::aiosiuri-contract-staging-135728714359/*"}]}'
   ```
2. 返ってきた一時資格情報を環境変数にして、bash でアップロード＋署名付きURL生成：
   ```bash
   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...
   python3 <skill>/scripts/upload_and_presign.py \
     --file "<送付用PDF>" \
     --bucket aiosiuri-contract-staging-135728714359 \
     --key "outbound/$(date +%Y-%m)/<相手先>_<契約名>_<YYYYMMDD>.pdf" \
     --expires 1800
   ```
   - 末尾行 `PRESIGNED_URL=...` を次の Step で remoteUrl に使う。

### Step 5. DocuSign 封筒の作成（ドラフトで止める。送信は人が DocuSign で行う）
**ドラフト（`status=created`）で作って止める。Claude は送信しない。**

```
createEnvelope(
  accountId = <getUserInfo の account_id>,
  envelopeDefinition = {
    status: "created",                       # ← まずドラフト
    emailSubject: "【AI OSI URI】<契約名> ご署名のお願い",
    documents: [{ documentId:"1", name:"<契約名>.pdf", remoteUrl:"<PRESIGNED_URL>" }],
    recipients: { signers: [
      { recipientId:"1", routingOrder:"1", name:"<甲署名者>", email:"<甲メール>",
        tabs:{ signHereTabs:[{ documentId:"1", recipientId:"1", anchorString:"<甲の会社名or代表者名>", anchorUnits:"pixels", anchorYOffset:"-8" }] } },
      { recipientId:"2", routingOrder:"2", name:"渚 有瓶", email:"<乙メール>",
        tabs:{ signHereTabs:[{ documentId:"1", recipientId:"2", anchorString:"AI OSI URI", anchorUnits:"pixels", anchorYOffset:"-8" }] } }
    ]}
  }
)
```
- 署名タブは署名欄の会社名/代表者名を `anchorString` にして配置する（offset は実物で微調整）。
- ドラフト作成後、**`getEnvelope` / `listRecipients` で内容を確認**し、署名者・件名・ドキュメント・署名欄位置を人に提示。
- **そのまま止めて、人に DocuSign での送信を案内する**：「DocuSign → Manage → 下書き（Drafts）で envelope『{件名}』（ID: {envelopeId}）を開き、内容を確認して送信してください」。
- 修正が必要なら、ドラフトを作り直す（または `updateEnvelope` で件名等を修正）。中止なら `updateEnvelope` で `status:"voided"`（voidedReason 必須）。
- **API から送信するのは、人が明示的に依頼した時だけ**：その場合のみ `AskUserQuestion` で最終確認 → `updateEnvelope status:"sent"`。

> 安全原則：**既定では Claude は送信しない。** 送信操作は人が DocuSign 上で行う。これが誤送信・誤宛先の最後の砦。

### Step 6. Drive へ格納 ＋ 送付メタ記録
格納先・命名は `references/storage-and-naming.md` に従う。要点：

- **受注（自社が顧客に署名依頼）**：`30.契約管理/03.締結済み契約（受注）/{ID}.{企業名}/_送付中/` に送付PDFを置く。
- **発注（自社が受け取る側）**：`30.契約管理/02.締結済み契約（発注）/{カテゴリ}/_送付中/`。
- 送付メタを同フォルダに `_送付メタ_<契約名>_<YYYYMMDD>.md` として残す（envelope ID・署名者・送付日時・S3キー・URL有効期限）。テンプレは `references/storage-and-naming.md`。
- 署名完了後（別途確認時）に `_送付中/` から確定フォルダへ移し、完成PDFを保存する。

### Step 7. 出力サマリ
人に次を簡潔に伝える：
1. チェック結果サマリ（問題なし/要確認/要修正の件数と主な論点）
2. 送付した署名者・件名・envelope ID（または「ドラフト作成済み、送信待ち」）
3. Drive 格納先パス
4. 注意点（Claude は弁護士ではない旨、リスク指摘は要確認レベル）

## 留意

- **誤送信防止が最優先。** 既定では Claude は送信しない（ドラフトで止め、人が DocuSign 上で送信）。宛先メールは人に確認させる。
- 金額・当事者・期間が契約書から判然としない場合は推測せず人に確認する。
- S3 の署名付きURLは短命・非公開バケット由来。チャットやメタファイルに**生のURLや一時資格情報を残さない**（メタにはS3キーと有効期限のみ）。
- 機密保持契約（NDA）・業務委託・レベニューシェア等、種別に応じて雛形の比較対象を変える。
- このスキルはプラグインのソース（読み取り専用インストール版）であり、案件情報をここに保存しない。成果物は outputs か Drive `30.契約管理/` へ。
