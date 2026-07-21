# osi-deploy

AI OSI URI のアプリ・LP・販売サイト・SaaS デプロイ自動化。Vercel パス（軽量）と AWS パス（業務系）に加え、**モバイル配信（iOS TestFlight）**にも対応。Stripe Live モード切り替え・Supabase Auth URL 更新・スモークテストまで一気通貫。

## スキル一覧

### Web / SaaS
- `deploy-app`
- `setup-deploy-environment`
- `gh-create-repo-and-push`
- `vercel-connect-and-deploy`
- `aws-static-deploy`
- `supabase-set-auth-url`
- `app-smoke-test`
- `switch-to-live-mode`
- `update-deploy` — 既存アプリを更新（ソース修正→push→Vercel自動デプロイ→smoke testまで一気通貫）

### モバイル配信 (new in 0.9.0)
- `mobile-testflight-deploy` — iOS アプリを Fastlane `ios_beta_auto` レーン経由で TestFlight に配信。Xcode Automatic Signing 対応（match 不要）。macOS Keychain の `osi-mobile-deploy.*` secrets を使用。
