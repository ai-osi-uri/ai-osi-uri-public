# サニタイズ要確認レポート

対象プラグイン: osi-creative, osi-sales, osi-docs, osi-deploy, osi-mobile-deploy, osi-knowledge, osi-finance, osi-core, osi-backoffice, osi-marketing

以下の 134 箇所に要注意語が残っています。publish 前に人手で確認してください（自動削除は文書を壊すため行いません）。

| ファイル | 行 | 語 | 抜粋 |
|---|---|---|---|
| plugins/osi-finance/README.md | 157 | 共有ドライブ | 顧客が決めるのは「OSI Finance ルートをどこに置くか」1問だけ（**共有ドライブ推奨**）、配下は規定ツリーで固定 |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 50 | Plaud | - 任意：既存下書きへの確実な添付に Claude in Chrome（ブラウザ操作の `file_upload`）、本文パーソナライズに Obsidian（`obsidian-knowledge-consult`）／Plaud／Drive |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 161 | CAIO | - **グループが複数の対象月にまたがる場合は、対象月を摘要・明細名に必ず残す**（例「CAIO業務 2026年4〜6月分」）。 |
| plugins/osi-finance/skills/osi-finance-invoice/SKILL.md | 246 | Plaud | - 当月ご一緒した取り組みを **Obsidian（`30_Projects/_Active/{社名}/議事録`、`obsidian-knowledge-consult` 経由）→ Plaud → Drive** の順で拾い、お礼文に1段落 |
| plugins/osi-finance/skills/osi-finance-setup/SKILL.md | 86 | 共有ドライブ | ルートフォルダ「OSI Finance」を**どこに作るか**だけを聞く。**共有ドライブを第一推奨** |
| plugins/osi-finance/skills/osi-finance-setup/SKILL.md | 110 | 共有ドライブ | OSI Finance/                 ← 顧客が決めるのはこの置き場所だけ（共有ドライブ推奨） |
| plugins/osi-finance/skills/osi-finance-ar-sync/SKILL.md | 80 | CAIO | `INV-2026-07-016` は 対象月 2026-06 の行（CAIO 550,000）と 2026-07 の行（準備金 1,375,000 / 2,200,000）が |
| plugins/osi-finance/skills/osi-finance-plan/SKILL.md | 39 | CAIO | 実績は勘定科目、計画は計画自身の切り方（CAIO契約売上、コンサル外注、通信費の内訳…）で、 |
| plugins/osi-finance/config/osi-finance-settings.example.md | 239 | 共有ドライブ | 共有ドライブに1つ作り、配下は規定ツリー（00.契約書／01.受領請求書／02.送付請求書／03.経費管理）で固定。 |
| plugins/osi-finance/config/osi-finance-settings.example.md | 244 | 共有ドライブ | \| OSI Finance ルートの場所 \| {{DRIVE_ROOT_LOCATION 例: 共有ドライブ「経理」直下／マイドライブ（要・経理チーム共有）}} \| |
| plugins/osi-finance/docs/導入マニュアル.md | 47 | 共有ドライブ | \| Google Workspace（**共有ドライブ**）＋ デスクトップアプリ \| 必須 \| 台帳・契約書・証憑の保管 \| |
| plugins/osi-finance/docs/導入手順書.md | 25 | 共有ドライブ | \| Google Workspace（**共有ドライブ**推奨） \| 必須 \| 台帳・契約書・証憑の保管 \| 既存契約でも可 \| |
| plugins/osi-finance/docs/導入手順書.md | 114 | 共有ドライブ | >   共有ドライブなら `G:\共有ドライブ\<会社>\{{paths.finance}}` のような形になります |
| plugins/osi-finance/assets/schema/data-layout.yaml | 163 | CAIO | 重複=異常と判定してはいけない。例: INV-2026-07-016 は NITOH の CAIO と準備金2件を1通にまとめたもの。 |
| plugins/osi-core/skills/transcript-router/SKILL.md | 34 | Plaud | - **テキストが貼られていなくても**、「今日の○○の録音を」「さっきの Plaud を」のように |
| plugins/osi-core/skills/transcript-router/SKILL.md | 35 | Plaud | Plaud 録音を指す一言が来ている（→ 下の「Plaud MCP からの取得」で先に本文を確保してから判定） |
| plugins/osi-core/skills/transcript-router/SKILL.md | 37 | Plaud | ## Plaud MCP からの取得（貼り付け不要の入口） |
| plugins/osi-core/skills/transcript-router/SKILL.md | 38 | Plaud | Plaud MCP コネクタ（`list_files` / `get_transcript` 等）が利用可能なら、文字起こしの |
| plugins/osi-core/skills/transcript-router/references/skill-customization.md | 35 | CAIO | - サービス = CAIO |
| plugins/osi-core/skills/getting-started/SKILL.md | 40 | Plaud | 3. 見えているツール名から、繋がっているコネクタを列挙する（AI OSI URI Deploy / AI OSI URI Finance / AI OSI URI Creative / Gmail / Slack / Google Dri |
| plugins/osi-core/skills/getting-started/SKILL.md | 88 | Plaud | \| MoneyForward / DocuSign / Plaud / Obsidian \| 軽い読み取り 1 回 \| 同上 \| |
| plugins/osi-core/skills/getting-started/references/tiers.md | 68 | Plaud | \| osi-sales \| `meeting-minutes` \| slack, box, plaud \| ○ \| 商談議事録を Plaud の文字起こしから自動生成し、Drive の `03_制作・成果物/` に docx として格納した |
| plugins/osi-core/skills/getting-started/scripts/init_kit.py | 31 | CAIO | "CAIO担当", "サポート", "アサイン状態", "次アクション", "次アクション期日", "最終接触日", |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 4 | 共有ドライブ | デプロイを使えるようにする初回セットアップ。**共有ドライブの .env は使わず**、 |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 19 | 共有ドライブ | > 旧版は `.deploy-credentials/.env` にトークンを書き込んでいたが、平文・共有ドライブ同期・ |
| plugins/osi-deploy/skills/setup-deploy-environment/SKILL.md | 25 | 共有ドライブ | （社内手順：共有ドライブ「環境構築キット」参照） |
| plugins/osi-deploy/skills/aws-static-deploy/SKILL.md | 38 | 共有ドライブ | 共有ドライブの `.deploy-credentials/.env` は **任意フォールバック**としてのみ参照する。 |
| plugins/osi-deploy/skills/update-deploy/SKILL.md | 68 | GITHUB_ORG | \| `repo_owner` \| `ai-osi-uri` または個人 username \| 既定は GITHUB_ORG / GITHUB_USERNAME \| |
| plugins/osi-deploy/skills/create-app/SKILL.md | 58 | GITHUB_ORG | **重要:** `GITHUB_ORG` が未設定だと、`github_create_repo_and_push` は `owner_override` を |
| plugins/osi-deploy/skills/create-app/references/drive-record.md | 21 | Notion | Notion のリード一覧に案件が登録されていれば、対応する Drive 案件フォルダが存在する。 |
| plugins/osi-deploy/skills/create-app/references/drive-record.md | 66 | Notion | \| 案件 \| （Notion リード ID / 案件名 / なし） \| |
| plugins/osi-deploy/skills/create-app/references/aws-app-gotchas.md | 54 | 共有ドライブ | 初回 apply 前に **`tf-state-backend` スキル**を呼ぶ（state基盤の作成＋backend.tf差し込み）。既存のローカルstateアプリは同スキルの migrate-existing（`aws_terrafo |
| plugins/osi-deploy/skills/tf-state-backend/SKILL.md | 73 | 共有ドライブ | 6. コード一式＋HANDOFF を共有ドライブへ退避（揮発対策） |
| plugins/osi-deploy/skills/tf-state-backend/SKILL.md | 158 | 共有ドライブ | 復旧時にバケット/キーが分からなくなる**。コード一式を共有ドライブの案件フォルダへ退避する。 |
| plugins/osi-backoffice/skills/contract-docusign-send/SKILL.md | 94 | 共有ドライブ | - **Drive（マウント済み共有ドライブ）**：格納先は `references/storage-and-naming.md` の定義に従う。**このスキルにパスを直書きしない**（組織ごとに違い、移行でも動く）。 |
| plugins/osi-backoffice/skills/contract-docusign-send/_旧版_S3方式_20260817/docusign-and-s3.md | 30 | 共有ドライブ | - **file tools（Mac）**：outputs と共有ドライブのみ書ける。 |
| plugins/osi-backoffice/skills/contract-docusign-send/references/storage-and-naming.md | 3 | 共有ドライブ | 契約の正本は Drive の**契約書フォルダ**（`{契約書ルート}`）。マウント済み共有ドライブに書くと Drive に同期される。 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 4 | Plaud | 商談議事録を Plaud の文字起こしから自動生成し、Drive の `03_制作・成果物/` に docx として格納したうえで、営業管理表（`{{ledgers.sales}}` の `取引先管理` タブ）の最終接触日・最終議事録日・メ |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 19 | Plaud | 自社の営業ワークフローにおいて、Plaud で録音した商談の文字起こしを |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 25 | Plaud | AS-IS では、Plaud で録音した文字起こしを主担当が手で読み込み、 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 35 | Plaud | このスキルなら「今日の○○社の録音を議事録にして」の一言で、Plaud MCP から |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 80 | Plaud | - Plaud MCP から取得した（または貼り付けられた）文字起こしを読み、 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 91 | Plaud | 2. 文字起こしを取得（Plaud MCP で直接取得が基本／貼り付け・Gmail転送・Drive はフォールバック） |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 131 | Plaud | ### 2-A: Plaud MCP で直接取得（プライマリ） |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 133 | Plaud | Plaud MCP コネクタ（ツール名に `plaud` を含む `list_files` / `get_file` / |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 143 | Plaud | 3. `get_note`（Plaud の AI 要約）は **参考情報に留める**。サマリ・次アクションの構造化は |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 144 | Plaud | Step 3 で Claude 自身が全文から行う（Plaud 要約の転記で済ませない）。 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 150 | Plaud | 1. **チャットへの貼り付け**：従来どおり Plaud アプリからのコピペを受け付ける |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 151 | Plaud | 2. **Gmail 転送メール**：Plaud から Gmail に自動転送されている場合、Gmail 検索 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 155 | Plaud | どれも無ければ `AskUserQuestion` で「Plaud の文字起こしを貼り付けてください |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 183 | yourrecord | "todo": "見積もり提案書（yourrecord + CAIO Advanced）を作成", |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 183 | CAIO | "todo": "見積もり提案書（yourrecord + CAIO Advanced）を作成", |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 261 | yourrecord | 例：`2026-07-21 議事録: 見積もり提案書（yourrecord + CAIO Advanced）を自社担当が7/24までに作成` |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 261 | CAIO | 例：`2026-07-21 議事録: 見積もり提案書（yourrecord + CAIO Advanced）を自社担当が7/24までに作成` |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 367 | Plaud | ### Plaud の文字起こしの特徴と対処 |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 416 | Plaud | - **Plaud MCP が 401 / 未認証** → `login` ツールでサインインを促して再試行。直らなければ 2-B へフォールバック |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 417 | Plaud | - **Plaud に該当録音が無い** → 条件を緩めて再検索 → 無ければ貼り付け / Gmail / Drive へフォールバック |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 426 | Plaud | - `references/transcript-parsing.md` — 【共通・正本】Plaud 文字起こしの取得（MCP/フォールバック）・特徴対処・話者推定（session-review / shodan-prep と共有） |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 438 | Plaud | - 「今日の○○社の録音を議事録にして」（← Plaud MCP で直接取得） |
| plugins/osi-sales/skills/meeting-minutes/SKILL.md | 439 | Plaud | - 「Plaud の文字起こしを議事録にして」 |
| plugins/osi-sales/skills/meeting-minutes/references/data-schema.md | 42 | yourrecord | "yourrecord 導入には強い興味", |
| plugins/osi-sales/skills/meeting-minutes/references/data-schema.md | 132 | CAIO | セクションヘッダは赤色（CAIO アクセントレッド）。 |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 1 | Plaud | # Plaud 文字起こしの取得・取り込み（共通・正本） |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 10 | Plaud | ### ① Plaud MCP（プライマリ） |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 12 | Plaud | Plaud MCP コネクタが接続されていれば、ユーザーに貼り付けさせずに直接取得する。 |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 20 | Plaud | \| `get_note` \| Plaud の AI 要約・アクションアイテム — **参考情報に留める**（構造化は必ず全文から） \| |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 31 | Plaud | 従来の Plaud アプリからのコピペ。テキストがそのまま会話に貼られていれば最優先でそれを使う |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 36 | Plaud | Plaud → Gmail の自動転送を設定している運用向け。Gmail 検索（`search_threads`）で |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 46 | Plaud | `AskUserQuestion` で「Plaud の文字起こしを貼り付けてください（または録音名・日付を |
| plugins/osi-sales/skills/meeting-minutes/references/transcript-parsing.md | 51 | Plaud | ## 2. Plaud 文字起こしの特徴と対処 |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 12 | yourrecord | "yourrecord 導入には強い興味。ただし社内データを AI に学習させることへの心理的ハードルが残っている", |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 13 | CAIO | "CAIO 契約は予算的に Advanced (30 万 / 月) が現実的。来月の役員会で諮る方針", |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 14 | CAIO | "次回は 2 週間後、見積もりと CAIO 契約の 6 ヶ月ロードマップを持参して再訪問" |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 18 | yourrecord | {"todo": "見積もり提案書（yourrecord + CAIO Advanced）を作成", "due": "2026-05-13", "owner": "自社担当"}, |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 18 | CAIO | {"todo": "見積もり提案書（yourrecord + CAIO Advanced）を作成", "due": "2026-05-13", "owner": "自社担当"}, |
| plugins/osi-sales/skills/meeting-minutes/assets/example-minutes.json | 19 | yourrecord | {"todo": "yourrecord のセキュリティ FAQ を作成して提供", "due": "2026-05-10", "owner": "自社担当"}, |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 6 | Plaud | Plaud の文字起こしから「初回で握れた／失敗した項目」を抽出し、初回チェックリスト（references/ |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 9 | Plaud | 「Plaud文字起こしから握れた/失敗を抽出して」など、商談の事前準備・初回チェックリストの作成や |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 40 | Plaud | 商談 後 ──▶ EXTRACT モード：Plaud文字起こし → 握れた/失敗を採点 → チェックリストを育てる |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 163 | Plaud | **まず Plaud MCP で直接取得**：コネクタ（`list_files` / `get_transcript` 等）が利用可能なら、 |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 233 | Plaud | - `references/extraction-guide.md` — Plaud 文字起こしの採点基準とチェックリスト更新の型。 |
| plugins/osi-sales/skills/shodan-prep/SKILL.md | 242 | Plaud | - 「◯◯社の Plaud 文字起こし、握れた/失敗を抽出して」 |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 4 | Plaud | 商談 **後** は Plaud 文字起こしから「握れた / 失敗した」を判定する採点軸として使う。 |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 6 | CAIO | > v0 は過去議事録からの抽出前の初版。現状診断シート（CAIO_systems_checklist）の B2 / A1 / A2 / E1 / |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 8 | Plaud | > 高契約率の成功パターン）から組んでいる。代表 3〜5 件の Plaud 文字起こしを投入するたびに、 |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 29 | CAIO | > 酔鯨・FRESH ROOM の失敗は、ここの握り不足から起きた「期待値ズレ」。CAIO は「何でもできる」が |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 71 | CAIO | ### B1. CAIO パッケージ（契約初日に渡すスキル一式）の中身を説明したか |
| plugins/osi-sales/skills/shodan-prep/references/initial-checklist.md | 133 | CAIO | - **握れた状態**：定例（隔週 60 分の CAIO Lab 等）の頻度・参加者・進め方が決まっている。 |
| plugins/osi-sales/skills/shodan-prep/references/extraction-guide.md | 1 | Plaud | # 抽出ガイド：Plaud 文字起こし → 握れた/失敗の採点とチェックリスト更新 |
| plugins/osi-sales/skills/shodan-prep/references/extraction-guide.md | 22 | Plaud | - Plaud 特有のクセ（句読点が少ない・話者ラベルが曖昧・聞き間違い）に注意。数字や固有名は怪しければ |
| plugins/osi-sales/skills/shodan-prep/assets/prep-sheet-template.md | 61 | CAIO | - [ ] B1 CAIOパッケージの説明 |
| plugins/osi-sales/skills/new-lead-registration/SKILL.md | 43 | CAIO | CAIO担当 / サポート / アサイン状態 / 次アクション / 次アクション期日 / 最終接触日 / |
| plugins/osi-sales/skills/new-lead-registration/references/ledger-access.md | 64 | CAIO | CAIO担当 / サポート / アサイン状態 / 次アクション / 次アクション期日 / 最終接触日 / |
| plugins/osi-sales/skills/new-lead-registration/references/ledger-access.md | 79 | CAIO | \| 西 \| CAIO担当・アサイン状態・事業区分 \| |
| plugins/osi-sales/skills/new-lead-registration/scripts/ledger.py | 76 | 共有ドライブ | os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/共有ドライブ/*/osi-profile.md"), |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 3 | CAIO | description: 見積もり・スケジュール入り**詳細提案書（pptx）を単発生成する atomic スキル**。まず storyline-gate で「この相手が、このスコープ・価格・期間で Yes と言う筋」を骨子1枚にして承認を |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 18 | CAIO | 具体的な金額（「初期30万」「月額30万」）／具体的サービス名（CAIO契約・カスタム開発）／スケジュール（「6ヶ月で」「ガント」）／既に面識あり、のいずれかが出ているとき。初回アプローチなら proposal-package の初回ルート |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 51 | CAIO | 骨子の③④をもとに提案の骨格を組む。自社でよく使うサービス構成パターン・CAIO の3フェーズモデル・価格帯は `references/service-catalog.md` を参照（「従う型」ではなく、骨子に合わせて選ぶ既存解）。 |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 72 | CAIO | > 例：CAIO契約 20万円/月（6ヶ月契約）／初期費用 0円（オンボーディング含む） |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 78 | CAIO | 骨子と価格・スケジュールの素材が揃ったら、**`deck-composition` スキルを呼んで slide-plan.md（スライド順・各 Action title・1メッセージ・載せる証拠）を作る。** 枚数・順序は骨子から導く。よく |
| plugins/osi-sales/skills/proposal-estimate/SKILL.md | 139 | CAIO | - `references/service-catalog.md` — サービス構成パターン・CAIO 3フェーズ・価格帯・よく使うスライド構成（**外部版には同梱しない。無ければ骨子と過去提案から組む**。自社の商品カタログを連結フォルダ |
| plugins/osi-sales/skills/proposal-estimate/references/brand-design.md | 3 | CAIO | CAIO_サービス紹介資料.pptx から抽出したブランドカラー。実際の描画は pptx / pptx-custom スキルに従い、配色はここを正本にする。 |
| plugins/osi-sales/skills/pr-times-article/SKILL.md | 126 | CAIO | - 契約形態（CAIO契約、開発契約等） |
| plugins/osi-sales/skills/pr-times-article/SKILL.md | 209 | CAIO | ← CAIOサービスを通じて何を支援しているかを端的に |
| plugins/osi-sales/skills/pr-times-article/SKILL.md | 223 | CAIO | ## CAIOサービスについて |
| plugins/osi-sales/skills/pr-times-article/SKILL.md | 262 | CAIO | ## 自社の「CAIO」サービスについて |
| plugins/osi-sales/skills/pr-times-article/SKILL.md | 332 | CAIO | - サービスの説明 → 「CAIOサービスについて」セクションに集約 |
| plugins/osi-sales/skills/pr-times-article/assets/sample-article.md | 3 | CAIO | ＡＩ　ｏｓｉ‐ｕｒｉ株式会社（代表取締役：渚 有瓶、本社：東京都港区）は、パーソナルジム「サンプル」を運営する株式会社サンプル（代表：山田太郎、本社：東京都◯◯区）に対し、「CAIO」サービスを通じた集客支援を行っています。Instagra |
| plugins/osi-sales/skills/pr-times-article/assets/sample-article.md | 19 | CAIO | ## CAIOサービスについて |
| plugins/osi-sales/skills/pr-times-article/assets/sample-article.md | 21 | CAIO | AI OSI URIが提供する「CAIO」サービスは、クライアントの課題に対してAIを活用し、高速で成果物を形にする伴走型支援です。隔週の定例で要望を聞き取り、次の定例までに動くものを見せてフィードバックを回すサイクルで進めます。 |
| plugins/osi-sales/skills/pr-times-article/assets/sample-article.md | 65 | CAIO | ## AI OSI URIの「CAIO」サービスについて |
| plugins/osi-sales/skills/proposal-package/SKILL.md | 173 | yourrecord | \| 「見積もり」「価格」「料金」「○○万円」「○○円」「ガントチャート」「スケジュール入り」「実施計画」「契約」「CAIO 契約」「yourrecord 導入提案」「フェーズ別計画」など金額・期間・具体サービス名を含む \| **estima |
| plugins/osi-sales/skills/proposal-package/SKILL.md | 173 | CAIO | \| 「見積もり」「価格」「料金」「○○万円」「○○円」「ガントチャート」「スケジュール入り」「実施計画」「契約」「CAIO 契約」「yourrecord 導入提案」「フェーズ別計画」など金額・期間・具体サービス名を含む \| **estima |
| plugins/osi-sales/skills/proposal-package/SKILL.md | 280 | yourrecord | - 提案サービス（yourrecord / CAIO / カスタム開発 等）— ユーザー発話から拾う、不足なら estimate 側が壁打ちで詰める |
| plugins/osi-sales/skills/proposal-package/SKILL.md | 280 | CAIO | - 提案サービス（yourrecord / CAIO / カスタム開発 等）— ユーザー発話から拾う、不足なら estimate 側が壁打ちで詰める |
| plugins/osi-sales/skills/proposal-package/SKILL.md | 578 | Plaud | デモ後に Plaud 文字起こしが渡されたら： |
| plugins/osi-sales/skills/session-review/SKILL.md | 56 | Plaud | - **必須**: 伴走セッションの文字起こし（Plaud 等。話者ラベル付き／なしの両対応）。 |
| plugins/osi-sales/skills/session-review/SKILL.md | 57 | Plaud | - **取得はまず Plaud MCP から**：コネクタ（`list_files` / `get_transcript` 等）が |
| plugins/osi-sales/config/osi-sales-settings.example.md | 12 | Notion | 案件情報の**正本**。Notion のリード一覧は 2026-07 に、Google スプレッドシート版は |
| plugins/osi-sales/config/osi-sales-settings.example.md | 30 | CAIO | CAIO担当 / サポート / アサイン状態 / 次アクション / 次アクション期日 / 最終接触日 / |
| plugins/osi-sales/config/osi-sales-settings.example.md | 96 | Notion | - 旧NotionのIDと現在のフォルダ番号は途中から乖離している。 |
| plugins/osi-mobile-deploy/skills/deploy-mobile-app/SKILL.md | 167 | GITHUB_ORG | \| GITHUB_ORG \| `ai-osi-uri` / `personal` \| `create-app` の `USE_ORG` 判定に準拠 \| |
| plugins/osi-creative/skills/vp-corporate-card/SKILL.md | 9 | Plaud | connector_prose_ok:  # Plaud は「音声の入手経路の例」。このスキルが呼ぶわけではない |
| plugins/osi-creative/skills/vp-corporate-card/SKILL.md | 39 | Plaud | \| **A. 音声1本**（既定） \| 社長・担当が60〜90秒喋った音声／Plaud文字起こし \| 材料を集める時間がないとき。「1分喋ってください」で済む \| |
| plugins/osi-creative/skills/ai-video-production/references/hook-insight.md | 57 | CAIO | この一言だと、B4（会社にひとりAIの意思決定者を置く＝CAIO）がそのまま答えになる。 |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 135 | 共有ドライブ | { "name": "Excel管理簿", "where": "営業共有ドライブ" } |
| plugins/osi-docs/skills/business-flow-asis-tobe/references/data-schema.md | 167 | Notion | \| `name`    \| yes  \| ドキュメント名（例：「契約書ドラフト Word」「Notion 商談 DB」） \| |
| plugins/osi-docs/skills/pptx-custom/exec-deck-patterns.md | 11 | CAIO | - ✅「初期費用ゼロのCAIO契約なら、3ヶ月で投資回収できる」 |
| plugins/osi-docs/skills/financial-model-3statement/SKILL.md | 46 | CAIO | {"名前":"CAIO ベーシック","掛け算":[ |
| plugins/osi-docs/skills/architecture-proposal/SKILL.md | 12 | yourrecord | ※ 自社サービス（CAIO / yourrecord 等）の新規営業・初回提案・見積提案は別スキル |
| plugins/osi-docs/skills/architecture-proposal/SKILL.md | 12 | CAIO | ※ 自社サービス（CAIO / yourrecord 等）の新規営業・初回提案・見積提案は別スキル |
| plugins/osi-docs/skills/architecture-proposal/scripts/deck_helpers.py | 11 | CAIO | # ---- ブランド配色（CAIO資料準拠 / EDIT可） ---- |
| plugins/osi-docs/skills/deck-composition/SKILL.md | 106 | CAIO | - ❌「コア事業の説明」→ ✅「では本丸の CAIO 事業を——仕組み・価格・現状を見ていく」 |
| plugins/osi-docs/skills/deck-composition/SKILL.md | 114 | CAIO | 複数スライドで使う用語・略語（CAIO, ARR, NPS 等）は、**初出のスライドで**定義する。5枚後に「Xとは」を置かない。定義はサブタイトルにインラインで入れるか、使い始める前に定義スライドを1枚置く。 |
