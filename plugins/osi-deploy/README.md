# osi-deploy

AI OSI URI のアプリ作成・公開自動化。Web、Desktop、Mobile、ローカル出力に対応し、DNS設定・事前診断・公開後の更新まで扱う。

## スキル一覧

- `create-app` — Web / Desktop / Mobile / ローカル出力を判定する新規作成オーケストレータ
- `setup-deploy-environment` — 初期セットアップ（GitHub / Vercel / Stripe / Supabase / ASC キー投入）
- `gh-create-repo-and-push`
- `vercel-connect-and-deploy`
- `aws-static-deploy`
- `aws-route53`
- `deploy-preflight`
- `supabase-set-auth-url`
- `app-smoke-test`
- `switch-to-live-mode`
- `update-deploy` — 既存 Web アプリの更新（ソース修正→push→Vercel自動デプロイ→smoke testまで一気通貫）
> **iOS ネイティブのリリースは osi-mobile-deploy に移設**（2026-08）。
> ビルド〜TestFlight は `ios-testflight-deploy`、TestFlight より先（ビルド昇格・App Store 申請・
> Xcode バージョン N-1 ピン運用）は `ios-appstore-release`。いずれも osi-mobile-deploy 側にある。
