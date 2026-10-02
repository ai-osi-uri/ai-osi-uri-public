# Web-Railway パス（Phase 4-W-R）

`create-app` が Railway を選んだときの実行手順。実作業は atomic スキル `railway-deploy` に
委譲する。ここでは **create-app として何を判断し、何を渡すか**を書く。

## 前提（着手前に必ず）

1. `health_check` の `railway.valid: true`（拡張 v1.35.0 以降が必要）
2. `railway_health_check` で作成先ワークスペースが見えること
3. 不足 → `setup-deploy-environment` を案内して中断。**未設定のまま進めない**

## 構成の決定

| アプリ定義 | 構成 |
|---|---|
| API サーバー（Node / Python / Go 等）+ DB | Railway サービス + Postgres |
| WebSocket・リアルタイム | Railway サービス（常駐が必要なため） |
| キュー処理・ジョブ | Web サービス + Worker サービス + Redis |
| 定期実行（バッチ） | サービスに `cron_schedule`（UTC） |
| Dockerfile がある既存アプリ | Railway サービス（Dockerfile をそのまま使う） |
| Next.js の画面 + 重いバックエンド | 画面は Vercel、API だけ Railway（併用） |

### 認証がある案件

Railway に認証機能は無い。Phase 3 のプラン承認で**どれで行くかを明示して合意を取る**:

- Supabase Auth を併用（DB も Supabase に寄せるなら Vercel パスの方が素直）
- アプリで実装（Lucia / Auth.js / Devise / FastAPI Users など）
- 社内ツールなら前段に認証プロキシを置く

## 流れ

```
scaffold → gh-create-repo-and-push → harness-init
→ （必要なら）railway_add_database
→ railway-deploy（プロジェクト → サービス → ドメイン → 状態確認）
→ app-smoke-test
```

## scaffold で守ること

- `PORT` 環境変数で listen する（固定ポート禁止）
- ヘルスチェック用の `/health`（200 を返すだけ）を用意する
- DB 接続は `DATABASE_URL` などの環境変数から読む（値はコードに書かない）
- マイグレーションは起動コマンドに混ぜず `pre_deploy_command` に分ける

## 完了レポートに入れるもの

- 公開 URL / Railway のダッシュボード URL
- サービス・DB の構成、環境変数の名前一覧
- スリープ設定の有無（常駐のぶん使った分だけ課金される旨）
