---
name: supabase-set-auth-url
description: |
  Supabase の Auth 設定（Site URL / Redirect URLs）を本番デプロイ後の URL に更新する。
  localhost:3000 も自動で許可リストに含め、Magic Link が localhost
  に飛ぶ典型問題を潰す。`create-app` から呼ばれる。単体では「Supabase Auth URL
  を更新して」「Magic Link が localhost に飛ぶ」で発動。DB スキーマ・edge function
  の操作には使わない。
version: 0.2.1
---

# Supabase Auth URL 更新（atomic / 拡張ツール版）

本番デプロイ後の URL に `Site URL` と `uri_allow_list` を更新する。**認証情報は AI OSI URI
Deploy 拡張**が保持する Supabase PAT を使う。`.env` は読まず、拡張の MCP ツール
`supabase_set_auth_url` を呼ぶ。

## 前提条件

| 前提 | 確認方法 | 不足時の対応 |
| --- | --- | --- |
| 拡張が有効・Supabase PAT 入力済み | `health_check` で `supabase.valid: true` | `setup-deploy-environment` を案内 |
| プロジェクト ref 取得済み | 呼び出し側 or `supabase_list_projects` | `supabase_list_projects` で選択肢提示 |
| `APP_URL` がデプロイ後の URL | https で始まる | バリデーション |

## 入力契約（= ツール引数）

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `project_ref` | ✅ | Supabase プロジェクト ref（`supabase_list_projects` の `id`） |
| `site_url` | ✅ | 本番デプロイ URL（`https://<project>.vercel.app` など） |
| `redirect_urls` | 任意 | 追加で許可したい Redirect URL の配列 |

## 実行

```
// ref が不明なら一覧から特定
supabase_list_projects()

supabase_set_auth_url({
  project_ref: "<ref>",
  site_url: "https://<project>.vercel.app",
  redirect_urls: []   // 任意
})
```

ツールは `site_url` と `uri_allow_list`（`<site_url>/**` と `http://localhost:3000/**` を自動付与）を
`PATCH /v1/projects/<ref>/config/auth` で更新する。`uri_allow_list` は完全置換なので、
追加許可は `redirect_urls` にまとめて渡す。

## エラー時の挙動

| 事象 | 対応 |
| --- | --- |
| PAT 未設定 / 401 / 403 | 拡張設定で Supabase PAT を確認・再入力。**デプロイ自体は成功扱い**、手動更新を案内 |
| 404（ref 違い） | `supabase_list_projects` で再選択 |

このスキルが失敗してもデプロイは成功しているので、オーケストレータは中断せず警告＋手動更新手順を提示すれば良い。

## マルチテナント RLS の典型パターン（参考）

このスキル自体は Auth URL 更新だけだが、マルチテナント SaaS のフル RLS テンプレは
`supabase-multitenant-rls` スキルにまとまっている。最重要ポイントだけここに：

- **`current_tenant_id()` / `is_admin()` は SECURITY DEFINER 必須**（再帰防止）
- **INSERT 時 tenant_id 設定漏れ → 500** が頻発するので `getMyTenantId()` ヘルパで統一
- **新規ユーザー auto-create トリガーは `raw_app_meta_data` から tenant/role を読む**
- **派生テーブルの FK は `ON DELETE SET NULL`**（RESTRICT のままだと下流が消せない）
- 検証は `app-smoke-test` の `rls_users_select` probe で

詳細とテンプレは `supabase-multitenant-rls` 参照。

---

## 注意事項

- `uri_allow_list` は完全置換。追加許可 URL は毎回 `redirect_urls` で渡す。
- 更新は即時反映だが 1-2 分のキャッシュがあることがある。直後の Magic Link テストは少し時間を空ける。
