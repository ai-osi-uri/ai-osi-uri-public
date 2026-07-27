# Local Output Path リファレンス（Phase 4-L）

> サーバ（クラウド）にデプロイせず、ローカル/オンプレで実行可能な形でアプリを出力するパス。
> 出力先は次の 3 つ。**b) と c) は「オンプレの App Builder に取り込んで動かす」受け渡し形式**（App Builder が受け手）。
> a) は App Builder を介さない生プロジェクト出力。

---

## 1. Phase 4-L の判定条件

Phase 3（技術選定）で以下のいずれかに該当する場合、Phase 4-L に進む。

| ユーザーの発言 | 判定 |
|--------------|------|
| 「ローカルで動かしたい」「オフラインで使う」「インターネットなしで使いたい」 | Phase 4-L |
| 「社内サーバ／オンプレに置きたい」「Docker で渡したい」「自己完結で動かしたい」 | Phase 4-L（app-builder-container-export） |
| 「App Builder で簡単な台帳を作って渡したい」「現場でチャット改修させたい」 | Phase 4-L（app-builder-export） |
| 「プロジェクトフォルダをそのまま渡したい」「コードを触りたい」「とりあえずローカルで試したい」 | Phase 4-L（local-project-output） |
| 「デプロイはしないで」 | Phase 4-L |

### Phase 4-L に該当しないケース

- 「URL で公開したい」→ Phase 4-W（Web）
- 「スマホアプリにしたい」→ Phase 4-M（Mobile）
- 「デスクトップアプリにしたい」→ Phase 4-D（Desktop）

---

## 2. 3 つの出力形式

### a) local-project-output: プロジェクトフォルダ一式

プロジェクトのソースコードをそのまま出力する。受け取った人が `npm install` + `npm start` で起動する。

```
出力物:
├── src/                  # アプリケーションコード
├── package.json          # 依存関係・起動スクリプト
├── tsconfig.json         # TypeScript 設定
├── .env.example          # 環境変数テンプレート（実値なし）
├── README.md             # セットアップ手順・起動方法
└── docker-compose.yml    # DB（PostgreSQL 等）をローカルで立てる場合
```

**特徴:**
- ソースコードがそのまま見える（改変・拡張が容易）
- Node.js のインストールが前提
- 開発環境のセットアップが必要
- **App Builder は経由しない**（受け手が自分で起動する）

### b) app-builder-export: 台帳スペック（.appbuilder.json）を App Builder へ

**実行可能バイナリではない。** アプリの「仕様」だけを軽量 JSON（`.appbuilder.json`）に固め、
オンプレの **App Builder に取り込む**。App Builder が自分のテンプレートから**単一テーブルの台帳アプリ**を
組み立てて起動する（config 駆動）。受け手はそのまま**チャットで改修**まで自走できる。

```
出力物: {kebab-name}.appbuilder.json （1 ファイル・spec バンドル）
  kind: "app-builder-app-spec"
  manifest.config: { appTitle, entity.label, fields[], modules }
  records: [...]（初期データ・任意）
```

**特徴・制約:**
- 送り手はソースを持たなくてよい（config だけ運ぶ／ソースは App Builder のテンプレが持つ）
- **単一エンティティの台帳のみ**（複数テーブル・関連・任意UI・任意スタックは扱えない）
- 起動には**受け手が App Builder を動かしていること**が前提
- 詳細は atomic スキル `app-builder-export` に委譲

### c) app-builder-container-export: 生アプリ（単一イメージ tar）を App Builder へ

**任意スタックの生アプリ**（フロント＋自前バックエンド＋DB）を `docker build` → `docker save` し、
**単一の Docker イメージ tar（`.tar.gz`）** に固める。オンプレの **App Builder に取り込む**と
`docker load` され、カタログの「🐳 生アプリ」として起動/停止できる。依存・ランタイム・DB を
1 ファイルに同梱した「自己完結・オフライン起動」。

```
出力物: {kebab-name}.appbuilder-container.tar.gz （docker save したイメージ 1 ファイル）
  ※ docker-compose ではない。単一イメージの tar。
```

**App Builder 側の起動契約（この形に合わせる）:**
- App Builder は tar を `docker load` し、**単一コンテナ**を起動する:
  `docker run -d -p 127.0.0.1:<自動割当>:<EXPOSEポート> --memory 512m --cpus 1 <image>`
- **EXPOSE したポートを検出**して割り当てる（無ければ既定 3000）。**PORT 等の env は注入しない**。
- アプリは **`0.0.0.0` の固定ポートで待ち受ける**こと。
- DB は**コンテナ内**（SQLite/ファイル）に同梱する。**MVP の App Builder は volume を張らないため、
  起動のたびにコンテナが作り直され状態はリセットされる**（永続が要るなら初期データ同梱 or 将来の volume 対応待ち）。

**特徴:**
- 任意スタック（Node/Python/Go/…）を、中身を問わず動かせる
- Docker があれば OS を問わず同一環境で動作、ネット不要（`docker load`＋`run` のみ）
- Go/Rust の静的バイナリ＋`FROM scratch` にすると**ベースイメージ pull すら不要**で最小・完全オフライン
- 詳細は atomic スキル `app-builder-container-export` に委譲

---

## 3. 各形式の選択基準

| 受け取る人 / 状況 | 推奨形式 | 理由 |
|-----------------|---------|------|
| 開発者（自分でコードを触る） | local-project-output | ソースが見える、改変・拡張できる |
| App Builder を運用していて、**単純な台帳**を渡したい | app-builder-export | config 1 ファイルで渡せる・現場がチャット改修できる |
| App Builder を運用していて、**任意スタックの生アプリ**を自己完結・オフラインで渡したい | app-builder-container-export | 単一イメージ tar・ネット不要・環境差異なし |
| 社内 IT / インフラ（オンプレで運用） | app-builder-container-export | 再現性が高く、App Builder のカタログから起動/停止できる |

### 判断フロー

```
受け取る側は生ソースを触りたい?
  ├─ Yes → local-project-output
  └─ No（App Builder に取り込んで動かす）
      ├─ 単一テーブルの台帳で十分? → app-builder-export（.appbuilder.json）
      └─ 任意スタックの生アプリ（複数機能・独自UI・自前DB）? → app-builder-container-export（イメージ tar）
```

---

## 4. 実行手順

### 共通ステップ

```
Step 1: scaffold 生成（Phase 2-3 で設計したアプリのコードを生成）
Step 2-3: 必要なら gh-create-repo-and-push / harness-init（オンプレ受け渡しでは省略可）
```

### 形式別ステップ

#### local-project-output の場合

```
Step 4: プロジェクトフォルダをそのまま出力する（README・.env.example・DBがあれば docker-compose.yml）
Step 5: 出力先フォルダのパスをユーザーに報告する
```

#### app-builder-export の場合（台帳スペック）

```
Step 4: app-builder-export atomic を呼ぶ
  - appTitle / entity.label / fields[] / records を確定する
  - kind="app-builder-app-spec" の .appbuilder.json を 1 ファイル書き出す
Step 5: 検証（有効なJSON・fields が 1 件以上・型が許可値・enum に options）
Step 6: 出力パスと「App Builder →『アプリを取り込む』→ この .appbuilder.json」を報告する
```

#### app-builder-container-export の場合（生アプリ・イメージ tar）

```
Step 4: app-builder-container-export atomic を呼ぶ
  - 自己完結の Dockerfile を用意（0.0.0.0 待受・待受ポートを EXPOSE・メモリ512m/CPU1 で動く）
  - docker build → docker save | gzip で {name}.appbuilder-container.tar.gz を書き出す
Step 5: 検証（docker load → docker run -p 127.0.0.1:...:EXPOSE → GET / と主要 API を確認 → 片付け）
Step 6: 出力パス（tarサイズ）と「App Builder →『アプリを取り込む』→ この .tar.gz →『🐳 生アプリ』で起動」を報告する
```

> どちらも **App Builder が受け手**。docker-compose や外部 DB サーバ（Postgres 等）は使わない
> （App Builder は単一コンテナ / 単一台帳を前提とする）。DB はコンテナ内 SQLite/ファイルに寄せる。

---

## 5. 完了レポートテンプレ

Phase 4-L 完了時に以下のレポートを生成する。

```
## ローカル出力完了レポート

### 基本情報
- アプリ名: {PROJECT_NAME}
- 出力形式: {local-project-output / app-builder-export / app-builder-container-export}

### 出力先
- パス: {出力先の絶対パス}

### 起動方法

#### local-project-output の場合:
  cd {出力先パス}
  npm install
  npm start
  → http://localhost:3000

#### app-builder-export の場合（台帳スペック）:
  オンプレの App Builder →「📦 アプリを取り込む」→ この .appbuilder.json を選択
  → カタログに新しいアプリが追加され、起動できる（現場でチャット改修も可）

#### app-builder-container-export の場合（生アプリ・イメージ tar）:
  オンプレの App Builder →「📦 アプリを取り込む」→ この .tar.gz を選択（docker load）
  → カタログの「🐳 生アプリ」で「起動」→ 割り当てられた localhost:PORT で動作

### 含まれるもの
- スタック: {フレームワーク / ランタイム}
- DB: {SQLite / ファイル / なし}（app-builder-container-export はコンテナ内に同梱）

### 注意事項
- app-builder-* は **受け手が App Builder を運用していること**が前提
- app-builder-container-export は **Docker 必須**・状態はコンテナ寿命内（volume 未対応）
- 完全オフラインにするなら Go/Rust 静的バイナリ＋FROM scratch、または base image のローカルキャッシュ

### 次のステップ
- [ ] 受け手の App Builder で取り込み → 起動確認
- [ ] （将来）クラウド公開する場合は Phase 4-W に切り替え可能
```
