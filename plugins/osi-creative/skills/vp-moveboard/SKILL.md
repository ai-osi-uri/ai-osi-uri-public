---
name: vp-moveboard
description: AI動画の「1枚の画像をカメラの動きで魅せる」メソッド。写真・絵画・イラスト・商品・建築・人物など“動かしたい画像1枚”を、引いた線（ムーブボード）の通りに動かす（仕上がりはシネマティックにもフラットにも、用途次第）。中核は「ルート＋番号＋動き説明ラベル付きのムーブボードをコードで1本だけ描き、Seedance 2.0 reference-to-video の参照画像として渡す」。書いたムーブボード／プロンプトは vp-core の承認ゲートに渡し、承認後に生成する。「この画像を動かして」「絵の中を潜り込む」「商品をかっこよく回す（オービット）」「建物の中をウォークスルー」「ドローン空撮」「上空から○○」などのリクエストで、オーケストレータ ai-video-production から呼ばれる（単独指定も可）。キャラの躍動アクションは vp-character-action、ナレ主体の企業説明は vp-corporate-narrated。
version: 0.1.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_image, edit_image, submit_video, reference_to_video, check_status]
---

# vp-moveboard — 1枚の画像をカメラムーブで魅せる（プロンプト作者）

このメソッドの仕事は **「美しいカメラの通り道を設計し、それを“1本のムーブボード”に固定して、短い動画プロンプトを書く」** こと。
生成・承認・連結は `vp-core` に渡す。元ネタ（ISTANBUL/SNSの線で飛ばすテク）を一般化し、video-creator-market（イスタンブール／東京／城）で確立。

**詳細レシピ（プリセット・カメラ語彙・プロンプト雛形・著作権）は `../ai-video-production/references/moveboard.md` を正本として必ず参照。**
落とし穴は `../ai-video-production/references/pitfalls.md` の #17（reference-to-videoで解決）/ #18（モーション予算）。

## 4つの確定原則（これを外すと失敗する）

1. **入力は `reference-to-video`（参照モード）**：model=`bytedance/seedance-2.0/reference-to-video`。`image-to-video`（1フレーム目固定）は赤線が映り込むので**使わない**（#17）。参照モードなら線は出力に出ず“指示”としてだけ効く。
2. **ルート線は AI に描かせず、コードで1本だけ描く**：AIに描かせると2本目・余計なループが出て解釈がブレる。Python(Pillow)で通過点を Catmull-Rom 補間して**1本の連続曲線**にする。
3. **線で表せない情報はラベルで補う**：動きの種類・速度・高さ(3D)・orbit は線だけでは伝わらない。**番号＋短い動き説明ラベル**を必ず付ける（例 `PUSH IN / strong motion`、`CLIMB / rise quickly`、`HERO ORBIT / around the landmark`、`PULL BACK / widen`、`GRAND REVEAL / finish high`）。ループ(orbit)は `ORBIT` ラベル付きで可。
4. **動画プロンプトは短く**：振り付けはムーブボード（画像）が担う。プロンプトは「線の通りに飛べ／線は出すな／FX音のみ」程度に。

## 被写体プリセット（6種）
①空撮（実景）②名画・アートの潜り込み ③商品ヒーロー（オービット）④建築・内装ウォークスルー ⑤人物の微動 ⑥抽象・テクスチャ。
（プリセット別の典型ムーブ・プロンプト雛形は正本レシピ参照。空撮の6ビート詳細は `../ai-video-production/references/drone-aerial-fpv.md`）

## フロー

1. **ヒアリング**（`AskUserQuestion`）：①元画像はある？(ある=自前/アップロード/URL、ない=生成) ②被写体タイプ(6プリセット) ③カメラムーブ ④迫力レベル(迫力重視/優雅/標準) ⑤尺(10/15秒)・縦横(16:9/9:16)・音。
2. **ベース画像**：無ければ `generate_image`（nano-banana-2, 4K, 指定アスペクト, テキスト/線なし）。
3. **ムーブボードを作る（コード描画）**：パスを設計し、Python(Pillow)で1本の連続曲線＋矢印＋番号＋動き説明ラベルをベース画像に重ねる。スクリプト雛形は正本レシピ「STEP2」。
4. **vp-core に渡す → プロンプト/ムーブボード承認ゲート**：ムーブボードを提示し「この動きでOK？/どこを変える？」。修正は**通過点の座標を直して描き直す**（一意・正確）。承認まで反復。
5. **生成（vp-core）**：model=`bytedance/seedance-2.0/reference-to-video`、`image_url`=承認済みムーブボード、短い動画プロンプト、尺/比率指定。`submit_video`→`check_status`。
6. **検証（vp-core）**：reference モードは赤線が出ない（頭トリック不要）。数フレーム抜いて線無し＆経路追従を確認。360°等が回りきらない/カットは #18。

## 鉄則
- ❌ `image-to-video` でムーブボードを起点にしない（赤線が映る／カメラが固定される）。
- ❌ ルート線を AI（generate_image/edit_image）に描かせない（2本目が出る）。
- ✅ パス設計はAI、線描画はコード、振り付けはラベル、動かすは reference-to-video。
- ✅ 大きな動き（フル360°等）は主役ビートに尺を割き、一定距離・速度で詰める（#18）。

生成・承認・連結ループは `vp-core` に委譲する。
