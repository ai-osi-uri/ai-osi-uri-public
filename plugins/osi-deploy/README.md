# osi-deploy

AI OSI URI のアプリ・LP・販売サイト・SaaS デプロイ自動化。Vercel パス（軽量）と AWS パス（業務系）に加えて、iOS ネイティブの Xcode Cloud / TestFlight / App Store 申請までカバー。Stripe Live モード切り替え・Supabase Auth URL 更新・スモークテストまで一気通貫。

## スキル一覧

- `deploy-app` — Web / SaaS の新規作成オーケストレータ（Vercel / AWS を判定して起動）
- `setup-deploy-environment` — 初期セットアップ（GitHub / Vercel / Stripe / Supabase / ASC キー投入）
- `gh-create-repo-and-push`
- `vercel-connect-and-deploy`
- `aws-static-deploy`
- `supabase-set-auth-url`
- `app-smoke-test`
- `switch-to-live-mode`
- `update-deploy` — 既存 Web アプリの更新（ソース修正→push→Vercel自動デプロイ→smoke testまで一気通貫）
- `ios-mobile-release` — **iOS ネイティブ**の Xcode Cloud / TestFlight / App Store 申請。Xcode バージョンは
  **N-1 ポリシー固定**（latest の1個前・N-1 内の最新パッチ）。カナリアで N を週次監視し、SDK 締切近接時に N 前倒し、N-1 提供終了で自動繰り上げ。前提：`AI OSI URI Deploy` 拡張 v1.17.2+ の
  新ツール（`xcode_cloud_list_xcode_versions` / `xcode_cloud_update_workflow`）が入っていること。
