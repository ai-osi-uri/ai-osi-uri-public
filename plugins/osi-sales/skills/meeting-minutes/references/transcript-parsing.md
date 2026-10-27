# 文字起こしの取得・取り込み（共通・正本）

meeting-minutes / session-review / shodan-prep で共通の「文字起こしをどう手に入れ、
どう読むか」の作法。ここが単一情報源（他スキルからはこのファイルを参照する）。

---

## 1. 取得チャネル（優先順）

会社に AI 秘書（置き場＝Supabase）があれば ① を先に見る。無ければ ② から。
どの経路でも、手に入るのは同じ「話者ラベル付きの全文」なので、以降（§2・§3）の読み方は共通。

### ① 会社の議事録DB（秘書の置き場。秘書がある会社ではプライマリ）

秘書の置き場には、会社に届いた議事録が **全員分** たまっている（Plaud の自動転送メール・
Gemini のメモ・議事録パートナーの文字起こし）。Plaud につながっていなくても、
自分以外のメンバーの録音でも、ここから取れる。

道具：会社のリモート MCP（URL でつなぐコネクタ）の `supabase_execute_sql`
（`project_ref` ＝ 秘書の置き場。`osi-profile.md` の `secretary.project_ref`。無ければ
`getting_started` が返す「会社の台帳（AI秘書）」の ref、または `secretary_status` で確かめる）。
**読むだけ（`select`）。`insert` / `update` / `delete` はしない。**

表：`public.minutes`。主な列：

| 列 | 中身 |
|---|---|
| `id` | 議事録の番号（本文を取るときに使う） |
| `kind` | `plaud`（Plaud の転送メール）/ `gemini`（Gemini のメモ）/ `partner`（議事録パートナー） |
| `owner` | 録った人（メンバーの呼び名） |
| `subject` | 件名（Plaud の録音名が入る。`[Plaud-AutoFlow] MM-DD ミーティング：…` の形） |
| `account` | 相手先（秘書が紐づけ済みなら入る。未紐づけは空） |
| `meeting_date` / `sent_at` | 会議の日付 / 届いた時刻（UTC） |
| `body` | 話者ラベル付きの全文（`[Speaker 1] …` の形。Plaud の文字起こしと同じもの） |
| `partner_todos` | 議事録パートナーが出した会議後の ToDo（参考情報） |

手順：
1. **候補を探す**（本文は取らず、件名と長さだけ見る）：
   ```sql
   select id, kind, owner, subject, account, meeting_date, sent_at, length(body) as body_len
   from public.minutes
   where meeting_date between '{YYYY-MM-DD}' and '{YYYY-MM-DD}'
     and (subject ilike '%{キーワード}%' or account ilike '%{キーワード}%' or owner = '{呼び名}')
   order by sent_at desc limit 20;
   ```
   「今日の」「昨日の」→ `meeting_date`、企業名・話題 → `subject` / `account`。相手の名前は
   件名に出ないことが多いので、当たらなければ日付だけで引いて候補を見せる。
2. 候補 1 件なら即決。複数なら件名・会議の時刻（`sent_at` を日本時間に直す）・録った人・長さを添えて
   `AskUserQuestion`。本文の冒頭 1,000 字（`left(body, 1000)`）を見れば、誰との会議かは大体分かる。
3. **本文を取る**：
   ```sql
   select subject, meeting_date, body, partner_todos from public.minutes where id = '{id}';
   ```
   長時間の録音は本文が 10 万字を超えることがある。要約せず全文を読む（必要なら
   `substr(body, 1, 50000)` と `substr(body, 50001, 50000)` のように分けて取る）。
4. `partner_todos`・Plaud の要約部分は **参考情報に留める**（構造化は必ず全文から）。
5. **届くまでの時間差**：録音が終わってから届くまで数分かかる。候補に無ければ ② Plaud MCP を見る
   （Plaud 側にはすぐある）。両方に無ければ ③ 以降へ。

やらないこと：
- `public.minutes_private`（「載せない」と指定された議事録）は読まない。
- 本文を台帳や他の場所に写さない（議事録の正本の置き方は各スキル本体に従う）。

### ② Plaud MCP（秘書が無い会社ではプライマリ）

Plaud MCP コネクタが接続されていれば、ユーザーに貼り付けさせずに直接取得する。
ツール（名前に `plaud` を含む）：

| ツール | 用途 |
|---|---|
| `list_files` | 録音の検索。`query`（録音名キーワード・大文字小文字不問）、`date_from` / `date_to`（YYYY-MM-DD）、`page` / `page_size` |
| `get_file` | 単一録音の詳細。`source_list`（話者・タイムスタンプ付きセグメント）、`note_list`（AI ノート）、`presigned_url`（音声、24h 有効） |
| `get_transcript` | 全文文字起こし（タイムスタンプ・話者ラベル付き）— 構造化の主入力 |
| `get_note` | Plaud の AI 要約・アクションアイテム — **参考情報に留める**（構造化は必ず全文から） |
| `login` / `logout` | OAuth サインイン / サインアウト |

手順：
1. ユーザーの発話から検索条件を組み立てる（「今日の」「昨日の」→ 日付、企業名 → `query`）。
2. `list_files` → 候補 1 件なら即決、複数なら録音名・開始時刻・長さを添えて `AskUserQuestion`。
3. `get_transcript` で全文取得。長時間録音はセグメントが多いので、要約せず全文を読む。
4. 401 / Not authenticated → `login` で再サインインを促して再試行。

### ③ チャット貼り付け（フォールバック）

従来の Plaud アプリからのコピペ。テキストがそのまま会話に貼られていれば最優先でそれを使う
（ユーザーが明示的に渡したものが最も意図に近い）。

### ④ Gmail 転送メール（フォールバック）

Plaud → Gmail の自動転送を設定している運用向け。Gmail 検索（`search_threads`）で
`from:plaud`＋録音名・日付などを検索し、本文の文字起こしを取得する。
複数ヒット時は件名と日時で確認。

### ⑤ Drive ファイル（フォールバック）

ユーザーがファイル名を指定した場合、Drive の `read_file_content` で取得。

### どれも無い場合

`AskUserQuestion` で「Plaud の文字起こしを貼り付けてください（または録音名・日付を
教えてください）」と促す。

---

## 2. 文字起こしの特徴と対処（Plaud 由来・議事録DB由来とも共通）

- **句読点が少ない** — 文単位ではなく意味の塊で読む。
- **発言者ラベルが曖昧**（Speaker 1/2 等） — meta.attendees・自己紹介・呼びかけ・文脈から
  人名を推定する。MCP の `get_transcript` や議事録DBの `body` は話者ラベル付きなので貼り付けより
  精度が高いが、ラベル＝人名ではない点は同じ。確定できない場合は「話者A（推定：○○様）」と注記。
- **数字・固有名詞は怪しい** — 誤認識が多い。原文に忠実に引用し、怪しければ「(原文ママ)」と
  注記。**数字は勝手に変えない**。
- **長い独白は 1 行に圧縮** — 逐語ではなく要旨で。ただし「重要発言」引用は原文のまま。
- **雑談・アイスブレイクは捨てる** — 構造化対象は本題のみ。

---

## 3. 話者推定の手がかり（優先順）

1. 話者ラベル＋冒頭の自己紹介・名乗り
2. 「○○さん、どう思いますか」等の呼びかけ
3. 発言内容の立場（自社サービスの説明をしている＝自社側、社内事情を話している＝先方）
4. meta.attendees（ユーザーから与えられた参加者リスト）

推定に自信が持てない発言は、話者を断定せずに引用する。
