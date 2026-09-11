---
name: lovable-payments-golive
description: |
  **Lovable** で作られたアプリの内蔵決済（seamless Payments / Stripe）を、有効化から
  Go Live（本番稼働）まで進めるスキル。「Lovableの決済を有効化して」「Lovableで本番化して」
  「Lovable Paymentsを有効にして」「LovableでStripeを使いたい」「Lovableのアプリで課金
  できるようにして」「Lovableの支払いを本番にして」などで発動する。**AI OSI URI Deploy
  拡張は使わない**（Vercel/AWS + Deploy拡張前提の Stripe 本番化は `switch-to-live-mode`
  の担当）。対象が **Lovable で作られたプロジェクトかどうか**で使い分けること。
  アカウント作成・パスワード入力・Stripe/Lovable の各種「有効化」「承認」「Go live」
  ボタンのクリックなど、アカウント本人性に関わる操作は必ずユーザー自身が行う（本スキルは
  実装・確認・案内のみを担当する）。
version: 0.1.0
requires_connectors:
  - server: Lovable
    provision: user-install
  - server: claude-in-chrome
    provision: user-install
---

# Lovable 内蔵決済 有効化〜Go Live スキル（lovable-payments-golive）

Lovable の「seamless Payments」（Lovable 内蔵の Stripe 連携）を、テスト環境での実装から
本番（Live）稼働まで一気通貫で進める。**Lovable Cloud を使っている Lovable プロジェクト
専用**。GitHub/Vercel/AWS + AI OSI URI Deploy 拡張の Stripe 本番化（BYOK）は別スキル
`switch-to-live-mode` が担当するので、対象が Lovable かどうかを最初に確認すること。

---

## 重大な前置き（必ずユーザーに伝える）

1. **アカウント本人性に関わる操作は代行しない。** Stripe/Lovable のアカウント作成、
   メール/パスワード入力、「Enable」「Claim」「Install」「Go live」ボタンのクリックは
   すべてユーザー自身が行う。本スキルはコード実装（チェックアウト UI・法的ページ）と、
   進行状況の確認・案内に専念する。
2. **Lovable Payments の有効化ダイアログは Lovable の実 UI でしか開けない。** API 経由の
   `send_message`（ヘッドレスチャット）では「Enable payments」インタラクティブダイアログが
   描画されず、有効化ツール自体が利用できないままになる。ユーザーに実際のブラウザで
   Lovable プロジェクトを開いてもらい、Lovable のチャット欄で決済導入を依頼し、出てきた
   ダイアログ（Email / Business name / Country）を埋めて「Enable」を押してもらう必要がある。
   これが済むと、以降は API 経由のツール呼び出しが使えるようになる。
3. **前提条件**：Lovable Pro プラン以上、かつ Lovable Cloud（内蔵 Supabase 相当）が有効な
   こと。外部の自前 Supabase プロジェクトに接続している場合、seamless Payments は使えない。

---

## 前提条件チェック（着手前に必ず確認）

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| 対象が Lovable プロジェクトである | ユーザーに確認、または Lovable の project URL の有無 | 違う場合は `switch-to-live-mode` へ |
| Claude in Chrome が接続されている | `mcp__claude-in-chrome__tabs_context_mcp` 等が呼べるか | 未接続ならユーザーに拡張のインストール・接続を案内 |
| Lovable MCP（project 操作）が接続されている | `list_projects` / `get_project` が通るか | 未接続なら Cowork の Lovable コネクタ接続を案内。見つからない場合は `mcp-registry` でコネクタを検索し提案する |
| Lovable Pro プラン | ユーザーに確認（Settings → Plan） | Pro 未満なら Lovable 側でアップグレードを案内 |
| Lovable Cloud 有効 / 外部 Supabase 非接続 | プロジェクト設定を確認 | 外部 Supabase 接続中なら seamless Payments 不可を伝える |

いずれかが欠けている場合、**その場で該当の接続・アップグレードをユーザーに促し**、揃った
時点で続行する（最初に全部揃っていなくても、必要になった段階でその都度案内すればよい）。

---

## ワークフロー全体像

```
Step 0: 対象確認（Lovable かどうか／switch-to-live-mode との切り分け）
Step 1: 決済プランの実装方針を決める（商品・価格・課金形態）
Step 2: Lovable UI で「Enable payments」を有効化してもらう（ユーザー作業）
Step 3: 商品・価格を作成（payments--batch_create_product、HITL 承認あり）
Step 4: チェックアウト UI をコードで実装（テスト環境で検証）
Step 5: 法的ページを実装（Privacy Policy / Terms of Service / Refund Policy）
Step 6: Stripe アカウントの Claim（既存アカウントへのリンク、ユーザー作業）
Step 7: Lovable Payments アプリを本番 Stripe アカウントにインストール（ユーザー作業・OAuth同意）
Step 8: Go live（ユーザー作業）
Step 9: 公開 URL での動作確認（プレビューではなく published サイトで確認）
Step 10: Stripe ダッシュボードでの取引確認・配送先住所の確認方法を案内
```

---

## Step 0: 対象確認

ユーザーの依頼が「決済を実装／本番化したい」という内容だった場合、まず対象アプリが
**Lovable で作られているか**を確認する。

- Lovable プロジェクト（lovable.dev の URL、または Lovable MCP の `list_projects` に
  該当プロジェクトがある）→ 本スキルを使う
- create-app で作った Vercel/AWS アプリ → `switch-to-live-mode` を使う（本スキルは使わない）
- どちらか不明 → ユーザーに一言確認する

---

## Step 1: 決済プランの実装方針を決める

支援金・購入代金など、金額区分（例：1,000円/3,000円/5,000円の支援プラン、2,500円/冊+
送料500円の物販など）と課金形態（都度課金のみ。サブスクは別途要検討）をユーザーと確定する。

---

## Step 2: Lovable UI で「Enable payments」を有効化してもらう

案内メッセージ例：

```
Lovableのプロジェクトをブラウザで開いて、Lovableのチャット欄で
「決済を導入したい」（例：「Stripeで支援金を受け取れるようにしたい」）と入力してください。
「Enable payments」のダイアログが出てきたら、Email / Business name / Country を確認し、
「Enable」を押してください。完了したら教えてください。
```

完了後、`payments--enable_stripe_payments` などの決済系ツールが呼べるようになっているかを
確認する。まだ呼べない場合は、ダイアログでの操作が完了していない可能性が高い。

---

## Step 3: 商品・価格を作成

`payments--batch_create_product` で商品・価格を作成する。**HITL（human-in-the-loop）承認が
必須**で、呼び出すと `queue_paused: true, queue_pause_reason: "hitl_tool"` の状態でキューが
止まる。

```
商品作成の承認待ちです。Lovableのチャット画面で保留中のアクションを確認・承認してください。
承認いただいたら自動的に処理が再開されます。
```

`send_message` は 180〜300 秒でタイムアウトすることが多いが、処理はサーバー側で継続する。
`wait:false` で送って `message_id` を受け取り、`get_message` を数秒間隔でポーリングして
`status: completed` になるまで待つのが安全。

---

## Step 4: チェックアウト UI の実装

Lovable の built-in Payments が生成する `StripeEmbeddedCheckout` 等のコンポーネントを使い、
金額・数量・注文内容に応じたチェックアウトを実装する。テスト環境（プレビュー）で
テストカード（4242 4242 4242 4242）を使い、金額・内訳（商品代＋送料等）が正しいかを確認する。

> ⚠️ Lovable のプレビュー画面は **仕様として常に「test mode」バナーが表示される**
> （バグではない）。実際の Live 決済が機能しているかどうかは、後述の Step 9 で
> **公開済み URL** を見て確認すること。プレビューで test mode と出ていても慌てない。

---

## Step 5: 法的ページの実装

Go live 前の readiness check で要求されるため、**先回りして実装しておく**。最低限：

- **Privacy Policy**：Stripe Checkout 経由で取得する情報（氏名・メール・支払情報。カード情報
  自体は自社サーバを経由しない）、利用目的、第三者提供（Stripe, Inc.）、問い合わせ先
- **Terms of Service**：運営者情報、サービス内容（支援金は対価のない任意の性質か、物販かで
  内容が変わる）、免責事項、準拠法
- **Refund Policy**：原則返金なしか、返金条件（二重課金・明確なシステムエラー等）、問い合わせ先

フッター等から常時リンクできるようにする。

---

## Step 6: Stripe アカウントの Claim（ユーザー作業）

Lovable のプロジェクト → その他（More）→ 決済（Payments）タブ → 「サンドボックスを請求
（Claim your Stripe account）」から、**既に本人確認・口座登録が完了している既存の Stripe
アカウント**にリンクしてもらう。同じ会社の別サイトで既に Stripe アカウントを作成済みなら、
そのアカウントに寄せることで KYC・銀行口座登録の重複を避けられる。

```
Lovableの「決済」タブから「サンドボックスを請求」を選び、既存のStripeアカウント
（<アカウント名/ID>）にログインしてリンクしてください。新規アカウントは作らないでください。
```

---

## Step 7: Lovable Payments アプリのインストール（ユーザー作業）

本番 Stripe アカウント側で、「Lovable Payments」アプリのインストール（OAuth 同意）を
行ってもらう。スコープは Account/User info（read-only）、API Keys（read + write）、
Events（read-only）。

---

## Step 8: Go live（ユーザー作業）

Lovable の決済タブで readiness check（法的ページの存在・サイト内容の実在性）が通れば
「Go live」ボタンが押せる。押すのはユーザー自身。

---

## Step 9: 公開 URL での動作確認

**Live モードでの決済確認は、プレビューではなく published サイトで行う。**

1. 公開 URL（`https://<project>.lovable.app` 等）を開く
2. 実際のカードで少額決済を 1 回試してもらう（実課金が発生することを事前に伝える）
3. 決済完了後の遷移・サンクスページ表示を確認

---

## Step 10: Stripe ダッシュボードでの確認方法の案内

取引確認は必ず**明示的にアカウント ID を含む URL**で開くよう案内する。ログイン中の
Stripe アカウントが複数ある場合、`https://dashboard.stripe.com/payments` のような
汎用 URL だと別アカウントに飛ぶことがある。

```
https://dashboard.stripe.com/<acct_ID>/payments
```

該当取引をクリックすると開く明細画面で確認できる項目：

| 確認したい情報 | 表示場所 |
| --- | --- |
| 決済ステータス・金額 | 画面上部（成功/失敗、金額） |
| 顧客のメール・電話番号 | 「Checkout サマリー」内「顧客」欄 |
| 配送先住所（配送ありの商品の場合） | 「Checkout サマリー」内「配送情報の詳細」欄 |
| 明細内訳（商品代・送料等） | 画面下部の明細表 |

注文が入るたびにこの画面で発送先などを確認できる旨をユーザーに伝える。

---

## エラー時の挙動

| 失敗箇所 | 対応 |
| --- | --- |
| Step 2 で決済系ツールが呼べないまま | 「Enable payments」ダイアログの操作が未完了の可能性。ユーザーに実 UI での操作を再確認 |
| Step 3 で HITL 承認待ちのまま進まない | Lovable チャット画面での承認待ちであることを案内し、承認後に `get_message` でポーリング再開 |
| Step 5 が未実装のまま Step 8 の readiness check に進んだ | Go live がブロックされる。Step 5 に戻って法的ページを先に用意する |
| Step 6 で新規 Stripe アカウントを作ってしまった | 既存アカウントとの二重管理になる。可能なら既存アカウントへの付け替えを検討し、ユーザーと相談 |
| Step 9 でプレビューを見て「test modeのままだ」と誤解される | プレビューは常に test mode 表示（仕様）。公開 URL で確認するよう案内 |
| Step 10 で別アカウントの取引一覧が表示される | URL に `acct_ID` を明示していないことが原因。正しい ID 付き URL に案内し直す |

---

## 注意事項

- 本スキルは **AI OSI URI Deploy 拡張を一切使わない**。Stripe キーの入力・管理は
  すべて Lovable 側（seamless Payments）が担う
- アカウント作成・ログイン情報の入力・各種「有効化」「承認」ボタンのクリックは
  **必ずユーザー本人が行う**（本スキルは絶対に代行しない）
- 支援金・寄付など対価のない支払いの場合、用途を明記するかどうかは事業判断。
  スキル側で勝手に用途を書かない（ユーザーに確認する）
- 既に活動済みの Stripe アカウントがある場合、Step 6 で同じアカウントにリンクすることで
  KYC・銀行口座登録の重複を避けられる。新規サイトを作るたびに新規 Stripe アカウントを
  作らないよう案内する
