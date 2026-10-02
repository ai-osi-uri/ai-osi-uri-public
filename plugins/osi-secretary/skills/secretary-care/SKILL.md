---
name: secretary-care
description: >
  できあがった AI 秘書の様子を見る・最新にするスキル。メンバー数・LINE がつながっているか・業務定義の版・秘書の版と最新・足りない関数を確かめ、
  新しい版があれば関数とデータの形（追加分）と管理画面を入れ直す。「秘書を最新にして」「秘書の様子を見て」「秘書が返事しない」
  「秘書の管理画面が開かない」「設定用リンクが切れた」などで発動する。秘書を新しく作るのは secretary-create、業務定義の作り直しは secretary-flow。
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# secretary-care（秘書の様子を見る・最新にする）

## 様子を見る
1. 秘書の置き場（`project_ref`）を確かめる（分からなければ `supabase_list_projects` で `-secretary` の付く置き場）。
2. `secretary_status` を見て、普通の言葉で伝える：
   - LINE：`line_key`（つながっているか）、`last_event`（最後に LINE から届いた時刻）
   - 人：`members`・`named`（呼び名の付いた人）
   - 業務定義：`flow_version`・`flow_steps`
   - 版：`template_version`（入っている版）と `template_latest`（Deploy 拡張に入っている最新）、`functions_missing`
   - 管理画面：`admin_site`

## 最新にする（版が古い・関数が足りない）
1. 「秘書を <入っている版> から <最新> にします。設定・業務定義・人はそのまま残ります。▶ 進める」と見せて OK をもらう。
2. `secretary_update`（`with_sql: true`。データの形の追加分も流す。何度流しても壊れない）。
3. 管理画面も入れ直す：`secretary_admin_deploy`（同じ project_name。同じ Vercel のプロジェクトに新しい版が出る）。
4. `secretary_status` で `functions_missing: []` と版を確かめ、LINE で「残ってる？」と送ってもらう。

## 困ったとき
| 様子 | 見るところ・すること |
|---|---|
| LINE で返事が来ない | `last_event` が古い → LINE の「応答設定」で応答メッセージ OFF・Webhook ON か。`line_key: false` → 設定用リンクから鍵を貼り直す（下） |
| 秘書が「うまく考えられませんでした」のような返事をする | Claude の API キーが入っていない・無効。設定用リンクで Claude の鍵を貼り直す（Anthropic Console で作り直す） |
| 設定用リンクが切れた | `secretary_admin_deploy` をもう一度呼ぶ（リンクだけ作り直る） |
| 管理画面が開かない・ログインできない | `admin_site` を開く。ログインは呼び名を入れると LINE にリンクが届く。開けなければ `secretary_admin_deploy` で出し直す |
| 関数が足りない | `secretary_update` |

鍵（LINE・Claude）は本人が設定用リンクに貼る。チャットに貼られたら使わず、作り直して貼り直してもらう。
