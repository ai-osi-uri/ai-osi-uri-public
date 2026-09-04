---
name: meishi-generator
description: >
  AI OSI URI の名刺（表面）のラクスル入稿用PDFを自動生成するスキル。
  「○○さんの名刺を作って」「新しいメンバーの名刺データを作成」「名刺を発注したい」
  「入稿データを作って」「名刺PDFを生成」など、名刺の作成・発注準備に関わるリクエストで発動する。
  会社共通デザイン（ロゴ・社名・住所・URL・トンボ）は原本の .ai（PDF互換）のベクターデータを
  そのまま維持し、人ごとに変わる部分（役職・氏名・ローマ字・携帯番号・メール）だけを差し替える。
  出力はラクスル「名刺 通常サイズ_横（仕上がり91×55mm）」テンプレ準拠・CMYK（スミ100／ブランド赤
  C17 M98 Y90 K0）の入稿用PDF。発注そのものは人がラクスルで行う（本スキルはデータ生成まで）。
requires_connectors:
  - server: cowork
    provision: builtin
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# 名刺入稿PDFジェネレーター（AI OSI URI）

## 概要

原本テンプレ（`scripts/template_noemail.pdf` = 松尾さん版ベース / `scripts/template_email.pdf` = 坂口さん版ベース）の可変部分を白マスクで消し、キャリブレーション済みの座標・サイズ・字間で新しい人のテキストを重ねる方式。固定要素は原本ベクターがそのまま残るため、印刷品質は原本と同一。

- 漢字・かな: Noto Sans CJK JP Medium（サブセット化→TrueType変換して埋め込み）
- 英字・数字: Montserrat 500（原本の欧文デザインとほぼ一致することを確認済み）
- 色: すべて DeviceCMYK。文字=K100、ローマ字赤=C16.8 M97.7 Y89.5 K0（ロゴと同色）
- メールあり/なしで右カラムのレイアウトが変わるため、ベースPDFを自動で切り替える

## 使い方

1. 次の項目をユーザーから集める（AskUserQuestionまたは会話で）:
   - 氏名（例: 松尾 夏実）※姓名の間はスペース
   - ローマ字（例: Natsumi Matsuo）※名→姓の順
   - 役職（例: 秘書、執行役員 CIO、エンジニア）※英字混じり可
   - 携帯番号（例: 090-1234-5678）※「Tel. 」は自動付与
   - メールアドレス（任意。あればE-mail行が追加される）
2. **作業コピーを作る（下の「実行環境の準備」を必ず先に実施）**。以後 `/tmp/meishi` で実行:

```bash
cd /tmp/meishi && python3 meishi_gen.py '{"name":"山田 太郎","romaji":"Taro Yamada","title":"エンジニア","tel":"080-1234-5678","email":"yamada@ai-osi-uri.com","out":"/tmp/meishi_out.pdf"}'
```

   `email` は省略可（`null` または キー自体を省く）。
   ローマ字は原本の組み方に合わせて各語の頭文字を大文字にする（`taro yamada` → `Taro Yamada`）。
3. 生成PDFを `pdftoppm -png -r 150` でレンダリングし、カード部分をクロップして必ずユーザーに目視確認してもらう。
4. 確認OKなら `名刺_{氏名スペースなし}_表.pdf` にリネームして SendUserFile で納品する。

## 実行環境の準備（Cowork では必須）

Cowork の bash は**独立した Linux サンドボックス**で動くため、このスキルの `scripts/`
（ホスト側のプラグインキャッシュにある）には**到達できない**。`cd scripts` すると
`No such file or directory` になる。実行前に、bash から見える場所へ作業コピーを作ること。

**方法A（配布リポの clone が手元にある人／推奨）**

1. `mcp__cowork__request_cowork_directory` で clone を接続する
   （既定 `~/projects/ai-osi-uri-plugins`。無ければ方法Bへ）
2. bash で作業コピーを作る（`<VM>` は接続時に案内される `/sessions/.../mnt/...` パス）:

```bash
cp -R "<VM>/ai-osi-uri-plugins/plugins/osi-backoffice/skills/meishi-generator/scripts" /tmp/meishi
```

**方法B（clone が無い人。「AI OSI URI Deploy」拡張が必要）**

1. `mcp__AI_OSI_URI_Deploy__github_clone` で
   `repo_owner: ai-osi-uri` / `repo_name: ai-osi-uri-plugins` / `depth: 1` /
   `dest_dir: <接続フォルダの絶対パス>/_meishi_tmp` を clone
2. bash で `cp -R "<VM>/_meishi_tmp/plugins/osi-backoffice/skills/meishi-generator/scripts" /tmp/meishi`
3. `rm -rf "<VM>/_meishi_tmp"` で片付ける
   （`Operation not permitted` が出たら `mcp__cowork__allow_cowork_file_delete` で許可を取る）

どちらも使えない場合は、そのメンバーの環境では生成できない。**Deploy 拡張の設定**
（`setup-deploy-environment`）を案内するか、生成できる人に依頼する。

## 検証（必ず実施）

- 生成後、300dpiでレンダリングして可変部分のテキストに文字化け（豆腐 ☒）がないか確認する。
- 氏名が5文字以上・役職が長い場合は左ブロックが右カラムに食い込まないか目視確認する
  （左ブロックの安全幅はカード左端から約300px@300dpi。はみ出す場合は `PARAMS` の
  `name.size` を下げるか、ユーザーに相談する）。

## ラクスルでの発注手順（人が実施）

1. ラクスルで「名刺印刷 通常サイズ（91×55mm）横型」を選択（用紙・部数・納期は前回発注に合わせる）
2. データ入稿で生成した表面PDFをアップロード
3. 裏面は共通デザイン（既存の裏面データを流用）
4. プレビューで文字位置・欠けを確認して注文確定

## 技術メモ

- 原本 .ai はテキストがアウトライン化されており直接編集不可。そのため差し替え方式を採用。
- 座標パラメータは `meishi_gen.py` の `PARAMS`（300dpi px基準）。松尾・坂口の原本2枚との
  ピクセル比較でキャリブレーション済み（可変部分以外は完全一致）。
- Noto の CFF→TrueType 変換は `fontprep.py`。**Cowork のサンドボックスには
  `NotoSansCJK-Medium.ttc` が入っていないことがある**（Regular / Bold のみ）ため、
  `fontprep.resolve_font()` がローカル候補を順に探し、無ければ notofonts の公式 OTF を
  `$TMPDIR/meishi-noto-cache/` に取得する（初回のみ約16MB・要ネットワーク）。
  手元のフォントを使わせたいときは環境変数 `MEISHI_NOTO_MEDIUM` にパスを指定する。
  太さの自動フォールバック（Medium→Regular 等）はしない。印刷物の見た目が
  気付かないまま変わる方が事故なので、用意できないときは明示エラーで止める。
- 依存: reportlab, pypdf, fontTools, pikepdf（いずれもCowork標準）
