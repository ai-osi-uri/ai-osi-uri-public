# OSI Finance — QA・リリースチェックリスト（Phase 2）

配布前の品質ゲート、導入直後のスモークテスト、スキル発火テスト、運用安全確認を1枚にまとめる。
顧客・伴走先にも配るプロダクトのため、毎リリースでここを通す。

---

## A. リリース前ゲート（push 前に必ず）

- [ ] **コネクタ監査** `python3 scripts/audit_connectors.py --strict` → **ERROR 0**（WARN は既存分のみ許容）。
- [ ] **スキル検証** `python3 scripts/validate_skills.py` → osi-finance 配下のスキルにエラーなし
      （※ クラウド同期由来の空 `_shared`/`.fuse_hidden` は git 非追跡で公開物に出ない）。
- [ ] **発火eval整合性** `python3 scripts/eval_skill_firing.py --strict` → **ERROR 0 / WARN 0**
      （C表データセット `docs/eval/firing-tests.yaml` の全スキルカバレッジ・no_fire target 整合）。
- [ ] **バージョン** plugin.json と marketplace.json の osi-finance を一致させて bump（semver）。
- [ ] **機微値スキャン** 登録番号(T+13桁)・口座番号・実在支払先名が repo に無い
      （`grep -rE 'T[0-9]{13}|[0-9]{7,}' plugins/osi-finance/skills` で0件）。
- [ ] **設定外出し** 実値版 `osi-finance-settings.md` がコミットに含まれない（`.gitignore` の `**/osi-finance-settings.md`）。
- [ ] **台帳テンプレ同梱** `assets/templates/請求管理台帳_テンプレート.xlsx` / `支払管理台帳_テンプレート.xlsx` が存在。
- [ ] **CHANGELOG/README** を更新。タグ `osi-finance-v<version>` を正しいコミットに付ける。

## B. 導入直後スモークテスト（osi-finance-setup 実行後）

- [ ] `osi-finance-settings.md` が生成され、社名・税率・採番・Driveルートが入っている。
- [ ] Drive に `00.契約書/01.受領請求書/02.送付請求書`（＋`32.経費管理/カードSaaS証憑`）が作成された。
- [ ] 台帳テンプレが `02.送付請求書/請求管理台帳.xlsx`・`01.受領請求書/支払管理台帳.xlsx` に配置された。
- [ ] **請求(AR)**：osi-finance-invoice を当月でドライラン → 当月の未請求が件数・金額つきで抽出される。
- [ ] **受領検出(AP)**：osi-finance-payment-detect → 新着の受領請求書が拾える／無ければ「新着なし」。
- [ ] **突合(AP)**：osi-finance-mf-sync → 支払済とMF仕訳が請求書IDで突合し、計上漏れ0を確認。
- [ ] **ダッシュボード**：osi-finance-dashboard → 費用構成・純損益・直近支払が描画され、AR数値が出る。
- [ ] **コネクタ**：MoneyForward・Google Drive（＋ローカル同期）・メール（Gmail/Superhuman）の疎通。
- [ ] **日次/月次タスク**：登録後に一度「Run now」で接続許可を先取り。

## C. スキル発火テスト（eval 用フレーズ）

各スキルが「発火すべき」入力で起動し、「発火すべきでない」入力で起動しないことを確認（skill-creator の eval でも自動化可）。

| スキル | 発火すべき例 | 発火すべきでない例 |
|---|---|---|
| osi-finance-contract-intake | 「契約を取り込んで」「○○社の契約を台帳に」 | 「請求書を作って」 |
| osi-finance-invoice | 「今月の請求書を作って」「請求下書きを作成」 | 「契約を取り込んで」 |
| osi-finance-payment-intake | 「この請求書払って」「受領請求書を起票」 | 「請求書を発行して」（AR） |
| osi-finance-payment-detect | （日次タスクから）受領請求書の取りこぼし検出 | 単発の支払起票（intakeの役割） |
| osi-finance-mf-sync | 「台帳とMFを突合」「計上漏れを確認」 | 「支払予定を起票」 |
| osi-finance-monthly | 「今月の経理を締めて」「月次クローズ」 | 「請求書を発行」 |
| osi-finance-dashboard | 「会計ダッシュボードを作って」「請求・支払・経費を一覧で」 | 「請求書を1枚作って」 |
| osi-finance-setup | 「OSI Finance を導入」「経理を初期セットアップ」 | 「今月の請求書を作って」 |

## D. 運用安全（毎回確認）

- [ ] **送金しない**（振込/カードは人が実行）。
- [ ] **台帳の自動確定をしない**（起票・更新は案 → 人が確認して反映）。
- [ ] **機微値をチャットに出さない**（口座番号・登録番号・実在支払先名は設定ファイルへ）。
- [ ] 会計・税務の最終判断は人（必要なら税理士）。会計の正本は MF の口座連携明細、台帳は資金管理。

---

## Phase 2 の実装状況（v0.5.0）

- [x] 自動 eval：C表を機械可読化した `docs/eval/firing-tests.yaml`（8スキル / fire 40 / no_fire 16）と
      runner `scripts/eval_skill_firing.py` を同梱。整合性検証（カバレッジ・no_fire target・重複）を
      `--strict` でゲート化。`--emit-skill-creator OUTDIR` で skill-creator `run_eval.py` 用の eval-set を
      skill 単位出力（本物の発火率測定は Mac の skill-creator で実行）。
- [x] オンボーディングUX：`osi-finance-setup` ステップ7「導入完了レポート」で B 表9項目を
      自動実行し OK/要対応/スキップ＋サマリ＋要対応リストを出す。雛形＝
      `skills/osi-finance-setup/references/setup-completion-report.md`。
- [x] エラー処理：正本 `docs/エラー処理ガイド.md`（大容量PDF＝ローカル同期／添付＝Superhuman／
      MF事業者・期間ズレ／settings未整備）を作成し、全8スキルの末尾「## エラー処理」節から参照。

### C表データセットの回し方（Mac, skill-creator で本物の発火eval）

```bash
# 1) eval-set を生成（skill 単位 JSON）
python3 scripts/eval_skill_firing.py --emit-skill-creator /tmp/osi-finance-evalset
# 2) skill-creator の run_eval.py で発火率を測定（例: osi-finance-invoice）
python3 <skill-creator>/scripts/run_eval.py \
    --eval-set /tmp/osi-finance-evalset/osi-finance-invoice.eval.json \
    --skill-path plugins/osi-finance/skills/osi-finance-invoice --verbose
```

## Phase 3（今後）

- 他会計SaaS（freee 等）・多通貨・多言語（需要が出たら）。
- 発火eval を CI に組み込み、誤発火/取りこぼしを定点観測（数値の経時比較）。
