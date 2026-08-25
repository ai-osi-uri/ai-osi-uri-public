# サニタイズ要確認レポート

対象プラグイン: osi-creative, osi-docs, osi-deploy, osi-mobile-deploy, osi-knowledge, osi-finance, osi-backoffice

以下の 40 箇所に要注意語が残っています。publish 前に人手で確認してください（自動削除は文書を壊すため行いません）。

| ファイル | 行 | 語 | 抜粋 |
|---|---|---|---|
| plugins/osi-finance/README.md | 138 | 共有ドライブ | 顧客が決めるのは「OSI Finance ルートをどこに置くか」1問だけ（**共有ドライブ推奨**）、配下は規定ツリーで固定 |
| plugins/osi-finance/assets/schema/data-layout.yaml | 129 | CAIO | 重複=異常と判定してはいけない。例: INV-2026-07-016 は NITOH の CAIO と準備金2件を1通にまとめたもの。 |
| plugins/osi-finance/docs/導入手順書.md | 25 | 共有ドライブ | \| Google Workspace（**共有ドライブ**推奨） \| 必須 \| 台帳・契約書・証憑の保管 \| 既存契約でも可 \| |
| plugins/osi-finance/docs/導入手順書.md | 114 | 共有ドライブ | >   共有ドライブなら `G:\共有ドライブ\AI OSI URI\06.会計` のような形になります |
| plugins/osi-finance/docs/導入マニュアル.md | 47 | 共有ドライブ | \| Google Workspace（**共有ドライブ**）＋ デスクトップアプリ \| 必須 \| 台帳・契約書・証憑の保管 \| |
| plugins/osi-finance/config/osi-finance-settings.example.md | 157 | 共有ドライブ | 共有ドライブに1つ作り、配下は規定ツリー（00.契約書／01.受領請求書／02.送付請求書／03.経費管理）で固定。 |
| plugins/osi-finance/config/osi-finance-settings.example.md | 162 | 共有ドライブ | \| OSI Finance ルートの場所 \| {{DRIVE_ROOT_LOCATION 例: 共有ドライブ「経理」直下／マイドライブ（要・経理チーム共有）}} \| |
| plugins/osi-finance/skills/osi-finance-ar-sync/SKILL.md | 78 | CAIO | `INV-2026-07-016` は 対象月 2026-06 の行（CAIO 550,000）と 2026-07 の行（準備金 1,375,000 / 2,200,000）が |
| plugins/osi-finance/skills/osi-finance-plan/SKILL.md | 37 | CAIO | 実績は勘定科目、計画は計画自身の切り方（CAIO契約売上、コンサル外注、通信費の内訳…）で、 |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 47 | Plaud | - 任意：既存下書きへの確実な添付に Claude in Chrome（ブラウザ操作の `file_upload`）、本文パーソナライズに Obsidian（`obsidian-knowledge-consult`）／Plaud／Drive |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 133 | CAIO | - **グループが複数の対象月にまたがる場合は、対象月を摘要・明細名に必ず残す**（例「CAIO業務 2026年4〜6月分」）。 |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 162 | 共有ドライブ | - **マウント済みの Drive 共有ドライブ（ローカル同期フォルダ＝FS）** に base64 をデコードして書き出す： |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 173 | Plaud | - 当月ご一緒した取り組みを **Obsidian（`30_Projects/_Active/{社名}/議事録`、`obsidian-knowledge-consult` 経由）→ Plaud → Drive** の順で拾い、お礼文に1段落 |
| plugins/osi-finance/skills/osi-finance-setup/SKILL.md | 77 | 共有ドライブ | ルートフォルダ「OSI Finance」を**どこに作るか**だけを聞く。**共有ドライブを第一推奨** |
| plugins/osi-finance/skills/osi-finance-setup/SKILL.md | 101 | 共有ドライブ | OSI Finance/                 ← 顧客が決めるのはこの置き場所だけ（共有ドライブ推奨） |
| plugins/osi-deploy/skills/create-app/SKILL.md | 56 | GITHUB_ORG | **重要:** `GITHUB_ORG` が未設定だと、`github_create_repo_and_push` は `owner_override` を |
| plugins/osi-deploy/skills/create-app/references/aws-app-gotchas.md | 54 | 共有ドライブ | 初回 apply 前に **`tf-state-backend` スキル**を呼ぶ（state基盤の作成＋backend.tf差し込み）。既存のローカルstateアプリは同スキルの migrate-existing（`aws_terrafo |
| plugins/osi-deploy/skills/create-app/references/drive-record.md | 21 | Notion | Notion のリード一覧に案件が登録されていれば、対応する Drive 案件フォルダが存在する。 |
| plugins/osi-deploy/skills/create-app/references/drive-record.md | 66 | Notion | \| 案件 \| （Notion リード ID / 案件名 / なし） \| |
| plugins/osi-deploy/skills/tf-state-backend/SKILL.md | 66 | 共有ドライブ | 6. コード一式＋HANDOFF を共有ドライブへ退避（揮発対策） |
| plugins/osi-deploy/skills/tf-state-backend/SKILL.md | 151 | 共有ドライブ | 復旧時にバケット/キーが分からなくなる**。コード一式を共有ドライブの案件フォルダへ退避する。 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 4 | 共有ドライブ | デプロイを使えるようにする初回セットアップ。**共有ドライブの .env は使わず**、 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 19 | 共有ドライブ | > 旧版は `.deploy-credentials/.env` にトークンを書き込んでいたが、平文・共有ドライブ同期・ |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 25 | 共有ドライブ | （社内手順：共有ドライブ「環境構築キット」参照） |
| plugins/osi-deploy/skills/aws-static-deploy/SKILL.md | 36 | 共有ドライブ | 共有ドライブの `.deploy-credentials/.env` は **任意フォールバック**としてのみ参照する。 |
| plugins/osi-deploy/skills/update-deploy/SKILL.md | 68 | GITHUB_ORG | \| `repo_owner` \| `ai-osi-uri` または個人 username \| 既定は GITHUB_ORG / GITHUB_USERNAME \| |
| plugins/osi-mobile-deploy/skills/deploy-mobile-app/SKILL.md | 165 | GITHUB_ORG | \| GITHUB_ORG \| `ai-osi-uri` / `personal` \| `create-app` の `USE_ORG` 判定に準拠 \| |
| plugins/osi-backoffice/skills/contract-docusign-send/SKILL.md | 92 | 共有ドライブ | - **Drive（マウント済み共有ドライブ）**：格納先は `references/storage-and-naming.md` の定義に従う。**このスキルにパスを直書きしない**（組織ごとに違い、移行でも動く）。 |
| plugins/osi-backoffice/skills/contract-docusign-send/_旧版_S3方式_20260817/docusign-and-s3.md | 30 | 共有ドライブ | - **file tools（Mac）**：outputs と共有ドライブのみ書ける。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/storage-and-naming.md | 3 | 共有ドライブ | 契約の正本は Drive の**契約書フォルダ**（`{契約書ルート}`）。マウント済み共有ドライブに書くと Drive に同期される。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/storage-and-naming.md | 24 | CAIO | - `{ID}.{企業名}` は営業管理表のZ列（案件ID）＝ `21.PJT資料/01.CAIO事業/` のフォルダ番号に合わせる。該当フォルダが無ければ作成（既存の命名に倣う）。 |
| plugins/osi-docs/skills/pptx-custom/exec-deck-patterns.md | 11 | CAIO | - ✅「初期費用ゼロのCAIO契約なら、3ヶ月で投資回収できる」 |
| plugins/osi-docs/skills/deck-composition/SKILL.md | 106 | CAIO | - ❌「コア事業の説明」→ ✅「では本丸の CAIO 事業を——仕組み・価格・現状を見ていく」 |
| plugins/osi-docs/skills/deck-composition/SKILL.md | 114 | CAIO | 複数スライドで使う用語・略語（CAIO, ARR, NPS 等）は、**初出のスライドで**定義する。5枚後に「Xとは」を置かない。定義はサブタイトルにインラインで入れるか、使い始める前に定義スライドを1枚置く。 |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 135 | 共有ドライブ | { "name": "Excel管理簿", "where": "営業共有ドライブ" } |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 167 | Notion | \| `name`    \| yes  \| ドキュメント名（例：「契約書ドラフト Word」「Notion 商談 DB」） \| |
| plugins/osi-docs/skills/architecture-proposal/SKILL.md | 12 | yourrecord | ※ 自社サービス（CAIO / yourrecord 等）の新規営業・初回提案・見積提案は別スキル |
| plugins/osi-docs/skills/architecture-proposal/SKILL.md | 12 | CAIO | ※ 自社サービス（CAIO / yourrecord 等）の新規営業・初回提案・見積提案は別スキル |
| plugins/osi-docs/skills/architecture-proposal/scripts/deck_helpers.py | 11 | CAIO | # ---- ブランド配色（CAIO資料準拠 / EDIT可） ---- |
| plugins/osi-creative/skills/ai-video-production/references/hook-insight.md | 57 | CAIO | この一言だと、B4（会社にひとりAIの意思決定者を置く＝CAIO）がそのまま答えになる。 |
