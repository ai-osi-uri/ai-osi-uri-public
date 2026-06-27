# サニタイズ要確認レポート

対象プラグイン: osi-creative, osi-docs, osi-deploy, osi-knowledge, osi-finance, osi-backoffice

以下の 13 箇所に要注意語が残っています。publish 前に人手で確認してください（自動削除は文書を壊すため行いません）。

| ファイル | 行 | 語 | 抜粋 |
|---|---|---|---|
| plugins/osi-backoffice/skills/contract-docusign-send/SKILL.md | 50 | 共有ドライブ | - **Drive（マウント済み共有ドライブ）**：格納先 `30.契約管理/`。書き込みはマウント経由で Drive に同期される。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/storage-and-naming.md | 3 | 共有ドライブ | 契約の正本は Drive の `30.契約管理/`。マウント済み共有ドライブに書くと Drive に同期される。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/storage-and-naming.md | 20 | Notion | - `{ID}.{企業名}` は Notion リード/PJT 番号に合わせる。該当フォルダが無ければ作成（既存の命名に倣う）。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/docusign-and-s3.md | 26 | 共有ドライブ | - **file tools（Mac）**：outputs と共有ドライブのみ書ける。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/setup.md | 39 | 共有ドライブ | - Drive（共有ドライブ `30.契約管理/`）がマウントされていること（格納先）。 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 3 | 共有ドライブ | description: AI OSI URI の Cowork から LP・販売サイト・課金つきアプリを自動デプロイするための初回セットアップ。**共有ドライブの .env は使わず**、各ユーザーが「AI OSI URI Deploy」 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 13 | 共有ドライブ | > 旧版は `.deploy-credentials/.env` にトークンを書き込んでいたが、平文・共有ドライブ同期・ |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 19 | 共有ドライブ | （社内手順：共有ドライブ「環境構築キット」参照） |
| plugins/osi-deploy/skills/deploy-app/references/aws-app-gotchas.md | 54 | 共有ドライブ | 初回 apply 前に **`tf-state-backend` スキル**を呼ぶ（state基盤の作成＋backend.tf差し込み）。既存のローカルstateアプリは同スキルの migrate-existing（`aws_terrafo |
| plugins/osi-deploy/skills/gh-create-repo-and-push/SKILL.md | 31 | GITHUB_ORG | > 旧版では `.env` の `GITHUB_ORG` で作成先を切り替えていたが、拡張版では固定の Org 設定を |
| plugins/osi-deploy/skills/aws-static-deploy/SKILL.md | 30 | 共有ドライブ | 共有ドライブの `.deploy-credentials/.env` は **任意フォールバック**としてのみ参照する。 |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 135 | 共有ドライブ | { "name": "Excel管理簿", "where": "営業共有ドライブ" } |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 167 | Notion | \| `name`    \| yes  \| ドキュメント名（例：「契約書ドラフト Word」「Notion 商談 DB」） \| |
