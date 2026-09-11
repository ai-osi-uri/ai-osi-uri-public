# 型 3：アイデア → アプリ公開

## いつ
「こういう仕組みが欲しい」が出た（商談の場でもよい）。その場でモックを見せる、または翌日までに動くものを出す。

## 入力
- 一言の要望（「予約が LINE で来て属人化している」「FAQ を先に返したい」）
- 誰が使うか（現場／顧客／社内）と、置き場（Web で公開／ローカルだけ）
- 案件ID（案件フォルダの `03_制作・成果物/app/` に記録を置くため）

## 連鎖
| # | スキル | 渡すもの → 受け取るもの |
|---|---|---|
| 1 | `osi-deploy:create-app` | 要望 → スタック判定（Web=Vercel/AWS・Desktop=Electron・ローカル出力）。**モバイルは `osi-mobile-deploy:deploy-mobile-app` へ直接** |
| 2 | （create-app 内）`osi-deploy:harness-init` | scaffold → AGENTS.md / CLAUDE.md / feature_list.json（不変条件 5 行＋非機能 7 行）。検証なしに完了宣言しない仕込み |
| 3 | （create-app 内）`osi-deploy:deploy-preflight` | リポ → PASS/FAIL/WARN。**FAIL があれば止まる** |
| 4 | （create-app 内）`gh-create-repo-and-push` → `vercel-connect-and-deploy` / `aws-static-deploy` | リポ → 公開 URL。Supabase を使うなら `supabase-set-auth-url` |
| 5 | （create-app 内）`osi-deploy:app-smoke-test` | 公開 URL → HTTP レベルの動作確認 JSON |
| 6 | `osi-deploy:app-manual` | 実装（ルート・ラベル・認証）→ 運営向け／利用者向けの使い方 pptx。**記憶から書かず現物のコードから起こす** |
| 7 | 記録 | `drive-record.md` の作法で `_アプリ情報_README.md` を案件フォルダに、`{{ledgers.apps}}` に 1 行 |
| 後 | `osi-deploy:update-deploy`（直す）／`osi-deploy:app-concierge`（「公開されてる？」「開かない」の確認）／`switch-to-live-mode`（決済本番化） | — |

## 止まる場所
- スタックと置き場（Web 公開か、ローカル出力か。Deploy コネクタが無い環境は `local-project-output`）
- preflight の FAIL
- 決済を本番にするとき（実課金）と、実カードでの E2E は人がやる
- 顧客のアカウントへ移管するとき（卒業時だけ。運用中はゼロ）

## 出口
- 公開 URL（または runnable なローカルプロジェクト）
- 案件フォルダに `_アプリ情報_README.md`（URL・リポ・構成・更新手順）、アプリ台帳に 1 行
- 使い方マニュアル（内部版・外部版）

## 完了条件
- smoke test が通った URL がある（「デプロイした」ではなく「開いて返ってきた」）
- feature_list.json の各項目に検証の証拠（evidence）が貼られている
- 不変条件 5 行・非機能 7 行がリポにあり、以後の update-deploy がそれを読む
- マニュアルの URL・ボタン名が現物と一致している（分割・改名・URL 変更のたびに更新）
- アプリ台帳に載っている

## よくある事故
- create-app 後の作業フォルダはコピーで、以後の編集を github_push しても入らない（嘘の成功）→ put_file で反映
- Vercel が脆弱な next を拒否する／インメモリ状態が消える → gotchas に従う
- 6 月のデモの土台が消えていて「実データ・実送信」と言えなくなる → 台帳に記録し、消えたら作り直す
