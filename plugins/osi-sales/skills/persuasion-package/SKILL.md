---
name: persuasion-package
description: 法人営業の重要提案について、対象企業の調査、決裁構造分析、社内推進戦略、説得文書、決裁者向けワンページ、独立ファクトチェックまでを一括で統括するオーケストレータースキル。「この企業向けの説得パッケージを作って」「調査から決裁資料まで一式」「大型提案の社内稟議を支援して」などで発動する。`decision-maker-research`、`champion-strategy`、`persuasion-document`、`research-verifier` を順に呼び、各ゲートを通過した成果物だけを次工程へ渡す。通常の初回提案や概算見積だけなら `initial-proposal` / `proposal-package` を使う。
---

# Persuasion Package

重要提案を「調査した」「資料を作った」で終わらせず、社内判断に耐える一式へまとめる。

## 使用判断

- 複数部署・経営層・調達が関与する提案 → 本スキル
- まず会話を始める簡易提案 → `initial-proposal`
- 費用・体制・工程を提示する見積提案 → `proposal-package`

## フェーズ

### 1. Research
`decision-maker-research` を実行し、事実・推論・不明点を分離する。入口仮説が根拠不足なら先へ進まない。

### 2. Strategy
`champion-strategy` で関係者、共通基準、証拠、合意形成順序、低リスクな次の一歩を設計する。

### 3. Document
`persuasion-document` で詳細文書と決裁者ワンページを作る。必要なら既存の見積・工程を参照する。

### 4. Verification
`research-verifier` で企業固有情報、数字、日付、効果主張を独立検証する。`refuted` は修正必須、`unsupported` は削除または仮説表示する。

### 5. Package

```text
persuasion-package/
├── 01-decision-research.md
├── 02-champion-plan.md
├── 03-persuasion-document.md
├── 04-executive-one-pager.md
├── 05-verification-report.md
└── source-register.md
```

顧客提出版には内部仮説、人物評価、検証メモを混ぜない。内部版と提出版を明確に分ける。

## 完了条件

- 求める判断と決裁者が明確。
- 主要主張に根拠と基準日がある。
- 現状維持を含む選択肢とリスクが示されている。
- 小規模検証の成功条件・中止条件がある。
- 決裁者ワンページ単体でも判断依頼が理解できる。
- 重大な `refuted` / `unsupported` が残っていない。
