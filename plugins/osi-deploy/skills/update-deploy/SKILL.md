---
name: update-deploy
description: |
  既にデプロイされている AI OSI URI のアプリ（Vercel / AWS）に対して、ソースを
  最新化して局所修正→push→自動再デプロイ→smoke test まで行う atomic スキル。
  「○○アプリを直して」「○○のバグ修正して再デプロイ」「○○のmax_tokens上げて」
  「アウトプット切れてるから直して」「公開済みアプリのコードをいじって」
  「もう動いてるVercelアプリにパッチ当てて」「ai-catalog-navigator を直して」
  「会員サイトの〜を直して」など、**新規作成ではなく既存リポを更新する**全リクエストで発動する。
  リポURLまたはVercelプロジェクト名から GitHub リポを特定し、ローカルの clone を
  確認（無ければユーザーに clone コマンドを案内、または gh CLI を計画的に使う）、
  該当ファイルを修正し、AI OSI URI Deploy 拡張の `github_push` で push、
  Vercel の自動再デプロイを `vercel_get_deployment_status` で監視、
  最後に `app-smoke-test` を呼んで「実際に直ったか」までを 1 つのフローで完結させる。
  新規アプリ作成（既存リポなし・新規リポを作る）は `deploy-app` の役割。
  本スキルは「ローカルから既存リモートを更新する」場合専用。
version: 0.4.0
---

# update-deploy — 既存アプリを更新するオーケストレータ

`deploy-app` が「新規作成」を担うのに対し、本スキルは「既にある GitHub リポ＋
Vercel/AWS のデプロイを、ローカル修正→push→自動再デプロイ→検証」まで貫通する。

## いつ発動するか

- 「○○アプリを直して」「○○のバグ修正」
- 「ai-catalog-navigator のアウトプット切れてる」「max_tokens 上げて」
- 「○○のコピー直して再デプロイ」「文言修正して反映」
- Vercel/AWS にすでに公開済みのリポを編集したい全シナリオ

新規 LP/SaaS を 0 から作る依頼（リポ未作成）は `deploy-app` を使うこと。

## ハーネス（必須）

`{OUTPUTS}/update-progress.md` を作成し、各フェーズの結果を evidence 付きで貼る。
DoD: smoke test の合格 evidence なしに「直りました」と報告しない。

---

## Phase 0: 認証情報・接続状況の確認

1. `health_check` を呼び `github.valid: true`、Vercel パスなら `vercel.valid: true`、
   AI 機能修正なら `anthropic.valid: true` を確認。
2. 不足していれば `setup-deploy-environment` を案内して中断。
3. AWS パスの修正なら `AWS_PROFILE` または `mcp__awslabs_aws-api-mcp-server__call_aws`
   が利用可能かを確認。

---

## Phase 1: 対象リポ特定

入力（自由文）から以下を確定する。読み取れない要素のみ AskUserQuestion で 1 問だけ聞く。

| 項目 | 抽出例 | 推測ヒント |
|---|---|---|
| `repo_owner` | `ai-osi-uri` または個人 username | 既定は GITHUB_ORG / GITHUB_USERNAME |
| `repo_name` | `ai-catalog-navigator` | Vercel プロジェクト名と一致することが多い |
| `repo_url` | `https://github.com/{owner}/{name}` | owner+name から組み立て |
| `branch` | 既定 `main` | 「develop の修正」など明示時のみ変える |
| `host` | `vercel` / `aws` | `list_projects`（Vercel MCP）の存在で判定 |
| `vercel_project_id` | `prj_xxx`（host=vercel 時） | `get_project` で `latestDeployment.id` も取得 |

Vercel パスの追加情報取得（**ユーザーに聞かず先に MCP で引く**）：

```
mcp__9f2dbe40-...__list_teams                     # team_xxx を取得
mcp__9f2dbe40-...__get_project                     # latestDeployment.id, framework, domains
mcp__9f2dbe40-...__get_deployment                  # meta.githubCommitSha, githubRepo, branchAlias
```

得られた `meta.githubCommitSha` は Phase 5 の「コミット一致検証」で使う。

---

## Phase 2: ローカル clone の確保（clone-or-pull の二分岐）

**原則**: 「無ければ clone、あれば pull」を**毎回必ず**実行する。古い clone のままで
作業を始めると、他者の最新 commit を巻き戻してしまったり、push 時にコンフリクトを
量産する。スキルを横展開すると毎回同じトラブルが再発するので、ここはケチらない。

### 最重要原則：認証が要る git/API は MCP 経由のみ

Cowork の bash サンドボックスは **GitHub への認証情報を持たない**。したがって：

- **やってはいけない**: サンドボックスから `git fetch / git pull / git clone` を
  プライベートリポに対して直接実行する（必ず
  `could not read Username for 'https://github.com'` で落ちる）。
- **やってはいけない**: `curl https://api.github.com/repos/.../pulls` のような
  認証必須エンドポイントを叩く（404 や 401 で空振りする）。
- **正しい道**:
  - **push** → `mcp__AI_OSI_URI_Deploy__github_push`（拡張保持の PAT で必ず通る）
  - **fetch/pull/PR一覧/PR作成/コンフリクト確認** → ユーザーのターミナルで
    `gh` を実行してもらい、出力を貼ってもらう（または `gh` の MCP ラッパーがあれば
    そちらを優先）
  - **コードのreadやedit** → `Read` / `Edit` ツール経由（ユーザーのMac上のclone を
    そのまま操作可能。サンドボックスを介さない）

「とりあえず curl してみる」「とりあえず git fetch してみる」は時間の無駄。
最初から MCP かユーザーのターミナルに振り分けること。

### Step 2-1: 既存の clone を探す

> **正本は GitHub リモート。ローカル clone は“そのマシンの作業コピー”**（壊れても再 clone で復旧）。
> 既定の配置は **`~/projects/{repo_name}`**（環境変数 `OSI_PROJECTS_DIR` で上書き可）。

順番に確認：

1. `~/projects/{repo_name}`（**既定。最優先**。`OSI_PROJECTS_DIR` があればそちら）
2. `~/Desktop/{repo_name}` / `~/Desktop/work/{repo_name}`（旧来の置き場の後方互換）
3. それでも無ければユーザーに「ローカル clone はどこですか？」と AskUserQuestion で 1 問

**ガード（他環境でも事故らないため）**:
- Cowork では対象パスが**接続（マウント）済み＆書込可能**かを確認。未接続なら `mcp__cowork__request_cowork_directory` で接続を促すか、接続済みフォルダを選ばせる。
- `~/projects` が無ければ作成してよい（`mkdir -p`）。同名で別アプリの clone が在る場合は remote 一致で必ず判別する。

clone を見つけたら `git -C <dir> remote -v` で remote URL を確認し、対象 repo と一致することを検証。
**remote が空（`github_push` 後の PAT入り remote 削除で `origin` が消えていることがある）** の
場合は、Step 2-2.5 で再追加する。一致しなければ「別アプリの可能性」を示してユーザー確認。

### Step 2-2: clone を取得（無かった場合）

**サンドボックスからは clone しない**（プライベートリポは絶対通らない）。ユーザーの
ターミナルで `gh repo clone` を実行してもらう。コマンドは
`mcp__computer-use__write_clipboard` でクリップボードに置き、ユーザーに paste & Enter
を促す。完了したら `mcp__cowork__request_cowork_directory` でフォルダをマウントして
Read/Edit から触れるようにする。

```
mkdir -p ~/projects && cd ~/projects && gh repo clone {repo_owner}/{repo_name}
```
（既定は `~/projects`。チームで別の置き場に揃える場合のみ `OSI_PROJECTS_DIR` を使う）

> サンドボックスの bash から `git clone https://...` を試すのは無意味（必ず認証で
> 落ちる）。試さない。

#### 将来の理想形（mcpb 改修案）

`AI OSI URI Deploy` 拡張に `github_clone_repo` ツールを追加すれば本ステップは MCP 一発で完結する。
追加仕様は `references/mcpb-clone-tool-spec.md` を参照。

### Step 2-2.5: remote が消えていたら再追加

`mcp__AI_OSI_URI_Deploy__github_push` は push 後に PAT 入り remote を削除する仕様。
そのため次回 fetch しようとすると `'origin' does not appear to be a git repository`
で落ちる。**毎回 remote 状態を確認し、空なら再追加する**：

```
test -n "$(git -C <dir> remote)" \
  || git -C <dir> remote add origin https://github.com/{repo_owner}/{repo_name}.git
```

これは認証 URL（PAT 入り）ではなくプレーンな HTTPS。`fetch` / `pull` は macOS の
osxkeychain credential helper（事前に `gh auth setup-git` 済み）が補完してくれる。

### Step 2-3: 最新化（既存 clone があった場合）

サンドボックスから fetch/pull は通らないので、ユーザーのターミナルで実行してもらう
（コマンドを `write_clipboard` で投入）。完了したらサンドボックスから
`git log --oneline -3` でローカルの先頭 commit を確認するだけにする。

```
cd <dir> && git fetch origin && git checkout {branch} && git pull --ff-only
```

ブランチがずれていたり未コミット変更がある場合は停止してユーザー確認（黙って `--force` しない）。
**`pull --ff-only` で失敗した場合**は他者の commit と衝突している可能性が高い。
`git status` と `git log --oneline origin/{branch}..HEAD` で何が手元にあるかを示し、
ユーザーに `merge` / `rebase` / 諦めて re-clone のどれにするか確認する。

---

## Phase 3: 修正対象の特定と編集

### Step 3-1: 不具合タイプの推定

ユーザーの自由文から修正タイプを判別：

| タイプ | 典型シグナル | 探索ヒント |
|---|---|---|
| AI 出力切れ | 「途中で切れる」「アウトプット途切れた」 | `max_tokens` / `max_output_tokens` / `messages.create` |
| AI レスポンス遅延 | 「30秒で落ちる」「504」「タイムアウト」 | `maxDuration` / Edge runtime / streaming |
| 文言修正 | 「コピー直して」「タイトル変更」 | grep で該当テキスト検索 |
| 価格修正 | 「金額を3万円に」 | `price`/`amount`/`STRIPE_PRICE_ID` |
| 環境変数 | 「API KEY 切替」 | `.env.local` ではなく Vercel env を直接更新 |
| バグ修正 | 「○○で500」「クラッシュ」 | `get_runtime_logs` でログ→該当ファイル特定 |

### Step 3-2: 該当箇所を Grep / Read で特定

```
Grep "max_tokens|maxTokens|max_output_tokens" app/api/**
```

該当が複数あれば、各箇所をユーザーに提示して「どれを直すか」確認（重要：勝手に全部書き換えない）。

### Step 3-3: 修正適用

Edit ツールで局所修正。原則：

- 1 ファイル 1 関数の最小変更にとどめる
- AI 系の修正なら同時に `maxDuration` も見直す（Vercel default 10s → 60s）
- 変更が複数ファイルにまたがるなら `update-progress.md` に diff サマリを書き出す

### Step 3-4: ローカル sanity check（任意）

```
cd <dir> && npm run lint --silent 2>/dev/null || true
cd <dir> && npx tsc --noEmit 2>/dev/null || true
```

エラーが出ても続行可能。push 後の Vercel ビルドで最終確認する（自動修正ループ込み）。

---

## Phase 4: push → 自動再デプロイ

### Step 4-0: pre-push hygiene（必須・サンドボックス由来の詰まり予防）

Cowork サンドボックスから `git` を実行すると、ホスト側に
`.git/index.lock` / `.git/HEAD.lock` / `.git/ORIG_HEAD.lock` /
`.git/objects/maintenance.lock` が残ることがある。これらが残った状態で
`github_push` を呼ぶと `fatal: Unable to create '.../index.lock': File exists.`
で必ず失敗するため、**push の直前に必ず以下を実行する**。

```
# サンドボックスでは rm が「Operation not permitted」になることがあるので mv で退避
cd <work_dir> \
  && mv -f .git/index.lock .git/index.lock.old 2>/dev/null \
  ; mv -f .git/HEAD.lock .git/HEAD.lock.old 2>/dev/null \
  ; mv -f .git/ORIG_HEAD.lock .git/ORIG_HEAD.lock.old 2>/dev/null \
  ; mv -f .git/objects/maintenance.lock .git/objects/maintenance.lock.old 2>/dev/null \
  ; true
```

`mv` が通れば lock は実質的に外れる（`*.lock.old` は git からは見えない）。
これを Step 4-1 の前に毎回呼ぶこと。失敗しても続行（`; true` で握り潰す）。

### Step 4-0.5: 空コミット回避（github_push は内部で commit するため）

`github_push` は内部で `git commit` してから push する設計。bash で既に
`git commit` 済みだったり、変更が何も無い状態で呼ぶと `commit` 段で失敗する。

事前に **作業ツリーに 1 件以上の未コミット差分がある** ことを確認する：

```
git -C <work_dir> status --porcelain | head -1
```

何も出ない場合は、ローカルで既に commit 済み → さらに小さな差分（例：
`.deploy-marker` をタッチ）を 1 件追加してから github_push を呼ぶか、
ユーザーに `git push origin <branch>` を一度だけ走らせてもらうかを選ぶ。

### Step 4-1: github_push

```
mcp__AI_OSI_URI_Deploy__github_push:
  work_dir: <ローカル clone path>
  repo_owner: {repo_owner}
  repo_name: {repo_name}
  commit_message: "fix: <要約> (update-deploy)"
```

`commit_message` は Conventional Commits 推奨（`fix:` / `chore:` / `feat:`）。

### Step 4-2: Vercel 自動デプロイ監視（host=vercel）

```
新 deployment_id を list_deployments で取得（since=直近）
vercel_get_deployment_status を 10s 間隔で polling、最大 5 分
ERROR/CANCELED → vercel_get_build_logs で末尾取得 → 自動修正ループ（最大 3 回）
  典型: 型エラー、import 漏れ、env 不足 → 修正→github_push→再ポーリング
READY → Phase 5 へ
```

### Step 4-3: AWS パスの場合

```
infra に変更が無ければ ECS の自動デプロイは走らない。
アプリコード変更 → docker build/push → ecs update-service --force-new-deployment
を Claude Code 側で `/create-app` 後の手順（Phase 5-A）を流用。
本スキルは指示の clipboard 投入と監視のみ担当する。
```

---

## Phase 5: 検証（DoD ゲート）

evidence なしに完了宣言しない。以下を `update-progress.md` に貼ってから報告する。

| 検証項目 | 方法 | 合格条件 |
|---|---|---|
| コミット一致 | `git rev-parse HEAD` ↔ Vercel `meta.githubCommitSha` | 完全一致 |
| 本番反映 | `curl -sf {APP_URL}/{修正ページ}` の中身 grep | 期待文字列が出る |
| AI 修正の場合 | 実際にリクエスト送信、レスポンス全長計測 | 文末が `。` で終わる／JSON が valid／指定文字数届く |
| smoke test | `app-smoke-test` skill 呼び出し | 全項目 PASS |
| Supabase 結合 | `app-smoke-test` の PostgREST probe | `PGRST200` なし |

---

## Phase 6: 完了報告

```
✓ update-deploy 完了

リポ: https://github.com/{repo_owner}/{repo_name}
コミット: {short_sha} "{commit_message}"
本番URL: {APP_URL}
変更ファイル: {N} 件
  - {file_path_1}（{要約}）
  - {file_path_2}

検証:
  - コミット一致: ✓ ({sha} = vercel meta.githubCommitSha)
  - 本番反映: ✓ (期待文字列「{string}」検出)
  - smoke test: ✓ ({checks_passed}/{total})

ロールバック:
  git -C <dir> revert {sha} && github_push でもう一度
  または Vercel 画面で「直前のデプロイに戻す」
```

---

## エラーハンドリング

| Phase | 失敗 | 対応 |
|---|---|---|
| 0 | 拡張未導入 | `setup-deploy-environment` 案内、中断 |
| 1 | repo 特定できない | ユーザーに repo URL を直接聞く |
| 2 | clone 不可（PAT 不足/権限なし） | `gh auth status` を案内、または Org 権限付与依頼 |
| 2 | local clone が dirty | ユーザー確認、`--force` は絶対にしない |
| 3 | 該当箇所が複数 | 全箇所を提示し選んでもらう |
| 4 | `index.lock: File exists` | Step 4-0 の pre-push hygiene を実行（`mv .git/*.lock *.lock.old`）。サンドボックスから rm 不可な仕様 |
| 4 | `git commit` が `nothing to commit` で失敗 | Step 4-0.5 のとおり、既に commit 済みなら微小差分（`.deploy-marker` 等）を追加してから `github_push` |
| 4 | Vercel ビルド失敗 | `vercel_get_build_logs` 取得 → 自動修正ループ（最大 3 回） |
| 4 | 自動修正ループも失敗 | ログを提示して中断、ユーザー判断待ち |
| 5 | smoke test 失敗 | 「コミットは反映済みだが期待通り動いていない」と正直に報告 |

---

## やってはいけないこと

- 既存リポを **新規 push（force-push）** で上書きしない。`github_push` は通常 push のみに使う。
- ユーザー確認なしに **複数ファイル一気に書き換え** ない（特に文言・価格系）
- 「コミットされた」「READY になった」だけで「直りました」と顧客に伝えない。**Phase 5 の evidence が揃って初めて完了**。
- AI 機能の `max_tokens` を闇雲に最大化しない（コスト直撃）。**ユーザー要望に合った値**（例: 4096→16384）に留め、根拠を `update-progress.md` に記す。
- AWS パスでインフラ変更（terraform）を本スキルから直接行わない（`tf-state-backend` / `aws-static-deploy` の管轄）

---

## 関連スキル

- `deploy-app` — 新規アプリ作成（既存リポなしならこちら）
- `gh-create-repo-and-push` — 新規リポ作成 atomic
- `vercel-connect-and-deploy` — 新規 Vercel プロジェクト atomic（本スキルは既存プロジェクトの再デプロイのみ）
- `app-smoke-test` — Phase 5 の検証で呼ばれる
- `switch-to-live-mode` — Stripe を本番化したいときの専用スキル（本スキルは扱わない）
- `setup-deploy-environment` — 前提となる初期設定
