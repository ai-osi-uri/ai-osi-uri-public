# サニタイズ要確認レポート

対象プラグイン: osi-creative, osi-docs, osi-deploy

以下の 10 箇所に要注意語が残っています。publish 前に人手で確認してください（自動削除は文書を壊すため行いません）。

| ファイル | 行 | 語 | 抜粋 |
|---|---|---|---|
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 135 | 共有ドライブ | { "name": "Excel管理簿", "where": "営業共有ドライブ" } |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 167 | Notion | \| `name`    \| yes  \| ドキュメント名（例：「契約書ドラフト Word」「Notion 商談 DB」） \| |
| plugins/osi-docs/skills/pptx-custom/SKILL.md | 190 | CAIO | - ✅ "Now let's look at the core CAIO business — how it works, pricing, current state" — transitions and previews |
| plugins/osi-docs/skills/pptx-custom/SKILL.md | 199 | CAIO | If a term will appear on multiple slides, define it the first time it appears — not five slides later. The most common b |
| plugins/osi-docs/skills/pptx-custom/SKILL.md | 203 | CAIO | 1. **Inline definition in the subtitle** when the term first appears: `"CAIO (= a monthly retainer that teaches companie |
| plugins/osi-deploy/skills/gh-create-repo-and-push/SKILL.md | 31 | GITHUB_ORG | > 旧版では `.env` の `GITHUB_ORG` で作成先を切り替えていたが、拡張版では固定の Org 設定を |
| plugins/osi-deploy/skills/aws-static-deploy/SKILL.md | 30 | 共有ドライブ | 共有ドライブの `.deploy-credentials/.env` は **任意フォールバック**としてのみ参照する。 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 3 | 共有ドライブ | description: AI OSI URI の Cowork から LP・販売サイト・課金つきアプリを自動デプロイするための初回セットアップ。**共有ドライブの .env は使わず**、各ユーザーが「AI OSI URI Deploy」 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 13 | 共有ドライブ | > 旧版は `.deploy-credentials/.env` にトークンを書き込んでいたが、平文・共有ドライブ同期・ |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 19 | 共有ドライブ | （社内手順：共有ドライブ「環境構築キット」参照） |
