# Web-Cloudflare パス（Phase 4-W-C）

`create-app` が Cloudflare を選んだときの実行手順。実作業の大半は atomic スキル
`cloudflare-deploy` に委譲する。ここでは **create-app として何を判断し、何を渡すか**を書く。

## 前提（着手前に必ず）

1. `health_check` の `cloudflare.valid: true`（拡張 v1.20.0 以降が必要）
2. `cloudflare_health_check` で以下を確認
   - `token_valid: true`
   - `account_id` が 32 桁で返る
   - `workers_dev_subdomain` が値を返す（`(未登録)` ならダッシュボードで一度だけ登録。**API 不可**）
   - `d1_permission: "OK"` / `r2_permission: "OK"`（使う分だけ）
3. 不足 → `setup-deploy-environment` を案内して中断。**権限不足のまま進めない**

## 構成の決定

| アプリ定義 | 構成 |
|---|---|
| LP / コーポサイト（API なし） | Workers（静的アセットのみ。Worker コード不要） |
| SPA + API + データ保存 | Workers + D1（＋画像等があれば R2） |
| セッション・レート制限が要る | 上記 + KV |
| 大きなファイル配信（PDF・動画・画像） | 上記 + R2（**エグレス無料**がここで効く） |
| Next.js を使いたい | Workers + `@opennextjs/cloudflare`（下の注意を読む） |
| ビルドを Cloudflare 側で回したい | Pages（Git 連携） |

### 認証がある案件（最重要の分岐）

D1 には Supabase Auth も RLS も無い。Phase 3 のプラン承認で**必ず明示して合意を取る**:

| 案件 | 提示する選択肢 |
|---|---|
| 社内ツール・限定公開 | **Cloudflare Access**（Zero Trust）で前段認証。アプリ側実装ゼロ |
| 一般公開 SaaS で認証必須 | **Vercel + Supabase に戻すことを推奨**。Cloudflare に寄せる利点より自前認証のコストが大きい |
| どうしても Cloudflare + 自前認証 | D1 + KV でセッション実装。**セキュリティ責任がアプリ側に移る**ことを明記して承認を取る |

ユーザーが「Cloudflare で」と言っただけで自前認証の実装に踏み込まない。
ここを黙って進めるのが、この構成でいちばん高くつく判断ミス。

### Next.js の注意

Workers は Node.js ランタイムではないため、素の `next build` の成果物は動かない。
`@opennextjs/cloudflare` を挟む（設定は `cloudflare-deploy` の
references/wrangler-config.md パターン B）。ISR / middleware / server actions を
多用する案件でビルドが通らず時間を溶かしそうなら、**Vercel パスに戻す判断を早く出す**。
「Cloudflare に寄せること」は目的ではない。

## 実行順序

```
1. scaffold 生成（Vite + React + Hono を既定。Next.js は上の注意を踏んだうえで）
2. gh-create-repo-and-push        → repo_id / work_dir
3. harness-init                   → deploy-progress.md 作成
4. リソース先出し（cloudflare-deploy 側で実行）
     cloudflare_d1_create / cloudflare_r2_create_bucket / cloudflare_kv_create_namespace
5. wrangler.jsonc を書く（4 で得た id を埋める）
6. cloudflare-deploy スキルへ委譲
     deploy → status polling → workers.dev 公開 → secrets → D1 マイグレーション
7. custom_domain があれば cloudflare_add_custom_domain
8. app-smoke-test で公開 URL を外部検証
9. Drive 記録 → 完了レポート
```

**4 と 5 の順序は入れ替えない。** D1 / KV は作成後の ID を設定ファイルに書く必要があり、
先に deploy するとバインディング未定義で落ちて二度手間になる。

## cloudflare-deploy への引き渡し

```
repo_dir:      <ローカルクローンの絶対パス>
app_name:      <PROJECT_NAME_LOWER>       // workers.dev のサブドメインになる
needs_db:      true|false                 // データ保存があるか
needs_storage: true|false                 // 画像・PDF・添付があるか
needs_kv:      true|false                 // セッション・レート制限があるか
secrets:       { ANTHROPIC_API_KEY: "..." } // 平文で wrangler.jsonc に書かないもの
custom_domain: <任意。Cloudflare 管理ゾーンであること>
use_pages:     false                      // 新規は Workers を既定
```

## Vercel パスとの違い（運用上）

| 項目 | Vercel | Cloudflare |
|---|---|---|
| 初回作成の冪等性 | プロジェクトは 1 リポ 1 つ。create は一度きり | `wrangler deploy` は**同名 Worker を上書き**するので何度打っても増殖しない |
| 更新方法 | git push → CI 自動デプロイ | `update-deploy` から `cloudflare_deploy_worker` を再実行（Git 連携なしでも可） |
| env の後付け | 初回 create に全部入れるのが安全 | `cloudflare_set_secret` で後からいつでも追加でき、**再デプロイ不要** |
| 本番 URL | production alias | `https://<app>.<subdomain>.workers.dev`（固定） |
| ビルド場所 | Vercel 側 | **ローカル**（`cloudflare_deploy_worker` が npm install→build→deploy） |

ビルドがローカルで走る点に注意。ビルドが通らないと deploy まで到達しないので、
`cloudflare_deploy_status` の `step` が `build` で止まったらアプリ側のビルドエラー。

## 完了レポートに載せるもの

- 公開 URL（workers.dev / 独自ドメイン）と `app-smoke-test` の HTTP 200 の証跡
- D1 のテーブル一覧（`cloudflare_d1_query` の出力）
- 作成したリソース名（Worker / D1 / R2 / KV）
- 認証方式（Cloudflare Access / 自前 / なし）と、その合意を取った旨
- 更新方法（`update-deploy` を使う。create-app を再実行しない）
