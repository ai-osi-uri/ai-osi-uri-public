# ガント／図の実装テクニック（proposal-estimate 用）

骨子と構成が固まってから読む。中身の判断ではなく「描き方」のメモ。

## 月単位ガントの描画

ガントはプログラマティックに描く。注意点：

- 各バーの開始位置と幅を月単位で計算する
- バーの右端が描画領域を超えないよう `Math.min()` でクランプする
- 月の境界線はグリッドラインとして明確に描く
- タスク名が長い場合はフォントを小さくするか改行する
- 凡例をガント下に置きカテゴリ色を説明する

## 立ち上げ期の週次ロードマップ（W1〜W8）

- 横軸を W1〜W8 の週グリッドにする。ヘッダ行は単色ダーク（`111827`）でニュートラルに
- タスクのバーはワークストリーム別に色分けし、凡例で示す（フェーズ色とは兼用しない）
- 「契約全体は◯ヶ月。本ロードマップは立ち上げ2ヶ月（8週）を週次で詳細化」と注記し、長期契約と矛盾させない
- 月単位ガントと週次ロードマップは併用可。短期で握りたい案件では週次ロードマップだけでも機能する

## SVG → PNG（pptxgenjs のシェイプで描きにくい図）

サイクル図・フロー図など、シェイプだけでは難しい図は SVG → PNG 変換で対応：

```javascript
const sharp = require("sharp");

// SVG を文字列として組み立て
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900">...</svg>`;

// sharp で PNG に変換
const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
const imageData = "image/png;base64," + pngBuffer.toString("base64");

// pptxgenjs に画像として追加
slide.addImage({ data: imageData, x: 2, y: 0.8, w: 5.8, h: 4.35 });
```

画像のアスペクト比に注意。SVG の viewBox と addImage の w/h を合わせないと歪む。
