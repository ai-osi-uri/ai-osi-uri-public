---
name: setup-deploy-environment
description: AI OSI URI の Cowork から LP・販売サイト・課金つきアプリを自動デプロイするための初回セットアップ。**共有ドライブの .env は使わず**、各ユーザーが「AI OSI URI Deploy」拡張（mcpb）をインストールし、設定欄にトークンを入力する方式に統一。GitHub PAT / Vercel Token / Stripe(test/live) / Supabase PAT / Anthropic API Key を拡張に入力し、OS キーチェーンに保存する。「デプロイ環境を整える」「初回セットアップ」「自動デプロイを使えるようにしたい」などで発動。トークンはチャットに貼らず拡張設定に入力する。毎回のデプロイ作業は `create-app`（旧 deploy-app） の役割。
version: 0.3.2
---

# デプロイ環境構築（拡張インストール方式）

自動デプロイ系スキル（`create-app`（旧 deploy-app） など）が使う認証情報を、**Google Drive の共有 `.env`
ではなく「AI OSI URI Deploy」拡張（mcpb）に入力**する。トークンは `sensitive` 指定で OS の
キーチェーンに暗号化保存され、拡張内の MCP サーバープロセスにのみ渡る。**1 ユーザー 1 回**。

> 旧版は `.deploy-credentials/.env` にトークンを書き込んでいたが、平文・共有ドライブ同期・
> チャット履歴残存の問題があったため拡張方式に移行した。`.env` はもう読まない。

## Step 1: 拡張のインストール

1. GitHub Releases（`mcpb-v*`）から `ai-osi-uri-deploy-mcp.mcpb` をダウンロード
   （社内手順：共有ドライブ「環境構築キット」参照）
2. Claude デスクトップで `.mcpb` を開く → インストール

## Step 2: トークンの発行と入力

拡張の設定欄に以下を入力（必要なものだけでよい）。発行先：

| 欄 | 必須 | 発行先 |
| --- | --- | --- |
| GitHub Personal Access Token | ✅ | https://github.com/settings/tokens （`repo`+`workflow`、classic、`ghp_`） |
| GitHub ユーザー名 | ✅ | 自分の GitHub username |
| Vercel API Token | ✅ | https://vercel.com/account/tokens （`vcp_`） |
| Stripe Secret Key（テスト） | 任意 | https://dashboard.stripe.com/test/apikeys （`sk_test_`） |
| Stripe Secret Key（本番/Live） | 任意 | https://dashboard.stripe.com/apikeys （`sk_live_`、実課金） |
| Supabase PAT | 任意 | https://supabase.com/dashboard/account/tokens （`sbp_`） |
| Anthropic API Key | 任意 | https://console.anthropic.com/settings/keys （`sk-ant-`、デプロイ時に env 自動注入） |
| App Store Connect API Key ID | iOS のみ | https://appstoreconnect.apple.com/access/integrations/api → Team Keys（10文字英数） |
| App Store Connect Issuer ID | iOS のみ | 同上ページ最上部の UUID |
| App Store Connect API Key (.p8) を base64 化した文字列 | iOS のみ | 発行した `.p8` を `base64 -i AuthKey_XXXXXXXXXX.p8 \| pbcopy` |
| iOS Distribution Cert (.p12) を base64 化 | iOS のみ | Keychain から書き出した `.p12` を base64（`ios-mobile-release` の references 参照） |
| iOS Distribution Cert .p12 のパスワード | iOS のみ | 書き出し時に付けたパスワード |

> 作成先は create-app（旧 deploy-app）のプリフライト（GitHub org / Vercel team / Supabase org の3点可否＝USE_ORG）で
> 決まる。3点揃えば org（`ai-osi-uri` / `ai-osi-uri` / `zsarvxuigtcmrmoewarw`）、1つでも欠ければ全部
> 個人に倒す（混在させない）。org に寄せるには PAT を Classic PAT(repo+workflow+read:org)、Vercel の
> ai-osi-uri スコープ、Supabase の会社 org を揃える。

> **トークンの所有者について（重要）**: ここで入力する Vercel / GitHub Token は AI OSI URI の
> もの。`health_check` や Vercel/GitHub の画面で個人ユーザー名（例: `yuhenagisa-aiosiuri`）や
> `org: "(個人アカウント)"` と表示されても、それは表示上の仕様であり**問題ない**。個人スコープ
> と判断して再発行・差し替えを促さない（`valid: true` ならそのまま使う）。

## Step 3: 検証

> **重要（初回の詰まり防止）**：拡張をインストール／更新したら、**Claude を完全終了して
> 再起動**してから `health_check` を呼ぶ。拡張は再起動しないと有効化されず、`health_check` が
> ツール未検出／false を返して詰まる。ウィンドウの×で閉じるだけでは再起動にならない
> （画面左上の Claude → Claude を終了 → もう一度起動）。

拡張を有効化後、`health_check` ツールを呼ぶと各トークンの有効性をまとめて確認できる
（値は末尾4文字のみのマスク表示）。`github.valid` / `vercel.valid` などが true なら準備完了。

> **iOS の追加検証**: iOS のリリース系（`ios-mobile-release` / Xcode Cloud / TestFlight）を
> 使うなら、`mobile_health_check`（AI OSI URI Deploy 拡張 v1.15+）を追加で呼ぶ。ASC の
> Key ID / Issuer / .p8 が揃っているか、JWT が生成できるか、`GET /v1/apps` が 200 を返すかを
> 一括で確認する。`.p8` が改行込みで欠けていたり、Issuer と Key ID が入れ替わっていると
> ここで即落ちる（fastlane まで進めて 8 分待って気付く事故を防ぐ）。Distribution Cert
> (`.p12`) も同時に基本検証する。詳細は `ios-mobile-release/references/n1-policy.md`。

> **DB を使うアプリは Supabase PAT が必須**：`supabase.valid:true` でないと create-app（旧 deploy-app）の
> Supabase 自動プロビジョニング（プロジェクト作成→キー取得）が動かず、「Supabase プロジェクト
> 設定できない」で止まる。DB／ログイン／保存が要るアプリを作る予定なら Supabase PAT を入れる。

## 完了後

`create-app`（旧 deploy-app） が使える。「LP を公開して」「Stripe つきでデプロイ」「SaaS を立ち上げて」など。

## よくある罠：GitHub PAT が突然 401 を返す

セッション中に何度か再発行が必要になるケース：

- **GitHub secret scanning による自動 Revoke**
  PAT を `https://x-access-token:<PAT>@github.com/...` の URL embedding で扱うと、
  curl のコマンド履歴や標準出力に PAT が紛れ込み、GitHub が自動検出して即 Revoke
  することがある。**401 突然発生時は最初にトークン一覧画面で生死を確認**：
  https://github.com/settings/tokens

- **Fine-grained PAT は Organization 配下で権限不足になりやすい**
  「You need admin access to the organization before adding a repository to it.」
  が出たら、選択肢は 2 つ：
  1. Org オーナーに当該 PAT を承認してもらう
  2. **Classic PAT に切り替え**（推奨）：`repo` + `workflow` + `admin:org` の `read:org`
     を付ければ Org にもリポを作れる

- **新 PAT 反映フロー（拡張方式）**
  1. https://github.com/settings/tokens/new で Classic PAT 発行（`ghp_` で始まる）
  2. Claude デスクトップの拡張設定欄で **GitHub PAT を新しい値に上書き**
     （拡張内で OS キーチェーンに再保存される）
  3. `health_check` を実行して `github.valid: true` を確認
  4. 旧 PAT を https://github.com/settings/tokens で Revoke

- **再発行頻度を下げるコツ**
  - 拡張内の MCP ツールは PAT を URL embed せず Authorization ヘッダで使うので、
    通常運用ではこの罠を踏まない
  - 手動 curl 等で動作確認するときは `Authorization: token $PAT` ヘッダ方式で

---

## 注意事項

- トークンはチャット欄に貼らず、**拡張の設定欄に直接入力**する（キーチェーン保存）。
- Stripe はサンドボックス（test）と本番（live）で別キー。各 Stripe ツールは `mode:"test"`（既定）/`"live"`、live は `confirm_live:true` 必須。
- 不要になったトークンは各サービスで Revoke し、拡張設定からも削除する。
