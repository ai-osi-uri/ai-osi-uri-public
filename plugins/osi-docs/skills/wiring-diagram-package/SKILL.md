---
name: wiring-diagram-package
description: 手描き配線図や現場写真の受領から、画像補正、構造化抽出、段階的なユーザー確認、必要な型番調査、物理・論理ネットワーク構成図、接続表、BOM、最終検証までを統括するオーケストレータースキル。「この配線図を正式な構成図とBOMにして」「手描き図から納品一式を作って」「途中から配線図作成を再開して」などで発動する。`wiring-diagram-intake` と `network-diagram-package` を順に呼び、セッション状態と意思決定履歴を保存して再開可能にする。
---

# Wiring Diagram Package

認識、確認、レンダリングを分離し、曖昧な入力から誤った完成図が直接生成されることを防ぐ。

詳細な正本スキーマは [references/data-schema.md](references/data-schema.md) を参照する。

## フェーズ

### 1. Intake

元画像を保全し、`wiring-diagram-intake` で補正、抽出、矛盾検出を行う。

### 2. Clarification Gate

P0 → P1 → P2の順に質問する。一度に全件を聞かず、回答によって後続質問が消えるものを先に確認する。決定は `decisions.jsonl` へ追記する。

### 3. Model Research

型番指定が必要な場合だけ実施する。メーカー公式仕様を優先し、図面から読めた情報とWeb補完を混同しない。候補採用にはユーザー承認を得る。

### 4. Source Freeze

`network-source.json` を確定し、ハッシュ、版、確認者、未確定一覧を `session.json` へ保存する。P0が残る場合は停止する。

### 5. Render

`network-diagram-package` で物理図、論理図、接続表、BOMを生成する。

### 6. Finalize

図・表・BOMの整合、ページ表示、機密情報、成果物名を検査し、最終報告を作る。

## セッション構成

```text
wiring-session/
├── session.json
├── intake/
├── decisions.jsonl
├── network-source.json
├── sources.md
├── output/
│   ├── physical-diagram.pptx
│   ├── logical-diagram.pptx
│   ├── connection-table.xlsx
│   ├── bom.xlsx
│   └── review.pdf
└── final-report.md
```

## 再開規則

- `session.json` と `network-source.json` の版を確認する。
- 完了済みフェーズを再実行しない。
- 入力変更時は影響を受ける成果物だけ無効化する。
- 決定履歴を上書きせず、新しい判断として追記する。

## 完了条件

- 入力から成果物まで追跡可能。
- ユーザー承認なしの型番補完がない。
- 構成図とBOMのID・数量が一致。
- 未確定事項、施工時確認、支給品が明示されている。
- 全成果物をレンダリング・視覚確認済み。
