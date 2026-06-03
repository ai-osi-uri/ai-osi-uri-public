# config.json データスキーマ

`generate_deck.js` が読み込む JSON のスキーマ定義。フィールドはすべて省略可能ではない（`?` 付きを除く）。

## トップレベル

```json
{
  "meta":         { ... },
  "summary":      { ... },
  "people":       [ ... ],
  "asisOverview": { ... },
  "tobeOverview": { ... },
  "overview":     { ... },           // 任意：全体スイムレーン (AS-IS / TO-BE 2枚)
  "steps":        [ ... ],
  "structure":    { ... },
  "summaryEnd":   { ... }
}
```

`overview` はオプショナル。指定すれば「フェーズを横軸に取った全工程の俯瞰スイムレーン」を AS-IS / TO-BE で各1枚生成する。指定しなければ生成されない。

## meta

```json
{
  "title": "業務 AS-IS / TO-BE",
  "subtitle": "4ツールを人間が繋ぐ運用から、AIが一次処理し人間が承認する運用へ",
  "client": "AI OSI URI",
  "audience": "NEXT ONE 営業部 / 代理店事業部 / 代理店窓口担当 / 経営",
  "date": "2026-04-29",
  "eyebrow": "ENEROPS PLATFORM"   // 表紙左上の小さなラベル（任意）
}
```

## summary（1行サマリスライド）

```json
{
  "asisHeadline": "人間がデータをコピペで運ぶ",
  "asisDetail":   "Backlog / ChatWork / kintone ── 4ツールの間を、人間が手で同期している状態",
  "tobeHeadline": "AIが処理し人間は承認1クリック",
  "tobeDetail":   "AIが正規化・与信・地点特定・不備分類・文面生成を一次処理。人間は差分を見て承認するだけ"
}
```

## people（登場人物カード × 4枚）

```json
[
  {
    "icon": "users",        // users / building / userTie / userCog / user
    "title": "NEXT ONE 営業",
    "num": "5名",            // ハイライトする数字または短いラベル（例: "10社", "標準化"）
    "desc": "月3,000〜4,000件の申込を捌く\n1人あたり20〜30件/日"
  },
  ...
]
```

`note` フィールド（任意）を指定すると、4枚のカードの下に補足リボンが入る。

## asisOverview（AS-IS 全体像）

```json
{
  "tagline":  "4ツール間を「人間がプロトコル変換」している状態",
  "topBox":   "代理店 10社 ── 各社バラバラのCSV / kintone / SWDB",
  "topToMid": "メール添付・コピペ・各社固有手順",
  "midTitle": "NEXT ONE 営業 5名（月3,000〜4,000件）",
  "midTools": [                // 中段の4ツール（AS-IS の主たる作業ツール）
    { "name": "Excel\n管理簿",  "note": "10MB" },
    { "name": "Salesforce",     "note": "案件" },
    { "name": "Backlog",        "note": "議論" },
    { "name": "ChatWork",       "note": "急ぎ" }
  ],
  "extSystems": [               // 下段の4つの外部システム
    { "name": "後払い.com", "note": "メール",       "icon": "envelope" },
    { "name": "オートロ",   "note": "RPA 60%",     "icon": "warn" },
    { "name": "ENESAP",     "note": "証明書認証",  "icon": "tools" },
    { "name": "OCCTO",      "note": "画面操作",    "icon": "warn" }
  ]
}
```

`midTools` は4要素を推奨（3〜5でも動く）。`extSystems` も同様。アイコン候補は `envelope`, `warn`, `tools`, `pin`, `server`, `sync`。

## tobeOverview（TO-BE 全体像）

```json
{
  "tagline":  "AIが一次処理 → 人間は差分を見て承認1クリック",
  "topBox":   "代理店 10社 ── 既存CSVをそのまま投入",
  "topToMid": "AI正規化 + プレビュー確認",
  "midTitle": "enerops プラットフォーム",
  "stages": [                   // 中段の3段階（TO-BE のプラットフォーム内ステージ）
    { "icon": "robot", "label": "AI Agent", "desc": "正規化・与信\n地点特定・文面生成" },
    { "icon": "click", "label": "HITL",     "desc": "差分を見て\n[承認] クリック" },
    { "icon": "db",    "label": "単一DB",   "desc": "案件・不備・監査\nログを一元管理" }
  ],
  "extSystems": [               // 下段の外部接続（3〜4個）
    { "name": "後払い.com", "note": "REST API",        "tone": "green" },
    { "name": "OCCTO",      "note": "SOAP API",        "tone": "green" },
    { "name": "ENESAP",     "note": "触らない（手動）", "tone": "muted" }
  ]
}
```

`tone`: `green`（接続あり）/`muted`（接続なし・グレーアウト）。

## steps（ステップ詳細スイムレーン × N枚）

各ステップにつき **1スライド（combined）** または **2スライド（split: AS-IS / TO-BE 別ページ）** を生成。デフォルトは combined。

```json
{
  "num": "01",                  // セクション番号（表紙以外で連番）
  "title": "①取込",            // ステップ名
  "layout": "split",            // 任意："combined"(default) | "split"
  "asis": {
    "subtitle": "...",          // 任意：split時のみ、タイトル下に表示する一行サマリ
    "lanes":   [ { "name": "代理店", "sub": "10社" }, ... ],   // 4本（多くて5本）
    "slots":   5,                                                // 横スロット数 4-6
    "actions": [
      { "lane": 0, "slot": 0, "label": "CSVを\n作成する",
        "doc": "［作成］申込CSV",   // 任意：このアクションが触るドキュメント
        "fill": "RED", "tag": "各社バラバラ様式" },
      { "lane": 1, "slot": 1, "label": "Excelで\nマージする", "fill": "NAVY" }
    ],
    "flows":   [
      { "path": [[0,0],[1,1],[1,2]], "color": "RED", "labels": ["メール添付", "→"] }
    ],
    "docs": [                   // 任意：split時に下部凡例として表示
      { "name": "申込CSV", "where": "代理店ローカル / メール添付" },
      { "name": "Excel管理簿", "where": "営業共有ドライブ" }
    ]
  },
  "tobe": { ... 同じ構造 ... },
  "effect": "マッピング作業ほぼ消滅"
}
```

### action フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `lane`    | yes  | レーンインデックス（0始まり、上から） |
| `slot`    | yes  | スロットインデックス（0始まり、左から） |
| `label`   | yes  | セル本体の文言。**「目的語＋動詞」で書く**。改行は `\n` |
| `doc`     | no   | このアクションで作成/更新するドキュメント名。指定するとセル内に label の下に小さなイタリック行で表示される。`［作成］` `［更新］` `［閲覧］` `［承認］` `［送付］` `［受領］` `［生成］` `［取込］` のような接頭辞をつけると意味が伝わりやすい。改行は `\n` |
| `fill`    | no   | カラー名（`RED` / `NAVY` / `NAVY_DK` / `GOLD` / `GREEN` / `SLATE` / `SLATE_LT`）。デフォルト `NAVY` |
| `color`   | no   | 文字色名。`fill: GOLD` のときは `NAVY_DK` を指定すること（コントラスト確保） |
| `tag`     | no   | カードの上下に表示する小さな注釈（例：「15:00 締切」「成功率 60%」） |
| `disabled`| no   | `true` で破線の薄い枠＋斜体テキスト。「触らない」「(従来通り)」などに使う |

### step.layout

| 値 | 動作 |
|----|------|
| `"combined"`（default）| 1スライドに上下で AS-IS / TO-BE を描く（従来動作） |
| `"split"`              | AS-IS / TO-BE を別スライドに分けて 2スライド生成。各スライド下部に `docs` 凡例があれば描画 |

### asis / tobe.docs（split時のドキュメント凡例）

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name`    | yes  | ドキュメント名（例：「契約書ドラフト Word」「Notion 商談 DB」） |
| `where`   | no   | 保管場所・状態（例：「ローカル / OneDrive」「AI 抽出済の合意項目」） |

### flow フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `path`    | yes  | `[[lane, slot], [lane, slot], ...]` 形式の連続したセル列。隣り合うペアごとに矢印が描画される |
| `color`   | no   | カラー名（`RED` / `GREEN` / `GOLD` / `SLATE_LT`） |
| `bidir`   | no   | `true` で双方向矢印（往復・コール&レスポンス用） |
| `labels`  | no   | path[i] → path[i+1] の矢印に対する短い注釈（配列）。例：`["返信待ち", "再起票"]` |

**矢印は4方向すべて対応**：上下左右どこへ行く矢印もスクリプト側で `flipH` / `flipV` を使って正しく描画される。

## overview（全体スイムレーン × 2枚）── 任意

ステップ詳細とは別に、**全工程を1枚に俯瞰する全体スイムレーン**を AS-IS / TO-BE で各1枚生成する。フェーズ（① 商談 → ② 契約 → ③ 登録 …）を横軸、レーンを縦軸とした全体マップ。

```json
{
  "overview": {
    "phases": ["①商談", "②契約", "③登録", "④請求", "⑤入金"],   // 4-6 のフェーズ名 (列ヘッダ)
    "position": "before-steps",                                    // "before-steps"(default) | "after-steps"
    "asis": {
      "subtitle": "代表が全工程を兼任 ── ドキュメント分散 (9種)",
      "lanes": [ { "name": "顧客" }, ... ],                        // 4本
      "actions": [
        { "lane": 0, "phase": 1, "label": "...", "doc": "...", "fill": "RED" }
        // phase は slot と同じインデックス。両方書いた場合 phase が優先
      ],
      "flows": [ { "path": [[0,1],[2,1]], "color": "RED" } ],     // path は [[lane, phase], ...] でステップ間も繋げる
      "docs":  [ { "name": "...", "where": "..." }, ... ]         // 下部凡例
    },
    "tobe": { ... 同じ構造 ... }
  }
}
```

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `phases`   | yes  | 列ヘッダになるフェーズ名の配列（4-6個推奨） |
| `position` | no   | 全体スイムレーンの挿入位置。`"before-steps"`（個別ステップの前、デフォルト）/ `"after-steps"`（個別ステップの後ろ）|
| `asis.actions[].phase` | yes | フェーズインデックス（0始まり、左から）。`slot` でも可（互換性のため） |
| `asis.docs` | no | 下部凡例。3列グリッドで表示される |

`overview` を定義しなければ生成されない（後方互換）。

## structure（横軸の構造変化）

```json
{
  "items": [
    {
      "label": "ツールの数",
      "asisStat": "10+",
      "asis":     "Backlog / ChatWork / kintone / Excel / ENESAP / ...",
      "tobeStat": "1",
      "tobe":     "enerops 1つ + 既存ENESAP（限定運用）"
    },
    { "label": "データの正", "asisStat": "分散", "asis": "...", "tobeStat": "単一", "tobe": "..." }
  ]
}
```

行は2〜4行を推奨。

## summaryEnd（まとめスライド）

```json
{
  "eyebrow":  "SUMMARY",
  "headline": "導入で何が起きるか",
  "stats": [                   // 大きな数字 × 3
    { "num": "10+ → 1",     "label": "ツール数",       "desc": "4ツール往復が単一プラットフォームへ集約" },
    { "num": "60% → 100%",  "label": "地点特定の自動化","desc": "RPA成功率 → AI+API直叩きで圧縮" },
    { "num": "25%",          "label": "不備発生率",     "desc": "AI下書き+承認1クリックで滞留自動検知" }
  ],
  "closingBanner": "人間は「データ運搬」から解放され、「判断と承認」に集中できる",
  "footer": "矛盾時は 00_decisions.md が優先 / 最終更新: 2026-04-29"
}
```

---

## アイコン辞書

`icon` フィールドで使える名前と用途：

| 名前 | 用途 |
|------|------|
| `users`     | グループ・チーム |
| `building`  | 会社・代理店 |
| `userTie`   | 管理職・部長 |
| `userCog`   | 運営・管理部 |
| `user`      | 個人 |
| `robot`     | AI Agent |
| `click`     | HITL・承認操作 |
| `db`        | データベース |
| `envelope`  | メール |
| `warn`      | 警告・痛み |
| `tools`     | システム保守 |

新しいアイコンが必要な場合、`scripts/generate_deck.js` の ICONS 定義を拡張する。
