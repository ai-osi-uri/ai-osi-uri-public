# 導入の段（tiers）

> `python3 scripts/build_tiers.py` で `requires_connectors` から自動生成。手で編集しない。
> 段の意味：**0** は Plugins からインストールするだけ／**1** は Claude の Connectors で純正コネクタ（Gmail・Drive・Slack・Calendar・MoneyForward 等）を繋ぐ／**2** は AI OSI URI Deploy・Finance・Creative などの自社 MCP を入れて鍵を設定する。
> 「公開」列は外部版（`build_external.py`）に含まれるか。

## 0 段目：入れた瞬間に動く（コネクタ不要） — 40 本

| プラグイン | スキル | 必要なコネクタ | 公開 | 何をする |
|---|---|---|---|---|
| osi-core | `getting-started` | — | ○ | スキルを入れた直後の「はじめて」を、会話 1 回で終わらせる入口スキル |
| osi-core | `research-verifier` | — | ○ | 調査結果、営業リスト、提案書、事業計画、記事などに含まれる事実主張を、作成時の推論から独立して主張単位で再検証する横断品質ゲート |
| osi-deploy | `app-builder-container-export` | — | 内部 | 【コマンド専用・自動発火しない】任意スタックのフルスタックアプリ（フロント +自前バックエンド + DB）を、オンプレ App Builde… |
| osi-deploy | `app-builder-export` | — | 内部 | 【コマンド専用・自動発火しない】アプリ仕様を、オンプレ AppBuilder（ソブリン推論筐体）が取り込める App Bundle（.app… |
| osi-deploy | `app-manual` | — | ○ | 公開したアプリの「使い方マニュアル」を、実装（ルート・画面のラベル・サーバーアクション・メール文面・認証方式）から起こして pptx で作る… |
| osi-deploy | `app-smoke-test` | — | ○ | デプロイ済みの URL を curl で叩いて HTTP レベルの動作確認をする |
| osi-deploy | `aws-static-deploy` | — | ○ | GitHub に push 済みの静的サイト（HTML / Vite / Next.js export）を S3 + CloudFront … |
| osi-deploy | `harness-init` | — | ○ | 生成するリポに「ハーネスエンジニアリング」の最小構成（AGENTS.md /CLAUDE.md・init.sh・claude-progres… |
| osi-deploy | `nextjs-pdf-export` | — | 内部 | Next.js（App Router）+ Vercel サーバレスで **日本語フォント埋め込み済み PDF** を出すAPI ルートを構築… |
| osi-deploy | `scroll-3d-website` | — | ○ | Build premium 3D scroll-animated websites end to end — Next.js setup, … |
| osi-deploy | `setup-deploy-environment` | — | ○ | デプロイを使えるようにする初回セットアップ |
| osi-deploy | `supabase-set-auth-url` | — | ○ | Supabase の Auth 設定（Site URL / Redirect URLs）を本番デプロイ後の URL に更新する |
| osi-docs | `business-flow-asis-tobe` | — | ○ | 任意の業態・客先について、業務フローの AS-IS（現状）と TO-BE（将来像）を定義し、ステップごとのスイムレーン図を含む詳細なpptx… |
| osi-docs | `business-plan-builder` | — | ○ | 新規事業・新会社の「事業計画一式」を作る唯一の窓口（オーケストレータ） |
| osi-docs | `company-financial-report` | — | 内部 | 対象企業（主に上場企業）の「業績・財務分析レポート」を、Web一次情報の調査からWord(docx)納品まで一気通貫で作るスキル |
| osi-docs | `deck-composition` | — | ○ | 承認済みの骨子（storyline.md）を、スライドの「構成」＝枚数・順序・各スライドの主張（Action title）・1スライド1メッ… |
| osi-docs | `financial-model-3statement` | — | ○ | 事業計画の「財務3表フル連動モデル（Excel）」を作る atomic スキル |
| osi-docs | `network-diagram-package` | — | ○ | 確認済みの `network-source.json` から、物理構成図、論理構成図、接続表、機器一覧、BOM Excel、未確定事項一覧を… |
| osi-docs | `storyline-gate` | — | ○ | 資料（提案書・スライド・事業計画・社内合意資料 など）を「描き始める前」に、伝えたいこと＝コアメッセージと、そこへ運ぶ最小の論理＝骨子を1枚… |
| osi-docs | `wiring-diagram-intake` | — | ○ | 手描きのネットワーク配線図、ホワイトボード、現場写真、既存図面を読み取り、部屋、ラック、機器、ポート、ケーブル、回線、電源、注記を構造化した… |
| osi-docs | `wiring-diagram-package` | — | ○ | 手描き配線図や現場写真の受領から、画像補正、構造化抽出、段階的なユーザー確認、必要な型番調査、物理・論理ネットワーク構成図、接続表、BOM、… |
| osi-finance | `osi-finance-console` | — | ○ | OSI Finance のローカルコンソール（ブラウザで開く台帳ビュー）の入口 |
| osi-finance | `osi-finance-plan` | — | ○ | OSI Finance の「計画（事業計画）」を読み解いて答えるスキル |
| osi-marketing | `course-outline` | — | ○ | オンライン講座、社内研修、顧客教育プログラムについて、対象者と前提知識、測定可能な学習成果、評価課題から逆算して、モジュール、レクチャー、演… |
| osi-marketing | `form-outreach-autopilot` | — | ○ | Webフォームへの営業送信を、人の手を最小化して自走させるオーケストレータ・スキル（osi-marketing の送信フロント） |
| osi-marketing | `funnel-design` | — | ○ | 商品コンセプトとペルソナを基に、認知、関心、比較、商談、購入、導入、継続、推奨までの顧客導線を、オファー、チャネル、コンテンツ、担当、計測イ… |
| osi-marketing | `media-placement-map` | — | ○ | 自社/クライアントの製品を「どのランキング・比較・ポータルサイトに載せるか」を決めるための、掲載先の洗い出しと陣取り（占有マップ）調査を行う… |
| osi-marketing | `outreach-list-build` | — | ○ | アウトバウンド営業/マーケの「ターゲット企業リスト」を、自社製品の情報を起点に作るスキル（osi-marketing の収集フロント） |
| osi-marketing | `persona-design` | — | ○ | 顧客インタビュー、商談記録、問い合わせ、アクセス解析、市場調査などの根拠から、購買・利用行動の違いが説明できる実用的なペルソナとカスタマージ… |
| osi-marketing | `product-concept` | — | ○ | 検証済みの顧客課題とペルソナから、価値提案、利用場面、差別化、提供範囲、収益仮説、成功指標を一枚の商品コンセプトへまとめるスキル |
| osi-marketing | `webinar-plan` | — | ○ | ウェビナーの対象者、参加後の変化、タイトル、集客、申込ページ、登壇構成、分単位の進行、デモ、質疑、CTA、フォローアップ、計測までを一式で設… |
| osi-meta | `marketplace-sync` | — | 内部 | ローカル Claude で更新したスキルを GitHub のマーケットプレイスリポ（ai-osi-uri/ai-osi-uri-plugin… |
| osi-mobile-deploy | `flutter-swift-parity-port` | — | ○ | 既存の Flutter アプリを SwiftUI ネイティブに移行するときだけ使う 5フェーズの移植ワークフロー |
| osi-mobile-deploy | `mobile-app-smoke-test` | — | ○ | ローカルビルドした IPA / AAB を Simulator / Emulatorで起動してクラッシュを検知する軽量スモークテスト |
| osi-sales | `champion-strategy` | — | ○ | 法人営業で、公開調査や面談情報から社内推進者候補と関係者を整理し、相手が自社内で提案を説明・合意形成できる状態までの戦略を設計するスキル |
| osi-sales | `decision-maker-research` | — | ○ | 法人営業や提案準備のために、対象企業の公開情報から経営課題、DX施策、意思決定構造、導入障壁、評価基準、社内推進者候補を調査し、根拠付きの決… |
| osi-sales | `persuasion-document` | — | ○ | 企業調査、決裁構造、社内推進戦略、提案内容を統合し、顧客が社内判断に使える根拠付き説得文書と決裁者向けワンページを作成するスキル |
| osi-sales | `persuasion-package` | — | ○ | 法人営業の重要提案について、対象企業の調査、決裁構造分析、社内推進戦略、説得文書、決裁者向けワンページ、独立ファクトチェックまでを一括で統括… |
| osi-sales | `proposal-estimate` | — | ○ | 見積もり・スケジュール入り**詳細提案書（pptx）を単発生成する atomic スキル** |
| osi-sales | `proposal-self-review` | — | ○ | 顧客向けの提案書・デモ・アプリ・資料などの「成果物」をユーザーに見せる前に、必ず通す自己レビューのゲート |

## 1 段目：Claude の純正コネクタを繋げば動く（OAuth でワンクリック） — 18 本

| プラグイン | スキル | 必要なコネクタ | 公開 | 何をする |
|---|---|---|---|---|
| osi-core | `transcript-router` | plaud | ○ | 会議・商談・伴走セッションの文字起こしや長文メモが貼り付けられ、短い指示（「まとめて」「本質とTODOを出して」「議事録にして」「論点を出し… |
| osi-docs | `architecture-proposal` | box | ○ | クライアントの既存構想（グランドデザイン／ADR／要件資料）を読み込み、自社がデリバリーパートナーとして「クラウド（GCP/AWS）上にどう… |
| osi-finance | `osi-finance-ar-sync` | money-forward | ○ | OSI Finance の経理で、請求管理台帳の「請求済」「入金済」取引と、会計SaaS（v1=マネーフォワード クラウド会計）の仕訳を突合… |
| osi-finance | `osi-finance-dashboard` | money-forward, cowork | ○ | OSI Finance の「会計ダッシュボード」を Cowork のライブ・アーティファクトとして生成するスキル |
| osi-finance | `osi-finance-feed-recon` | money-forward | ○ | OSI Finance の経理で、マネーフォワード クラウド会計の「連携明細（未仕訳）」を棚卸しして整理するスキル（連携明細の入口整理役） |
| osi-finance | `osi-finance-mf-sync` | money-forward | ○ | OSI Finance の経理で、支払管理台帳の支払済取引と、会計SaaS（v1=マネーフォワード クラウド会計）の仕訳を突合し、計上漏れ・… |
| osi-finance | `osi-finance-monthly` | money-forward | ○ | OSI Finance の月次経理クローズを進めるオーケストレータ・スキル |
| osi-finance | `osi-finance-payment-detect` | superhuman | ○ | 毎朝、受領請求書（AP）の取りこぼしを検出する日次スキル |
| osi-finance | `osi-finance-payment-intake` | superhuman, money-forward | ○ | 受領請求書（AP）を「①受領・格納 → ②読取・科目/税区分判定 → ③支払管理台帳に支払予定を起票→ ④振込情報の整形提示」まで進めるオン… |
| osi-finance | `osi-finance-receipt-intake` | money-forward, drive-fs, superhuman | ○ | OSI Finance の経費レシート取込 |
| osi-knowledge | `calendar-free-time` | google-calendar | ○ | Google Calendarから空き時間を取得し、コンパクトなフォーマットで表示するスキル |
| osi-meta | `skill-lifecycle` | cowork | 内部 | スキルそのものを管理するライフサイクル・オーケストレータ |
| osi-sales | `meeting-minutes` | slack, box, plaud | ○ | 商談議事録を Plaud の文字起こしから自動生成し、Drive の `03_制作・成果物/` に docx として格納したうえで、営業管理… |
| osi-sales | `new-lead-registration` | slack | ○ | 新規リード（見込み案件）を営業管理表（`{{ledgers.sales}}` の `取引先管理` タブ）に1行追加し、`{{paths.pr… |
| osi-sales | `pr-times-article` | slack | ○ | 協業実績・事例紹介をPR TIMES記事として作成するスキル |
| osi-sales | `proposal-package` | slack, plaud | ○ | リードに対する提案準備を一気通貫で行う**唯一の窓口（オーケストレータ）スキル** |
| osi-sales | `session-review` | plaud | ○ | 「AI伴走（Cowork / AI 導入支援）セッション」の文字起こしから、振り返りレビューを構造化して生成するスキル |
| osi-sales | `shodan-prep` | box, plaud, web-fetch | ○ | 商談を「準備」と「振り返り」の両面で支援するスキル |

## 2 段目：自社 MCP（Deploy / Finance / Creative 等）と鍵が要る — 55 本

| プラグイン | スキル | 必要なコネクタ | 公開 | 何をする |
|---|---|---|---|---|
| osi-backoffice | `contract-docusign-send` | docusign, ai-osi-uri-finance | ○ | バックオフィス向け「契約書を内容チェックして DocuSign で署名依頼を送る」スキル |
| osi-backoffice | `meishi-generator` | cowork, AI_OSI_URI_Deploy | 内部 | 名刺（表面）のラクスル入稿用PDFを自動生成するスキル |
| osi-creative | `ai-video-production` | ai-osi-uri-creative | ○ | AI動画を作るオーケストレータ（ディスパッチャ）スキル |
| osi-creative | `live-ugc-reel-edit` | ai-osi-uri-creative | 内部 | インフルエンサー等の「実写UGCクリップ（商品を飲む・使う・作る縦型素材）」を、参照リールの構成と“文字の遊び”に寄せて編集し、動く日本語テ… |
| osi-creative | `music` | ai-osi-uri-creative | ○ | 動画のBGM・音楽を担う atomic スキル（narration と同格の能力アトミック） |
| osi-creative | `narration` | ai-osi-uri-creative | ○ | AI音声ナレーション（日本語特化）を作る atomic スキル |
| osi-creative | `vp-character-action` | ai-osi-uri-creative | ○ | AI動画の「キャラ一貫アクション」メソッド |
| osi-creative | `vp-core` | ai-osi-uri-creative | ○ | AI動画制作の「共通インナー」atomicスキル |
| osi-creative | `vp-corporate-card` | ai-osi-uri-creative | ○ | AI動画の「企業の動画名刺」メソッド |
| osi-creative | `vp-corporate-narrated` | ai-osi-uri-creative | ○ | AI動画の「ナレ付き企業動画」メソッド |
| osi-creative | `vp-moveboard` | ai-osi-uri-creative | ○ | AI動画の「1枚の画像をカメラの動きで魅せる」メソッド |
| osi-creative | `vp-personal-intro` | ai-osi-uri-creative | ○ | AI動画の「個人の自己紹介動画」メソッド |
| osi-creative | `vp-seamless-journey` | ai-osi-uri-creative | ○ | AI動画の「連続する1本のカメラ・ジャーニー」を作るメソッド |
| osi-deploy | `app-concierge` | AI_OSI_URI_Deploy | 内部 | 非エンジニアが「自分たちのアプリ・サイト・データ」の**現状を確認したい /不具合を訴えたい**ときの入口 |
| osi-deploy | `aws-route53` | AI_OSI_URI_Deploy | ○ | 既存の Route 53 ホストゾーンに DNS レコードを足す・直す |
| osi-deploy | `create-app` | AI_OSI_URI_Deploy, aws-api, slack | ○ | 自社が Cowork から**アプリを新規に作って公開する**ための唯一のオーケストレータ |
| osi-deploy | `deploy-preflight` | AI_OSI_URI_Deploy | ○ | デプロイを実行する **前** に、失敗しやすい前提条件を機械チェックするゲート |
| osi-deploy | `desktop-release-monitor` | AI_OSI_URI_Deploy | ○ | GitHub Actions の workflow run を polling し、全 OS（Windows/Mac/Linux）のビルド完… |
| osi-deploy | `electron-scaffold-and-build` | AI_OSI_URI_Deploy | ○ | Electron の scaffold 生成 + electron-builder 設定注入 + GitHub Actions の matr… |
| osi-deploy | `gcp-ops` | AI_OSI_URI_Deploy | ○ | Cowork から GCP を REST 経由で操作する（gcp_health_check / gcp_api / bq_query） |
| osi-deploy | `gh-create-repo-and-push` | AI_OSI_URI_Deploy | ○ | ローカル作業ディレクトリを新規 GitHub リポジトリに作って push する |
| osi-deploy | `local-project-output` | AI_OSI_URI_Deploy | 内部 | アプリを **クラウドに出さず、ローカルフォルダに runnableなプロジェクト一式として書き出す** |
| osi-deploy | `lovable-payments-golive` | Lovable, claude-in-chrome | ○ | **Lovable** で作られたアプリの内蔵決済（seamless Payments / Stripe）を、有効化からGo Live（本番… |
| osi-deploy | `supabase-multitenant-rls` | AI_OSI_URI_Deploy | 内部 | Supabase + Next.js のマルチテナント SaaS に **Row Level Security 一式** を SQLマイグレ… |
| osi-deploy | `switch-to-live-mode` | AI_OSI_URI_Deploy | ○ | デプロイ済みアプリの Stripe を **テストモードから本番（Live）に切り替える** |
| osi-deploy | `tf-state-backend` | AI_OSI_URI_Deploy, aws-api | ○ | Terraform state を、揮発する作業フォルダではなく自社 AWS の共有 S3 バケット（+DynamoDB ロック）で一元管理… |
| osi-deploy | `update-deploy` | AI_OSI_URI_Deploy, aws-api, cowork, computer-use | ○ | 既にデプロイ済みの **Web / SaaS アプリ（Vercel / AWS）** を、ソース最新化 → 局所修正→ push → 自動再… |
| osi-deploy | `vercel-connect-and-deploy` | AI_OSI_URI_Deploy | ○ | GitHub に push 済みのリポを Vercel に接続し、環境変数を設定して初回本番デプロイを実行する |
| osi-docs | `nda-creation` | slack, ai-osi-uri-sales | 内部 | 機密保持契約書（NDA）を雛形から自動作成するスキル |
| osi-docs | `pptx-custom` | ai-osi-uri-creative | ○ | 社内体裁（ブランド配色・レイアウト規約）で .pptx を描画/整形する**描画エンジン**スキル |
| osi-finance | `osi-finance-bank-recon` | AI_OSI_URI_Finance, drive-fs | ○ | OSI Finance の経理で、ネットバンキングの入出金明細CSVと台帳を突合し、入金（AR）・支払（AP）の実績を裏取りするスキル（BA… |
| osi-finance | `osi-finance-connect` | claude-in-chrome, AI_OSI_URI_Finance, money-forward | ○ | AI OSI URI Finance 拡張（請求管理台帳の読み書き＋MoneyForwardクラウド請求書ポーリング）の **OAuth 接… |
| osi-finance | `osi-finance-contract-draft` | AI_OSI_URI_Finance, drive-fs | ○ | OSI Finance の契約書作成・雛形管理スキル（コンソールの中核パートナー） |
| osi-finance | `osi-finance-contract-intake` | gmail, ai-osi-uri-finance | ○ | OSI Finance の請求業務の起点 |
| osi-finance | `osi-finance-freee-sync` | AI_OSI_URI_Finance, drive-fs | ○ | OSI Finance の経理で、freee 会計からエクスポートした仕訳CSVと台帳（請求管理台帳・支払管理台帳）を突合し、売上(AR)・… |
| osi-finance | `osi-finance-invoice` | AI_OSI_URI_Finance, gmail, claude-in-chrome, plaud | ○ | OSI Finance の月次請求書発行 |
| osi-finance | `osi-finance-journal` | AI_OSI_URI_Finance | ○ | OSI Finance の内部仕訳帳（仕訳台帳）に、台帳からローカルで仕訳を生成・記帳するスキル（v4 の中核） |
| osi-finance | `osi-finance-setup` | money-forward, gmail, superhuman, ai-osi-uri-finance | ○ | OSI Finance（請求AR・支払APの経理自動化）を新しい組織・Cowork に初回セットアップするオーケストレータ・スキル |
| osi-knowledge | `obsidian-knowledge-capture` | obsidian | ○ | Obsidian vault（{{paths.vault}}）に会話・思考・気づき・調査結果を自律的に保存・整理するスキル |
| osi-knowledge | `obsidian-knowledge-consult` | obsidian | ○ | Obsidian vault（{{paths.vault}}）に蓄積されたユーザー独自の知識を引き出し、回答の文脈に組み込むスキル |
| osi-mobile-deploy | `android-play-deploy` | AI_OSI_URI_Deploy | ○ | Android AAB を Google Play Internal Track にアップロードする |
| osi-mobile-deploy | `apiv2-callable-iam-gotchas` | AI_OSI_URI_Deploy | ○ | Firebase Cloud Functions v2 の callable がクライアントから呼べないときの復旧 |
| osi-mobile-deploy | `deploy-mobile-app` | AI_OSI_URI_Deploy, cowork, computer-use, ai-osi-uri-creative | ○ | ネイティブモバイルアプリ（iOS = SwiftUI / Android = Kotlin + Jetpack Compose）を新規に作っ… |
| osi-mobile-deploy | `firestore-bulk-index-sync` | AI_OSI_URI_Deploy | ○ | `firebase deploy --only firestore:indexes` が index limit / 409 already… |
| osi-mobile-deploy | `ios-appstore-release` | AI_OSI_URI_Deploy, slack | 内部 | TestFlight にビルドが上がった **後** の iOS リリース管理 |
| osi-mobile-deploy | `ios-sim-auth-backdoor` | AI_OSI_URI_Deploy | 内部 | iOS Simulator で Firebase Auth のサインインを通す 2 本立て |
| osi-mobile-deploy | `ios-testflight-deploy` | AI_OSI_URI_Deploy | ○ | fastlane + altool で iOS ビルドを TestFlight にアップロードする |
| osi-mobile-deploy | `mobile-app-scaffold` | AI_OSI_URI_Deploy | ○ | Golden Template（SwiftUI + Jetpack Compose、Firebase / CI / fastlane 込み）… |
| osi-mobile-deploy | `mobile-crash-triage` | AI_OSI_URI_Deploy | ○ | TestFlight / Play に配信済みのビルドがクラッシュしたとき、ログを取得・シンボリケートして原因候補と修正案を出す |
| osi-mobile-deploy | `mobile-firebase-setup` | AI_OSI_URI_Deploy | ○ | モバイルアプリ用の Firebase プロジェクトを作成し、iOS / Android アプリを追加してconfig を GitHub Se… |
| osi-mobile-deploy | `mobile-icon-generator` | nano-banana, ai-osi-uri-creative | ○ | 1枚の 1024x1024 画像から iOS AppIcon と Android mipmap の全サイズを一括生成する |
| osi-mobile-deploy | `mobile-secrets-sync` | AI_OSI_URI_Deploy, cowork | ○ | モバイル配信に必要な GitHub Actions Secrets（証明書 / ASC キー / keystore / Play SA/ F… |
| osi-mobile-deploy | `mobile-update-deploy` | AI_OSI_URI_Deploy, cowork, computer-use | ○ | 既存のネイティブモバイルアプリを修正して再配信する（修正 → push → CI 監視 →TestFlight / Play Interna… |
| osi-mobile-deploy | `xcodegen-project-regen` | AI_OSI_URI_Deploy | ○ | xcodegen 管理の iOS プロジェクトで、pull 後に「Missing package product'FirebaseCore'… |
| osi-sales | `discussion-prep` | obsidian | ○ | 「方向性ディスカッション（経営メンバーとの壁打ち）」に丸腰で臨まないための準備スキル |
