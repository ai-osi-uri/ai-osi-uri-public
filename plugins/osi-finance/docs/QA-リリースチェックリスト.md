# OSI Finance — QA・リリースチェックリスト（Phase 2）

配布前の品質ゲート、導入直後のスモークテスト、スキル発火テスト、運用安全確認を1枚にまとめる。
顧客・伴走先にも配るプロダクトのため、毎リリースでここを通す。

---

## A. リリース前ゲート（push 前に必ず）

- [ ] **コネクタ監査** `python3 scripts/audit_connectors.py --strict` → **ERROR 0**（WARN は既存分のみ許容）。
- [ ] **スキル検証** `python3 scripts/validate_skills.py` → osi-finance 配下のスキルにエラーなし
      （※ クラウド同期由来の空 `_shared`/`.fuse_hidden` は git 非追跡で公開物に出ない）。
- [ ] **バージョン** plugin.json と marketplace.json の osi-finance を一致させて bump（semver）。
- [ ] **機微値スキャン** 登録番号(T+13桁)・口座番号・実在支払先名が repo に無い
      （`grep -rE 'T[0-9]{13}|[0-9]{7,}' plugins/osi-finance/skills` で0件）。
- [ ] **設定外出し** 実値版 `keiri-settings.md` がコミットに含まれない（`.gitignore` の `**/keiri-settings.md`）。
- [ ] **台帳テンプレ同梱** `assets/templates/請求管理台帳_テンプレート.xlsx` / `支払管理台帳_テンプレート.xlsx` が存在。
- [ ] **CHANGELOG/README** を更新。タグ `osi-finance-v<version>` を正しいコミットに付ける。

## B. 導入直後スモークテスト（osi-finance-setup 実行後）

- [ ] `keiri-settings.md` が生成され、社名・税率・採番・Driveルートが入っている。
- [ ] Drive に `00.契約書/01.受領請求書/02.送付請求書`（＋`32.経費管理/カードSaaS証憑`）が作成された。
- [ ] 台帳テンプレが `02.送付請求書/請求管理台帳.xlsx`・`01.受領請求書/支払管理台帳.xlsx` に配置された。
- [ ] **請求(AR)**：keiri-invoice を当月でドライラン → 当月の未請求が件数・金額つきで抽出される。
- [ ] **受領検出(AP)**：keiri-payment-detect → 新着の受領請求書が拾える／無ければ「新着なし」。
- [ ] **突合(AP)**：keiri-mf-sync → 支払済とMF仕訳が請求書IDで突合し、計上漏れ0を確認。
- [ ] **ダッシュボード**：keiri-dashboard → 費用構成・純損益・直近支払が描画され、AR数値が出る。
- [ ] **コネクタ**：MoneyForward・Google Drive（＋ローカル同期）・メール（Gmail/Superhuman）の疎通。
- [ ] **日次/月次タスク**：登録後に一度「Run now」で接続許可を先取り。

## C. スキル発火テスト（eval 用フレーズ）

各スキルが「発火すべき」入力で起動し、「発火すべきでない」入力で起動しないことを確認（skill-creator の eval でも自動化可）。

| スキル | 発火すべき例 | 発火すべきでない例 |
|---|---|---|
| keiri-contract-intake | 「契約を取り込んで」「○○社の契約を台帳に」 | 「請求書を作って」 |
| keiri-invoice | 「今月の請求書を作って」「請求下書きを作成」 | 「契約を取り込んで」 |
| keiri-payment-intake | 「この請求書払って」「受領請求書を起票」 | 「請求書を発行して」（AR） |
| keiri-payment-detect | （日次タスクから）受領請求書の取りこぼし検出 | 単発の支払起票（intakeの役割） |
| keiri-mf-sync | 「台帳とMFを突合」「計上漏れを確認」 | 「支払予定を起票」 |
| keiri-monthly | 「今月の経理を締めて」「月次クローズ」 | 「請求書を発行」 |
| keiri-dashboard | 「会計ダッシュボードを作って」「請求・支払・経費を一覧で」 | 「請求書を1枚作って」 |
| osi-finance-setup | 「OSI Finance を導入」「経理を初期セットアップ」 | 「今月の請求書を作って」 |

## D. 運用安全（毎回確認）

- [ ] **送金しない**（振込/カードは人が実行）。
- [ ] **台帳の自動確定をしない**（起票・更新は案 → 人が確認して反映）。
- [ ] **機微値をチャットに出さない**（口座番号・登録番号・実在支払先名は設定ファイルへ）。
- [ ] 会計・税務の最終判断は人（必要なら税理士）。会計の正本は MF の口座連携明細、台帳は資金管理。

---

## Phase 2 の残タスク（このチェックリスト導入後の発展）

- 自動 eval：skill-creator で C 表のフレーズを回し、発火精度を数値化（誤発火/取りこぼしを定点観測）。
- オンボーディングUX：osi-finance-setup の完了時に B 表のスモークを自動実行し「導入完了レポート」を出す。
- エラー処理：大容量PDFのDrive格納（ローカル同期推奨）・添付取得（Superhuman必須）の失敗時ガイドを各スキルに明記。
- Phase 3：他会計SaaS（freee 等）・多通貨・多言語（需要が出たら）。
