# Mobile Path リファレンス（Phase 4-M）

> モバイルアプリ（iOS / Android）は **`osi-mobile-deploy` プラグインに全面委譲**する。
> create-app は Phase 0-3 でアプリ定義を確定し、それを渡すところまでで役目を終える。

このファイルには **委譲の受け渡し項目だけ**を書く。
osi-mobile-deploy 側のスキル一覧・手順・技術スタックはここに複製しない
（複製すると必ず陳腐化する。実際 v1.2.0 まで「React Native / Expo」と書かれたまま
osi-mobile-deploy 側はネイティブ既定に移行していた）。

---

## 1. そもそも create-app に来るべきか

**「モバイルアプリを作って」は `deploy-mobile-app`（osi-mobile-deploy）が直接受ける。**
create-app 経由は不要で、そちらが入口。

Phase 4-M が必要になるのは次のケースだけ:

- Web 前提でヒアリングを進めた結果、Phase 2-3 で「これはモバイルだ」と判明した
- Web とモバイルの両方を作る案件で、Web 側を create-app が担当している

---

## 2. 前提: osi-mobile-deploy が入っているか

`ListPlugins` で `osi-mobile-deploy` の有無を確認する。

**未インストールの場合** — マーケットプレイスからの導入を案内し、Phase 4-M を中断する。
導入できない事情があれば、次の代替を提示する:

- Web パス（Phase 4-W）に切り替え、PWA としてモバイル対応する
- モバイルは別途対応することにして、今回は Web だけ公開する

---

## 3. 委譲時に渡す情報

Phase 0-3 で確定した以下を、`deploy-mobile-app` を呼ぶ prompt に構造化して含める。

| 項目 | 説明 | 例 |
|------|------|-----|
| `PROJECT_NAME` | プロジェクト名（ケバブケース） | `inventory-tracker` |
| `PROJECT_DESCRIPTION` | アプリの一行説明 | `在庫管理モバイルアプリ` |
| エンティティ一覧 | Phase 1 で設計したデータモデル | `Product`, `Warehouse`, `StockEntry` |
| ロール一覧 | Phase 1 で設計したユーザーロール | `admin`, `warehouse_staff`, `viewer` |
| 機能要件 | Phase 2 で設計した画面・機能 | `バーコードスキャン`, `在庫一覧`, `入出庫記録` |
| OS 選択 | 対象プラットフォーム | `iOS` / `Android` / `両方` |
| バックエンド | Phase 3 で決定済みなら | `Firebase` / `Supabase` / `自前 API` |
| 作成先 | `health_check` の `repo_target`（org / 個人） | `org:ai-osi-uri` |

**技術スタックは create-app 側で決めない。** 既定スタックの選定（iOS = SwiftUI /
Android = Kotlin + Jetpack Compose）は osi-mobile-deploy 側の方針であり、
create-app が古い前提で上書きしないこと。

**コード生成もしない。** scaffold は `mobile-app-scaffold` が担う。

---

## 4. 委譲後

`deploy-mobile-app` が scaffold → Firebase → アイコン → Secrets → CI →
TestFlight / Play Internal までを完結させる。create-app 側でやるのは:

1. 委譲したことと、渡した情報を Phase N-1 の Drive 記録に残す
2. 完了レポートに「モバイル部分は osi-mobile-deploy に委譲」と明記する

配布状況・スタック・CI の詳細は osi-mobile-deploy 側のレポートを引用する形にし、
**create-app 側で独自に埋めない**（ここも陳腐化の温床になる）。

---

## 5. 完了レポートテンプレ

```
## モバイルアプリ（委譲）

- アプリ名: {PROJECT_NAME}
- 対象 OS: {iOS / Android / 両方}
- 委譲先: osi-mobile-deploy / deploy-mobile-app
- 実行ステータス: {完了 / 進行中 / 未開始}
- リポジトリ: {REPO_URL}

※ スタック・配布状況・CI の詳細は osi-mobile-deploy の完了レポートを参照。
```
