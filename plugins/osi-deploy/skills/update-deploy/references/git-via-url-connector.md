# 手元のフォルダと GitHub を、URL でつなぐコネクタでつなぐ（2026-10-16〜）

手元の Deploy 拡張の `github_push`・`github_clone`・`github_pull`・`github_create_repo_and_push` の代わり。
GitHub の鍵はサーバーの中だけで使い、Claude にも手元にも出ない。中身は会話を通さず、Claude が zip にして直接上げる。

## 送る（push の代わり）

1. 新しいリポジトリなら、先に `github_create_repo`（中身は空のまま）。
2. `github_upload_url` を呼ぶ。`upload_url`（10 分で切れる）と `upload_id` が返る。
3. 手元のシェルでフォルダを zip にして上げる（返ってきた `how` のとおり）:
   ```bash
   cd <フォルダ> && zip -qr /tmp/up.zip . -x 'node_modules/*' '.git/*' '.next/*'
   curl -sS -X PUT -H 'content-type: application/zip' --data-binary @/tmp/up.zip '<upload_url>'
   ```
4. `github_push_folder(repo_name, upload_id, message)` を **dry_run のまま**呼ぶ。足す・変わる・消すの一覧が返る。
5. 一覧を本人に見せる。特に `deleted`（消すもの）を確かめる。OK なら同じ `upload_id` で `dry_run:false`。
6. 返ってきた `commit_sha` を記録する。Vercel 等の Git 連携があれば push で自動デプロイが走る（`vercel_get_deployment_status`）。

- `mirror`（既定 true）は zip に無いファイルを消す。足すだけにしたいとき・フォルダの一部だけ送るときは `mirror:false`。
- リポジトリの中の一部のフォルダにだけ置くときは `base_path`（例 `web`）。その外には触らない。
- 送らない・消さないもの（既定）：`.git/`・`node_modules/`・`.next/`・`.vercel/`・`.env`・`.env.*`（`.env.example` は送る）・鍵のファイル。ほかにあれば `exclude`。
- 1 回の zip は 200MB・5,000 ファイルまで。1 ファイル 50MB まで。大きい画像・動画は Git に入れず、置き場か Releases に置く。

## 取り込む（clone / pull の代わり）

1. `github_download_folder(repo_name, ref?)` を呼ぶ。`download_url`（10 分）と `head_sha` が返る。
2. 手元で落として展開する:
   ```bash
   curl -sSL -o /tmp/repo.zip '<download_url>' && unzip -q /tmp/repo.zip -d <置き場所>
   ```
   1 段目に `<owner>-<repo>-<sha>/` のフォルダが 1 つできる。中身を作業フォルダに移す。
3. 直したあと送るときは、`github_push_folder` に `expected_head_sha: <head_sha>` を渡す。
   そのあいだに誰かが push していたら止まる（上書きしない）。止まったら取り込み直して、直したところを当て直す。

## 事故の型

- いきなり `dry_run:false` で送り、要るファイル（`.github/workflows/` など）を消す → 必ず dry_run の `deleted` を見せてから
- zip の 1 段目に余計なフォルダが入り、リポジトリが一段深くなる → 1 段目が 1 つのフォルダだけなら自動で外す。外れていないときは `stripped_root` を見る
- `upload_url` が切れていた（10 分）→ `github_upload_url` からやり直す
- 手元の Deploy 拡張がつながっていて、手元の Git の細かい操作（ブランチの付け替え・やり直し）が要るときだけ、手元の道具を使ってよい
