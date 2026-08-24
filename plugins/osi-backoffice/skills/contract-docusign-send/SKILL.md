---
name: contract-docusign-send
description: >
  AI OSI URI のバックオフィス向け「契約書を内容チェックして DocuSign で署名依頼を送る」スキル。
  Cowork にアップロードされた契約書（PDF / docx）を読み取り、(1) 基本項目の整合・(2) 金額/期間/条件・
  (3) リスク条項・(4) 自社雛形との差分、の4観点でチェックして人レビュー用に提示し、承認後に署名者を
  契約書から抽出して確認したうえで、DocuSign の封筒（Envelope）を作成して送付する。送った契約書は
  Drive の契約管理フォルダ（設定で指定）に格納し、送付メタ（envelope ID・署名者・日時）を記録する。
  「契約書をアップしたのでチェックして DocuSign で送って」「この契約書を署名依頼に回して」
  「○○社の契約書を内容確認して送付」「NDA を DocuSign で送りたい」「業務委託契約を電子署名で送って」
  「契約書レビューして署名依頼」など、契約書の内容確認 → 電子署名送付に関わるリクエストで発動する。
  送付方向は選択式：自社から DocuSign で送る場合と、先方が送付する（自社は内容チェックのみ）場合の両方に対応する。
  ※ 契約書そのものを新規作成するのは nda-creation 等の役割。受領契約 → 請求スケジュール化は
  osi-finance の osi-finance-contract-intake。本スキルは「手元の契約書をチェックして送る」ことに特化する。
requires_connectors:
  # 既定の経路。Claude のコネクタ一覧からボタン1つで接続でき、鍵の登録は要らない
  - server: docusign
    provision: user-connect
  # 台帳の読み書きと、Integration Key がある組織向けの ds_* に使う
  - server: ai-osi-uri-finance
    provision: user-install
---

# contract-docusign-send（契約書チェック → DocuSign 送付）

契約書を「丸腰で送らない」ためのバックオフィス・ゲート。アップロードされた契約書を
**人がレビューしやすい形に整理 → 承認 → 署名者確認 → DocuSign 送付 → Drive 格納**まで一気通貫で行う。

契約は重要文書なので、**誤送信を絶対に起こさない設計**を最優先する。DocuSign 送付は必ず
2段階（まず `status=created` でドラフト作成 → 人が最終確認 → 送信）で行う。

## 役割と非役割

- やる：契約書の取り込み → 4観点チェックの提示 → 署名者抽出・確認 → DocuSign 封筒作成（ドラフト→送信）→ Drive 格納＋メタ記録。
- やらない：契約書の新規作成（= `nda-creation` 等）／受領契約の請求スケジュール化（= `osi-finance/osi-finance-contract-intake`）／法的助言（弁護士ではない旨を添える）。

## 最重要ルール：送信は人が DocuSign から行う（Claude は送信しない）

**Claude は契約書を送信しない。** 封筒の最終送信は必ず人が DocuSign 上で行う。これが本スキルの絶対原則。

- 封筒は必ずドラフト（`send` を渡さない）で作り、**そこで止める**。送信への自動更新はしない。
- DocuSign は封筒作成（ドラフト）時点で PDF を自前で保存する。**そのため作成後はこちらのファイルに依存せず、人は DocuSign 上でいつでも送信できる。**
- Claude はドラフト作成後、**署名者・件名・添付・署名欄位置を提示し、「DocuSign の下書き（Drafts）を開いて内容を確認 → 送信してください」と案内する**。
- 例外：人が「API から送信まで実行して」と**明示的に依頼した場合に限り**、`AskUserQuestion` で最終確認を取ったうえで `ds_create_envelope(send: true)` を使ってよい。依頼が無ければ送信しない。
- 宛先メールは人が確認・確定する（推測で送らない）。テスト時は相手先ではなく自分宛など安全な宛先を使う。

## 前提コネクタ・環境

- **DocuSign（必須・公式 DocuSign MCP コネクタ）**：
  `createEnvelope` / `createEnvelopeFromTemplate` / `updateEnvelope` /
  `updateEnvelopeRecipients` / `updateEnvelopeTabs` / `getEnvelope` / `getEnvelopes` /
  `listEnvelopeDocuments` / `listRecipients` / `sendReminder`。
  Claude のコネクタ一覧から**ボタン1つで接続**でき、鍵の登録も設定も要らない
  （DocuSign 自身が公開しているアプリなので、Integration Key は DocuSign 側が持っている）。

  **できないのは1つだけ。手元のファイルを渡せない。**それ以外——受信者・署名順・CC・
  署名欄（`anchorString` 指定可）・件名・本文・リマインダー・有効期限・案件IDの埋め込み
  （`customFields`）・下書きで止める・後から受信者やタブを直す・送信・リマインド・取り消し
  ——は**すべてできる**。

  書類の渡し方は2通りしかない（2026-08-20 実地確認）。
  1. **`documents[].remoteUrl`**：DocuSign のサーバーが取りに行ける HTTP(S) URL。
     公開URLでの封筒作成は成功を確認済み。**認証が要る URL は不可**で、非公開の Google Drive
     ファイルを指すと `NO_DOCUMENT_RECEIVED`（バイトが取れない）になる。
  2. **既存の DocuSign テンプレート**（`templateId` / `createEnvelopeFromTemplate`）。

- **手元のファイルは人がアップロードする（既定の運用）**：
  本スキルはもともと「**送信は人が DocuSign の画面で行う**」が絶対原則で、人はどのみち
  DocuSign を開く。そこでファイルもドラッグしてもらい、**下書き（Drafts）を作ってもらう**。
  以降は `getEnvelopes` で拾い、`updateEnvelopeRecipients` / `updateEnvelopeTabs` /
  `updateEnvelope` で受信者・署名欄・件名を整える。

  > **試して駄目だったこと（同じ道を再探索しないために）。**
  > * Claude in Chrome での代行アップロード → `file_upload` がこの環境で使えない
  >   （`client converted paths before they reached the host`）。画面遷移とファイル入力欄の
  >   特定までは通るが、**渡す所だけができない**
  > * Google Drive を一時置き場にする → Drive コネクタの `share_file` は
  >   **メールアドレス指定の共有しかできず**、「リンクを知っている全員」を作れない。
  >   フォルダ側に手作業で公開設定をすれば動くが、初回の手作業が残る
  > * 本番 DocuSign アカウントで Integration Key を発行 → **画面に「実稼働環境では作成
  >   できません。開発者アカウントで作成し Go-Live を経て移行」と明記**されている

- **自前コネクタ（`ai-osi-uri-finance` の `ds_*`）＝上級者向け・任意**：
  `ds_create_envelope` は**台帳フォルダのファイルを base64 で直接送る**ので、URL も置き場所も
  要らない。ただし **Integration Key が必要**で、そのためには開発者アカウント（無料・即時）を
  作り、Go-Live を通す必要がある。通せる組織はこちらが最短。
  接続は `ds_connect`（ブラウザで「許可」を1回）、鍵の保存はコンソールの［DocuSign］画面。
  **未接続のまま `ds_create_envelope` を呼ぶと、送信せずに `need_connect` と認可URLを返す。**

- **AWS / S3 / Supabase：使わない。** 契約書のための置き場所を新設しない（2026-08-17 の判断を維持）。
- **Cowork bash**：契約書の PDF 変換や中身の確認に使う（アップロードには使わない）。
- **Drive（マウント済み共有ドライブ）**：格納先は `references/storage-and-naming.md` の定義に従う。**このスキルにパスを直書きしない**（組織ごとに違い、移行でも動く）。

> **ファイルの受け渡しについて：** 既定では**外に出さない**（人が DocuSign に直接アップする）。
> 自前コネクタを使う場合も、ファイルは HTTPS リクエストの本体としてしか出ず、置き場所を作らない。

### 書類を渡せないときにやってはいけないこと

- **契約書を恒久的な公開URLに置かない。**金額・住所・代表者名が入った文書を、認証なしで
  誰でも取得できる状態にしない。`remoteUrl` を使うなら、**取得後すぐ消せる一時コピー**に限る
  （原本の共有設定は絶対に触らない）。
- **勝手に置き場所（S3・当社サーバー等）を新設しない。**2026-08-17 に S3 方式を捨てたのは、
  置き場所・有効期限・消し忘れの管理が増えるからで、その判断は生きている。
  必要だと思ったら、実装せずに人へ選択肢として提示する。
- **送信まで自動でやらない。**下書きで止めるのは変わらない絶対原則。


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
  - PDF化できない環境では docx のまま送付してよい（`ds_create_envelope` が拡張子を判定する）。ただし署名欄位置の確実性は PDF が上。
- すでに PDF ならそのまま使う。

### Step 2. 内容チェック（4観点）→ 人レビュー提示
`references/contract-checklist.md` のチェックリストに沿って読み取り、**表形式で論点を提示**する。
最低限、次を必ず確認・提示する。

1. **基本項目の整合**：当事者（甲/乙）の正式名称・住所・代表者、自社情報（`references/issuer-info.md` と一致するか）、契約日、署名欄の有無。
2. **金額・期間・条件**：報酬額・契約期間・更新条件・支払条件などの数値と抜け漏れ。
3. **リスク条項**：責任制限・損害賠償・解約・知財帰属・秘密保持・準拠法/管轄など、自社に不利な点。
4. **雛形との差分**：自社標準雛形と比較し、変更・追加・削除箇所。**雛形は台帳の「雛形マスタ」タブから引く**（パスを直書きしない。組織ごとに違い、移行でも動くため）。区分で NDA／受注用／発注用を選ぶ。

> 出力は「問題なし／要確認／要修正」のラベル付きで簡潔に。Claude は弁護士ではないため、
> リスク指摘は「確認を促す」トーンに留め、最終判断は人に委ねる。

### Step 3. 署名者の抽出と確認（必須ゲート）
- 契約書末尾の署名欄（甲・乙ブロック）から**署名者の氏名・会社名・肩書**を抽出する。
  - 例：甲＝相手先（代表取締役 氏名）、乙＝自社（代表者名）。**自社の名義・代表者は `references/issuer-info.md` から取る**（Step 0 で確認済みのもの）。ここに具体名を書かない。
- **メールアドレスは契約書に無い**ため、`AskUserQuestion` で各署名者のメールを確認する（営業管理表があれば候補提示）。
- 署名順（routingOrder）・CC（社内控え等）も確認する。既定は 甲→乙 の順、または同時。

### Step 3.5. 送付方法の選択（必須）
契約は「自社から送る」場合と「先方が送ってくれる」場合がある。`AskUserQuestion` で送付方向を確認する。

- **自社から送付（DocuSign）**：Step 4・5 に進む（送付ファイルの確定 → DocuSign ドラフト作成 → 人が DocuSign で送信）。
- **先方が送付**：自社は電子署名の発信者にならない。**DocuSign 封筒は作らない。**
  - Step 2 のチェック結果と Step 3 の署名者情報を整理して人に渡す。
  - 必要なら「先方に送付を依頼する文面（メール下書き）」を作る（誰が・どのアドレスに送るか、署名者は誰か）。
  - 受領後の契約は契約管理フォルダへの格納（または `osi-finance/osi-finance-contract-intake`）で扱う。Step 6（格納）は受領後に実施。
  - この場合は Step 4・5 を**スキップ**して Step 6/7 へ。

### Step 4. 書類を DocuSign に載せる（自社送付の場合のみ）

**経路を1つ選ぶ。既定は A。**

**A. 人がアップロードする（既定・設定不要）**

1. 送付用の PDF（または docx）の場所を人に伝える。Drive の案件フォルダに置いておく。
2. 「DocuSign を開いて［今すぐ開始］→ このファイルを追加して、**下書きのまま閉じて**ください」と案内する。
3. 人が下書きを作ったら、`getEnvelopes`（`status=created`）で拾って `envelopeId` を得る。
4. `updateEnvelopeRecipients` で署名者・CC・署名順を、`updateEnvelopeTabs` で署名欄を、
   `updateEnvelope` で件名・本文を整える。**送信はしない。**

> 人はどのみち送信ボタンを押すために DocuSign を開く。**増える手間はドラッグ1回**で、
> 鍵も置き場所も要らない。この経路が壊れることは無い。

**B. `remoteUrl`（DocuSign が取りに行ける URL がすでにある場合のみ）**

`documents[].remoteUrl` に渡す。**認証が要る URL は使えない**（非公開 Drive は
`NO_DOCUMENT_RECEIVED` になる。2026-08-20 に確認済み）。
**この経路のために新しく公開の置き場所を作らない。**既に公開されている URL があるときだけ使う。

**C. 自前コネクタ（Integration Key がある組織のみ）**

`ds_create_envelope(documents: ["<台帳フォルダからの相対パス>"], ...)`。
台帳フォルダの外は拒否される。1ファイル 25MB まで。未接続なら `need_connect` が返る。

### Step 5. 封筒を整える（ドラフトで止める。送信は人が DocuSign で行う）

**既定はドラフト（`status: "created"`）。Claude は送信しない。**

新規に作る場合（経路 B / C）:

```
createEnvelope(
  accountId: "<getUserInfo で取得>",
  envelopeDefinition: {
    status: "created",                                  # 下書き。sent にしない
    emailSubject: "【<自社名>】<契約名> ご署名のお願い",
    emailBlurb:   "<宛名と依頼文>",
    documents: [{ documentId: "1", name: "<表示名>.pdf", remoteUrl: "<URL>" }],
    recipients: {
      signers: [
        { email:"<甲メール>", name:"<甲署名者>", recipientId:"1", routingOrder:"1",
          tabs: { signHereTabs:[{ anchorString:"<甲の会社名or代表者名>", documentId:"1", recipientId:"1" }],
                  dateSignedTabs:[{ anchorString:"<同上>", anchorYOffset:"40", documentId:"1", recipientId:"1" }] } },
        { email:"<乙メール>", name:"<乙署名者>", recipientId:"2", routingOrder:"2", tabs: { ... } }
      ],
      carbonCopies: [{ email:"<自社の共有アドレス>", name:"<自社控え>", recipientId:"3" }]
    },
    customFields: { textCustomFields: [{ name:"案件ID", value:"<案件ID>" }] }
  }
)
```

- **件名は必ず自分で書く。** 既定の `Docusignで送信: ファイル名.docx` は相手に届く件名として不適切で、
  `(1)` `(2)` のような連番までそのまま出る（実際に出ていた）。
- 署名欄は `anchorString`（目印の文字列）で置く。座標指定は雛形を1文字直すと崩れる。
- `accountId` は `getUserInfo` の `accounts[].account_id`（GUID）。**画面に出るアカウントIDの数字ではない。**
- 返ってくる `envelopeId` を Step 6 のメタに記録する。
- 状態の確認は `getEnvelope` / `getEnvelopes` / `listRecipients`。催促は `sendReminder`。

**送信は人が DocuSign の画面で行う。**外部への発信は取り消せないので、人の明示的な指示が無い限り
`status: "sent"` にしない。

### Step 6. Drive へ格納 ＋ 送付メタ記録
格納先・命名は `references/storage-and-naming.md` に従う。要点：

- **受注（自社が顧客に署名依頼）**：`{契約書ルート}/02.取引先別/{取引先ID}.{企業名}/受注（AR）/_送付中/` に送付PDFを置く。
- **発注（自社が受け取る側）**：`{契約書ルート}/02.取引先別/{取引先ID}.{企業名}/発注（AP）/_送付中/`。
- `{契約書ルート}` は組織ごとに違う。**直書きせず `references/storage-and-naming.md` の定義から解決する。**
- 送付メタを同フォルダに `_送付メタ_<契約名>_<YYYYMMDD>.md` として残す（envelope ID・署名者・送付日時・送付したファイルの相対パス）。テンプレは `references/storage-and-naming.md`。
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
- **DocuSign の秘密鍵・Integration Key をチャットやメタファイルに書かない。**設定は拡張の user_config（OSキーチェーン）にだけ置く。
- 機密保持契約（NDA）・業務委託・レベニューシェア等、種別に応じて雛形の比較対象を変える。
- このスキルはプラグインのソース（読み取り専用インストール版）であり、案件情報をここに保存しない。成果物は outputs か Drive の契約管理フォルダへ。
- **配布物なので、自社名・代表者名・フォルダパス・口座などの組織固有値をこのファイルに書かない。**
  自社情報は `references/issuer-info.md`、雛形とフォルダ構成は台帳（雛形マスタ）と設定から引く。
  2026-08-17 に、書かれていた `30.契約管理/…` が移行で存在しなくなっていたことが判明した。
