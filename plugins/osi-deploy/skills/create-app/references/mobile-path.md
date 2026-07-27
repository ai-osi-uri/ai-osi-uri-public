# Mobile Path リファレンス（Phase 4-M）

> モバイルアプリ（iOS / Android）の構築・配布は `osi-mobile-deploy` プラグインに委譲する。
> create-app は Phase 0-3 でアプリ定義を確定し、必要な情報を渡す役割に徹する。

---

## 1. Phase 4-M の位置づけ

create-app のフロー全体における Phase 4-M の役割:

```
Phase 0: ヒアリング（何を作る？誰が使う？）
Phase 1: エンティティ・ロール設計
Phase 2: 画面・機能設計
Phase 3: 技術選定 → デプロイ先 = モバイル と判定
Phase 4-M: osi-mobile-deploy プラグインに委譲 ← ここ
```

**create-app は Phase 4-M で「作る」ことをしない。**
Phase 0-3 で確定したアプリ定義を `osi-mobile-deploy` プラグインの `deploy-mobile-app` オーケストレータに渡し、
以降のモバイル固有の工程（scaffold・ビルド・TestFlight/Play Console 配布）はすべてプラグイン側が担う。

---

## 2. osi-mobile-deploy プラグインの前提条件

### プラグインがインストール済みであること

Phase 4-M に入る前に、`osi-mobile-deploy` プラグインが利用可能か確認する。

#### 確認方法

```
mcp__plugins__list_plugins を呼び出し、osi-mobile-deploy が一覧に含まれるか確認する
```

#### インストール済みの場合

そのまま Phase 4-M に進む。

#### 未インストールの場合

ユーザーに以下を案内する:

```
モバイルアプリの構築には osi-mobile-deploy プラグインが必要です。

インストール方法:
1. Claude Code の設定画面でプラグインマーケットプレイスを開く
2. 「osi-mobile-deploy」を検索する
3. インストールボタンを押す

プラグインがインストールされたら、再度このスキルを呼び出してください。
```

- プラグインが存在しない場合は Phase 4-M を中断し、Phase 4-W（Web）への切り替えを提案する
- 「PWA としてモバイル対応する」という代替案も提示する

---

## 3. 委譲時に渡す情報

create-app の Phase 0-3 で確定した以下の情報を `deploy-mobile-app` に渡す。

| 項目 | 説明 | 例 |
|------|------|-----|
| `PROJECT_NAME` | プロジェクト名（ケバブケース） | `inventory-tracker` |
| `PROJECT_DESCRIPTION` | アプリの一行説明 | `在庫管理モバイルアプリ` |
| エンティティ一覧 | Phase 1 で設計したデータモデル | `Product`, `Warehouse`, `StockEntry` |
| ロール一覧 | Phase 1 で設計したユーザーロール | `admin`, `warehouse_staff`, `viewer` |
| 機能要件 | Phase 2 で設計した画面・機能 | `バーコードスキャン`, `在庫一覧`, `入出庫記録` |
| OS 選択 | 対象プラットフォーム | `iOS` / `Android` / `両方` |
| バックエンド | DB・API の情報（Phase 3 で決定済みの場合） | `Supabase` / `Firebase` / `自前 API` |

### 渡し方

`deploy-mobile-app` スキルを呼び出す際に、上記情報を構造化して prompt に含める。
create-app 側でコード生成は行わない（scaffold はプラグイン側の `mobile-app-scaffold` が担う）。

---

## 4. osi-mobile-deploy のスキル一覧と役割

### deploy-mobile-app（オーケストレータ）

モバイルアプリの構築から配布までを一気通貫で進めるオーケストレータ。
以下の atomic スキルを順番に呼び出す。

### mobile-app-scaffold

React Native / Swift / Kotlin のテンプレートプロジェクトを生成する。

- React Native: Expo または bare workflow
- Swift: Xcode プロジェクト（SwiftUI ベース）
- Kotlin: Android Studio プロジェクト（Jetpack Compose ベース）
- GitHub Actions CI（ビルド・テスト）を `.github/workflows/` に設定する

### ios-testflight-deploy

iOS アプリを TestFlight に配布する。

- Xcode Cloud または GitHub Actions で `.ipa` をビルドする
- App Store Connect API でアップロードする
- テスターグループへの配布を設定する
- 前提: Apple Developer Program への加入、証明書・プロビジョニングプロファイルの設定

### android-play-deploy

Android アプリを Google Play Console に配布する。

- GitHub Actions で `.aab`（Android App Bundle）をビルドする
- Play Console API でアップロードする
- 内部テスト / クローズドテスト / オープンテストトラックへの配布を設定する
- 前提: Google Play Console アカウント、署名鍵の設定

### mobile-app-smoke-test

配布したアプリの動作確認を行う。

- API エンドポイントへの疎通確認
- ディープリンクの動作確認
- クラッシュフリーレートの初期確認

### mobile-firebase-setup

Firebase の初期設定を行う。

- Firebase プロジェクトの作成
- `google-services.json`（Android）/ `GoogleService-Info.plist`（iOS）の配置
- Analytics / Crashlytics / Push Notifications の有効化
- Firestore / Realtime Database のルール設定（必要な場合）

### mobile-icon-generator

アプリアイコンを生成する。

- 元画像（1024x1024）から各サイズのアイコンを自動生成する
- iOS: `Assets.xcassets/AppIcon.appiconset/`
- Android: `mipmap-xxxhdpi` ~ `mipmap-mdpi`
- Adaptive Icon（Android）の foreground / background 設定

### mobile-secrets-sync

シークレット管理を行う。

- API キー、署名鍵、証明書などを GitHub Secrets に登録する
- CI/CD ワークフローから安全に参照できるようにする
- `.env` ファイルのテンプレートを生成する（実値は含めない）

### mobile-crash-triage

クラッシュ分析を行う。

- Firebase Crashlytics / Sentry からクラッシュレポートを取得する
- 頻度・影響度でトリアージする
- 修正の優先度を提案する

### mobile-update-deploy

モバイルアプリの更新版を配布する。

- コード変更を検出し、バージョンを bump する
- CI/CD パイプラインをトリガーする
- TestFlight / Play Console への再配布を行う

---

## 5. ios-mobile-release との関係

`osi-deploy` プラグイン内の `ios-mobile-release` スキルは、iOS アプリの**リリース管理**を担う。

### 役割分担

| スキル | プラグイン | 役割 |
|--------|-----------|------|
| `ios-testflight-deploy` | osi-mobile-deploy | TestFlight への**初回配布・テスト配布** |
| `ios-mobile-release` | osi-deploy | App Store への**本番リリース管理** |

### ios-mobile-release の機能

- **カナリアリリース**: 一部ユーザーへの段階的配布（1% → 10% → 50% → 100%）
- **週次バッチリリース**: 毎週決まった曜日にリリースを実行するスケジュール管理
- **ロールバック**: 問題発生時に前バージョンに戻す
- **App Store Connect のステータス監視**: レビュー状況の追跡

### フロー

```
開発 → mobile-app-scaffold（osi-mobile-deploy）
     → ios-testflight-deploy（osi-mobile-deploy）でテスト配布
     → テスト完了後
     → ios-mobile-release（osi-deploy）で本番リリース管理
```

- テストフェーズまでは `osi-mobile-deploy` プラグインが担当する
- 本番リリース管理は `osi-deploy` プラグインの `ios-mobile-release` が担当する
- create-app は初回構築のみ関与し、リリース管理には直接関与しない

---

## 6. 完了レポートテンプレ

Phase 4-M の委譲完了時に以下のレポートを生成する。

```
## モバイルアプリ完了レポート

### 基本情報
- アプリ名: {PROJECT_NAME}
- 対象 OS: {iOS / Android / 両方}
- フレームワーク: {React Native / Swift / Kotlin}
- リポジトリ: {REPO_URL}

### 委譲先
- プラグイン: osi-mobile-deploy
- オーケストレータ: deploy-mobile-app
- 実行ステータス: {完了 / 進行中 / 未開始}

### 配布状況
- iOS (TestFlight): {配布済み / 未配布 / 対象外}
- Android (Play Console): {配布済み / 未配布 / 対象外}

### バックエンド連携
- DB: {Supabase / Firebase / 自前 API}
- 認証: {Supabase Auth / Firebase Auth / なし}
- プッシュ通知: {Firebase Cloud Messaging / APNs / 未設定}

### CI/CD
- GitHub Actions: {設定済み / 未設定}
- シークレット: {GitHub Secrets に登録済み / 未登録}

### 次のステップ
- [ ] テスターによる動作確認
- [ ] Firebase Crashlytics の監視開始
- [ ] 本番リリース時は ios-mobile-release（osi-deploy）を使用する
```
