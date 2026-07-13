# claude-progress.md

> ハーネスの「状態サブシステム」。長いタスク・複数セッションをまたいで文脈を失わないための単一の真実。
> **毎セッション終了前に更新し、毎セッション開始時に最初に読む。**

---

## Current Verified State（現在の検証済み状態 = 唯一の真実）

- プロジェクト名: {{PROJECT_NAME}}
- 標準の起動パス: ./init.sh （内部: {{START_CMD}}）
- 標準の検証パス: {{VERIFY_CMD}}
- 最優先の未完了機能: 【TODO: 次のセッションが着手すべき feature の id / title】
- 現在のブロッカー: 【TODO: 詰まっていることがあれば。なければ "なし"】
- 最終更新: 【TODO: YYYY-MM-DD】

---

## Session Record（セッション記録 — 1セッション1エントリ、新しい順に上へ追記）

### YYYY-MM-DD セッションN

- **Goal（やる予定だったこと）**: 【TODO】
- **Completed（実際にできたこと）**: 【TODO】
- **Verification run（実行した検証）**: 【TODO: 実行したコマンドと結果】
- **Evidence recorded（残した証拠）**: 【TODO: テスト出力 / ログ / スクショの場所】
- **Commits（コミット）**: 【TODO: ハッシュやメッセージ】
- **Known risks（壊れているかもしれない箇所）**: 【TODO】
- **Next best action（次セッションの最初の一手）**: 【TODO】

---

<!--
新しいセッションを始めるたびに、上の Session Record の先頭にテンプレをコピーして埋める。
Current Verified State は常に最新の1状態だけを保つ（履歴は Session Record 側に積む）。
-->
