# contract-docusign-send セットアップ

このスキルを使うメンバーが最初に1回だけ整える項目。**必要なのは DocuSign の設定だけ**です。

> **2026-08-17 に方式を変えました。** 以前は AWS（aws-api-mcp）コネクタと S3 ステージングバケットが
> 必須でしたが、**どちらも不要になりました。** 契約書は自前コネクタが読んで base64 で DocuSign に
> 直接送るため、一時ファイルも一時公開URLも作りません。旧手順は `_旧版_S3方式_20260817/` にあります。

---

## 1. 拡張「AI OSI URI Finance」を入れる

契約書の送付ツール（`ds_*`）はこの拡張に入っています。台帳の読み書きと同じ拡張です。
入っていない場合は配布ポータルから `.mcpb` を取得して開いてください。

## 2. DocuSign 側で Integration Key を作る（管理者が1回）

DocuSign の **設定 → 統合 → アプリと鍵**（Apps and Keys）で行います。

1. **アプリを追加**して名前を付ける（例: `AI OSI URI Finance`）
2. **Integration Key** をコピーする（後で設定に貼る）
3. **RSA キーペアを生成**し、**秘密鍵を保存する**
   - 秘密鍵は生成直後にしか表示されません。**その場で保存してください**
4. **リダイレクトURI**に `https://www.docusign.com` を追加する
   - 同意を1回踏むためだけに使います。実際にそのページを開く必要はありません
5. 画面上部の **User ID（GUID）** を控える（送信者になるユーザーのID）

## 3. 拡張の設定に入れる

Claude Desktop の **設定 → 拡張機能 → AI OSI URI Finance**：

| 項目 | 入れるもの |
|---|---|
| DocuSign Integration Key | 手順2でコピーしたキー |
| DocuSign 送信者の User ID | 手順2で控えた GUID |
| DocuSign RSA 秘密鍵 | `-----BEGIN RSA PRIVATE KEY-----` から末尾までの**全文** |
| DocuSign アカウントID | 空でよい（複数アカウントに所属している場合だけ指定） |
| DocuSign 環境 | 空でよい（既定 production。開発用サンドボックスなら `demo`） |

**保存したら Claude Desktop を完全に終了して開き直します。**設定はプロセス起動時にしか読まれません。

## 4. 同意を1回だけ踏む

チャットで「DocuSign の疎通を確認して」と言うと `ds_status` が動きます。

- `need_consent: true` が返ったら、続けて「同意URLを出して」→ `ds_consent_url` が URL を返します
- **ブラウザで開いて「許可」を押すだけ**です。戻り先のページが開けなくても構いません
- もう一度「DocuSign の疎通を確認して」で `ok: true` になれば完了です

**この同意は失効しません。**（認可コード方式の refresh token と違い、使わない月があっても切れません）

## 5. 確認

`ds_status` が次を返せば準備完了です。

```
ok: true / env: production / account_id: ... / sender: ... / auth: JWT Grant
```

---

## 送れるファイルの制約

- **台帳フォルダの中のファイルだけ**送れます（外を指定すると拒否されます）
- 1ファイル **25MB** まで
- 拡張子は pdf / docx / doc / png / jpg / txt / html / rtf / xlsx

## トラブル

| 症状 | 原因と対処 |
|---|---|
| `DocuSign の設定が未入力です` | 手順3が未完了、または保存後に Claude を再起動していない |
| `consent_required` | 手順4の同意がまだ。`ds_consent_url` の URL を踏む |
| `RSA 秘密鍵で署名できませんでした` | 秘密鍵が PEM 全文になっていない（`-----BEGIN` から末尾まで、改行込み） |
| `redirect_uri` で弾かれる | 手順2-4のリダイレクトURIと、同意URLに渡す値が**完全一致**していない |
| `台帳フォルダの外のファイルは送れません` | 送付用ファイルを台帳フォルダ配下（`00.契約書/…`）に置く |
