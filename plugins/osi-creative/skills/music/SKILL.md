---
name: music
description: 動画のBGM・音楽を担う atomic スキル（narration と同格の能力アトミック）。①ブランドごとの「シグネチャー音源」を3〜5本作って使い回す設計、②AI生成（stable-audio-3 / lyria2 / cassetteai）とフリー音源（DOVA等）の使い分け、③映像のビート切り替えを曲の拍に合わせる音ハメ、④ffmpeg でのミックス（音量・フェード・途切れ防止）を扱う。「BGMを付けて」「音楽を作って」「この動画に合う曲を」「シグネチャー音源を作りたい」「テーマ曲を決めたい」「音ハメして」「BGMの音量を調整」「フリーBGMを探して」などで発動する。動画オーケストレータ ai-video-production および vp-* 各メソッドから「BGMパート」として呼ばれるほか、単体でも使える。ナレ音声は narration、映像生成は各 vp-* メソッドの担当。
version: 0.1.0
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_music, submit_music, check_music, list_music_models]
---

# music — BGM／シグネチャー音源

動画に音楽を付ける atomic スキル。**「毎回いい曲を作る」のではなく「ブランドの曲を決めて使い回す」**のが中核の設計。

## ★ 最重要の設計判断：BGMは毎回生成しない

短尺動画を**量産する**前提では、1本ごとに別の曲を生成すると、10本並べたときに「同じ会社の動画」に聞こえない。

> **ブランドごとに シグネチャー音源を3〜5本だけ先に作り、以後はそれを使い回す。**

| 音源ID | 性格 | 使いどころ |
|---|---|---|
| `signature_a` | 芯・信頼 | 企業版（`vp-corporate-card`）の標準 |
| `signature_b` | 疾走・前向き | 個人版（`vp-personal-intro`）の標準、採用系 |
| `signature_c` | 静・余韻 | 士業・医療、B5（動機）を効かせたいとき |
| `sting` | 2秒のロゴ音 | **全動画のB6に共通で置く＝耳のロゴ** |

音源はブランドキット `brandkit/<company>/music/` に置く（`../ai-video-production/references/brandkit.md`）。
**新規案件で最初にやるのは「曲を作ること」ではなく「この4本を決めること」。**

### 人のプロに頼むならどこか

AIが弱いのは**トップライン（メロディと展開の設計）**。ここは毎本ではなく**ブランドに1回**効かせるのが費用対効果が高い。

- **シグネチャー音源の制作＝人のプロ枠**（作曲家・音楽プロデューサー、プロ向けツール）
- **各動画への適用・音ハメ・ミックス＝AI／スクリプト枠**

依頼するときは「動画ごとに曲を作ってもらう」ではなく「**設計思想＋3〜5本**」の単位で頼む。

## モデル選択（AI生成する場合）

| slug | 実体 | 最大尺 | 使いどころ |
|---|---|---|---|
| **`stable-audio-3`** ★既定 | Stable Audio 3 Medium | 6分20秒 | 長尺も一発生成でループ不要。学習データが全てライセンス済みで商用リスクが低い |
| `lyria2` | Google Lyria 2 | 30秒 | **30秒の動画名刺・スティングにちょうどよい**。ワンフレーズ完結 |
| `cassetteai` | CassetteAI | 3分 | 最安クラス（$0.02/出力分） |
| `stable-audio-3-sfx` | Stable Audio 3 Small SFX | 2分 | 効果音 |
| `stable-audio` | Stable Audio Open（レガシー） | 47秒 | ループ必須で継ぎ目が出る。**新規では使わない** |

**15秒／30秒の動画名刺はワンフレーズ完結で足りる** → `lyria2` か `stable-audio-3` の一発生成。ループ不要なので継ぎ目問題が構造的に消える。

### 生成プロンプトの型

```
[GENRE] warm minimal piano with soft strings
[TEMPO] 92 BPM
[MOOD] confident, hopeful, understated
[STRUCTURE] gentle 4-bar intro, lift at 0:08, resolve at 0:26
[MIX] no vocals, no drums after 0:24, leaves room for narration
```

- **必ず `no vocals` を入れる**（ナレの邪魔になる）。
- **ナレの居場所を空ける**指示（`leaves room for narration` / 中域を空ける）を書く。
- シグネチャー音源は**同じプロンプトの語彙を共有**して3本作る（性格だけ差し替える）＝兄弟に聞こえる。

## フリー音源を使う場合

ショート／SNS狙いで「今っぽさ・流行り感」が欲しいときは、AI生成よりフリー音源が刺さることがある。
**調査→選定→取得→著作権確認の定型は `references/bgm-selection.md` が正本。**

要点だけ：
- **ヒット曲は商用利用ほぼ不可**（アプリ内ライブラリの包括契約は個人・非商用向け）。焼き込んでアプリ外配信すると原盤権侵害。
- **DOVA-SYNDROME** は商用OK・クレジット不要・加工OK。**魔王魂**はクレジット条件あり。**甘茶の音楽工房**は商用OK。
- クラシックは作曲がPDでも**演奏音源の権利は別**。PD/CCの音源を使う。

## 音ハメ（映像のビートに合わせる）

映像のカット切り替えを曲の拍に合わせると、短尺の疾走感が跳ね上がる。
**手順の正本は `../vp-seamless-journey/references/music-vibration.md`。**

動画名刺（6ビート）での当て方：

| ビート | 音楽側 |
|---|---|
| B1（0–3s） | イントロ。音を薄く、B1の最後で1拍入れる |
| B2（3–8s） | 主旋律の入り。**名乗りと同時に曲が立ち上がる** |
| B3–B4（8–24s） | 一定。ナレが主役なので音は下げる |
| B5（24–28s） | 一度**抜く**（動機はナレだけで聞かせる） |
| B6（28–30s） | **スティング**を重ねて締める |

## ミックス（ffmpeg）

- **曲尺 ≥ 動画尺**の曲を選ぶ（`stream_loop` のループ継ぎ目は"途切れ"に聞こえる）。足りないときは `acrossfade` で繋ぐ。
- 音量 **volume=0.16〜0.18**（ナレの下に敷く）。ナレと被る箇所はさらに下げる。
- 冒頭 1.2秒 fade in、**末尾は2秒かけて fade out**（ブツ切り防止）。
- 仕上げに `volumedetect` で末尾1秒の mean_volume を確認し、途切れが無いことを担保する。

```bash
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 voice.mp4)
FOUT=$(awk "BEGIN{print $DUR-2.2}")
ffmpeg -y -i voice.mp4 -i BGM.mp3 -filter_complex \
 "[0:a]volume=1.0[a0];\
  [1:a]atrim=0:$DUR,asetpts=N/SR/TB,volume=0.17,afade=t=in:st=0:d=1.2,afade=t=out:st=$FOUT:d=2.2[b];\
  [a0][b]amix=inputs=2:duration=first:dropout_transition=0[a]" \
 -map 0:v -map "[a]" -t "$DUR" -c:v copy -c:a aac -ar 48000 final.mp4
```

## ユーザーへの出し方

- 新規ブランドなら、まず**シグネチャー音源の候補を3本**提示して選ばせる（1本ずつ聴かせない。並べて比べさせる）。
- 既存ブランドなら**音源は聞き返さない**。キットの `signature_*` を黙って使う（毎回聞くのが量産の敵）。
- フリー音源を使ったときは、ライセンス（商用可否・クレジット・Content IDリスク）を一言添える。

## やらないこと

- 動画1本ごとに新しい曲を生成する（→ シリーズに見えなくなる）
- ヒット曲・チャート曲を商用動画に使う
- ボーカル入りをナレの下に敷く
- ループ前提の音源で長尺を埋める（継ぎ目が"途切れ"に聞こえる）
