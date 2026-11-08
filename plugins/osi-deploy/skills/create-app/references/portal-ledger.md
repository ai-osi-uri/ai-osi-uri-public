# ポータルの台帳に載せる（使っているもの・費用・管理者）

作ったアプリは、ツールポータルの「アプリ一覧」→ アプリ詳細で、お客さま自身が次を見られるようにする。
後から人が台帳に書く運用は続かないので、作り終えたこの時点で AI が入れる。

- 見るところ：公開 URL・ソースコード（GitHub）・管理画面の URL・管理者（誰が管理者か・どう入るか）
- いまの状態：作った人と日・最後に直した人と日・今月の費用
- 使っているもの：GitHub・Vercel・Supabase・Google Cloud（Cloud Run・鍵の保管・定期実行）・LINE・そのほかの SaaS
- 費用の内訳：出どころごとの金額（Google Cloud は請求の実額、AI などは使った量 × 単価）

## 1. 公開 URL・管理画面・管理者を書く

道具 `set_project_info` を呼ぶ（`project` は list_projects の slug）。

- `public_url`：公開 URL
- `admin_url`：管理画面がある場合、その URL
- `admin_note`：管理者は誰か・どう入るか（例：管理者は yamada@example.com。メールのリンクでログイン）

**パスワード・鍵の値は書かない。** 管理者のパスワードが要る作りなら、本人に直接渡し、台帳には「パスワードは〇〇さんが持っている」とだけ書く。

## 2. 使っているものを台帳に載せる

GitHub・Vercel・Supabase は公開の道具が自動で載せる。それ以外（Google Cloud の Cloud Run・Secret Manager・Scheduler、LINE 公式アカウント、外部の SaaS）は、
自動で載らないので、道具 `add_project_resource` で 1 つずつ載せる（`kind` を付ける）：
`gcp_cloud_run` / `gcp_secret` / `gcp_scheduler` / `gcp_project` / `line_channel` / `saas` / `other`（Cloud Storage のバケットなど）。

- Cloud Run：`external_id` はサービス名、`url` は公開 URL、`gcp_project`・`region`・`service_account`（実行サービスアカウント）を入れる。
  `cpu`・`memory_gib`・`min_instances` も入れる（請求データが届くまでの見込みに使う）。値は `gcp_api` でサービスを読んで写す（推測で書かない）
- Secret Manager：`external_id` は「<アプリ名>-*」のようにまとめて 1 行でよい
- 月額が決まっているもの（SaaS の月額など）は `monthly_jpy` に入れる
- 載せたら `list_projects` でそのアプリの resources に出ているかを確かめる

## 3. Google Cloud には印（ラベル）を付ける

Cloud Run などには `app=<アプリの名前>` のラベルを付ける（`gcloud run deploy ... --labels app=<名前>`）。
請求データの書き出しがこの印でアプリごとに分けるので、印が無いと「どのアプリにも結びついていない費用」になる。
Cloud Run のサービス名と台帳の external_id は同じ名前にする。

## 4. AI などを使ったら、使った量を知らせる

AI の鍵は会社で 1 本のまま、アプリごとに分けない（アプリごとに鍵を発行・登録させるのは使いにくい）。
代わりに、アプリが AI を呼ぶたびに、使った量をツールポータルの `/api/usage` に知らせる。

- 送るもの：`{ provider: "anthropic", model, input_tokens, output_tokens }`（AI の応答の usage をそのまま）。
  トークン以外で数えるもの（音声の文字数など）は `units` と `unit`、金額が分かれば `cost_usd`
- **待たずに送り、失敗は捨てる。** 知らせられなくてもアプリの動きは止めない
- 身元の示し方：
  - **Google Cloud（Cloud Run）で動くアプリ**：合言葉は要らない。メタデータサーバから自分のサービスアカウントの ID トークン
    （audience は `/api/usage` の URL）を取り、`Authorization: Bearer` で送る。ポータルはサービスアカウントからアプリを見分ける
    （台帳の gcp_cloud_run の meta.service_account、無ければ「サービス名@プロジェクト」のサービスアカウント）。
    Cloud Run の外（手元のテスト）では ID トークンが取れないので、何もしない作りにする
  - **それ以外（Vercel など）**：アプリごとの合言葉を発行し（sha256 だけを projects.usage_token_hash に置く）、
    値はそのアプリの環境変数 `USAGE_TOKEN` に入れる。合言葉の値を会話に出さない

## DoD

- アプリ詳細の「見るところ」に、公開 URL・ソースコード・（あれば）管理画面・管理者が出ている
- 「使っているもの」に、アプリが使うものが全部出ている
- AI を使うアプリは、動かしてから 1 回 AI を呼び、翌日以降の「費用の内訳」に AI の行が出ることを確かめる（集計は毎朝）
