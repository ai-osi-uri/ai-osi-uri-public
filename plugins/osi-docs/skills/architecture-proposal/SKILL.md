---
name: architecture-proposal
description: >
  クライアントの既存構想（グランドデザイン／ADR／要件資料）を読み込み、AI OSI URI が
  デリバリーパートナーとして「クラウド（GCP/AWS）上にどう実装するか」を示す技術・
  アーキテクチャ提案書（pptx）を作るスキル。インフラ構成図（公式アイコン調・担当色つき）、
  段階ロードマップ（v1/v2/v3）、スコープ定義、課題→解→効果のトレーサビリティ、役割分担、
  PoC合格基準、見積もりまでを一気通貫で作る。
  「○○の設計資料を読んで実装提案を作って」「アーキテクチャ提案」「PoC提案」「GCP/AWSの
  構成図つき提案」「段階的に作る技術提案」「既存構想を実装に落とす提案」「クラウド移行/
  構築の提案書」などで必ず発動する。設計資料(PDF/MD)が共有された提案依頼でも発動する。
  ※ 自社サービス（CAIO / yourrecord 等）の新規営業・初回提案・見積提案は別スキル
  （initial-proposal / proposal-estimate / proposal-package）の担当。本スキルは「相手の設計を
  クラウド上に実装する技術・デリバリー提案」専用。
requires_connectors:
  - server: notion
    provision: user-install
  - server: box
    provision: user-install
---

# 技術・アーキテクチャ提案スキル

相手企業がすでに持つグランドデザイン／ADR／要件を読み込み、それを**クラウド上に動く形で
実装する道筋**を提案するためのスキル。営業提案（自社サービス売り込み）とはカテゴリが違う。
価格より、**課題→解→効果・スコープ・段階ロードマップ・アーキテクチャ・役割分担・PoC合格基準**
が主役で、起点は「自社紹介」ではなく「相手資料の読解」。

## いつ使うか
- 相手の設計資料（PDF/MD/URL）を渡され「これを実装する提案を作って」と言われたとき
- アーキテクチャ図つきの技術提案、PoC提案、段階的（v1/v2/v3）な実装提案
- GCP/AWS など特定クラウドでの構築・移行提案

自社サービスの初回営業・見積は initial-proposal / proposal-estimate を使うこと。

## ワークフロー
1. **資料読解**：相手の設計資料を読む（PDFは pypdf でテキスト抽出）。目的・課題・確定事項
   （アーキ/ADRが済か）・採用技術スタックを把握する。
2. **最初に確認（AskUserQuestion）**：相手と自社の立場（元請/下請/協働）／対象クラウド
   （GCP/AWS/Azure）／段階提案にするか（v1/v2/v3）／役割分担の方針（誰がどこ）／価格の出し方。
3. **理解の表明ドラフト**：references/structure.md の「目的ファースト」に従い、相手の業務課題→
   目指す状態→だから本取組、の順で骨子を書く。固有名詞から始めない。
4. **構成設計**：references/structure.md の標準構成に沿って各章の中身を決める（課題→解→効果、
   vスコープ、段階アーキ、役割、利用シーン/UC、進め方、スケジュール、体制、見積、前提）。
5. **インフラ構成図を生成**：scripts/arch_diagram.py をコピーして案件に合わせ編集し、段階ごとに
   3回レンダリング（下記「アーキ図の作り方」）。
6. **pptx生成**：scripts/deck_helpers.py を import して各スライドを組む（下記「pptxの作り方」）。
7. **QA**：references/structure.md の QA 手順（markitdown＋画像化＋サブエージェント点検）を回す。
8. （任意）Drive 格納・Notion 反映は proposal-package の流儀に合わせる。v1モック画面＋Vercel
   公開が要るなら deploy-app と連携。

## アーキ図の作り方（scripts/arch_diagram.py）
- これは**コピーして編集するテンプレート**。完全自動の汎用エンジンにしていないのは、任意
  アーキの自動レイアウト／配線が壊れやすく、既知の良い型を編集する方が速く確実だから。
- ノードは `node(x,y,w,h, owner, icon, l1, l2="", intro=段階)`。`owner` は担当色（RED=自社/構築、
  BLUE=相手社/AI設計、GRAY=発注元）で**箱の背景が薄くその色になる**。`icon` の種類と GCP↔AWS
  対応は references/cloud-services.md。`intro` はそのコンポーネントが登場する段階（1/2/3）。
- 段階表示：`STAGE` を 1→2→3 で渡して3回レンダリングすると、`intro>STAGE` は自動でグレーアウト、
  `intro==STAGE` は緑「NEW」バッジが付く。これで「v1/v2/v3で何が増えるか」を3枚で見せる。
  ```bash
  for s in 1 2 3; do python3 arch_diagram.py $s; done
  for s in 1 2 3; do soffice --headless --convert-to png arch_v$s.svg; done
  ```
- 配線は `oconn([(x1,y1),...], label=..., intro=段階)`。クラウド正準を守る（AWS流のpublic/private
  subnet を持ち込まない。GCPは Cloud Run＋Serverless VPC Access＋Cloud NAT＋Google Front End）。

## pptxの作り方（scripts/deck_helpers.py）
- `from deck_helpers import *` → `prs=new_deck()`、各スライドは `s=slide(prs)` で作り、`head/rect/
  txt/chip/pagenum/add_image` で組む。色は AIOSI/PARTNER/CLIENT（担当）と DARK/RED/LIGHT/LRED 等。
- アーキ図は `add_image(s, "arch_v1.png")` で各段階スライドに貼る。
- 構成と作法は references/structure.md に従う（特に：課題→解→効果の対応、略語の定義、
  vスコープを各1枚、役割の立て付け、箇条書きの独立）。

## 参照
- references/structure.md … 標準構成・必ず守る作法・QA手順
- references/cloud-services.md … アイコン種別・GCP↔AWS対応・GCP固有の注意
- scripts/arch_diagram.py … 段階対応インフラ構成図テンプレート
- scripts/deck_helpers.py … pptx共通ヘルパー
