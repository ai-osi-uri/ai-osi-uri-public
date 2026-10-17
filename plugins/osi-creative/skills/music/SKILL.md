---
name: music
description: 動画のBGM・音楽を担う atomic スキル（narration と同格の能力アトミック）。①ブランドごとの「シグネチャー音源」を3〜5本作って使い回す設計、②AI生成（stable-audio-3 / lyria2 / cassetteai）とフリー音源（DOVA等）の使い分け、③映像のビート切り替えを曲の拍に合わせる音ハメ、④ffmpeg でのミックス（音量・フェード・途切れ防止）を扱う。「BGMを付けて」「音楽を作って」「この動画に合う曲を」「シグネチャー音源を作りたい」「テーマ曲を決めたい」「音ハメして」「BGMの音量を調整」「フリーBGMを探して」などで発動する。動画オーケストレータ ai-video-production および vp-* 各メソッドから「BGMパート」として呼ばれるほか、単体でも使える。ナレ音声は narration、映像生成は各 vp-* メソッドの担当。
requires_connectors:
  - server: ai-osi-uri-creative
    provision: user-install
    tools: [generate_music, submit_music, check_music, list_music_models]
# スキルの一覧（つないだときに Claude に渡す）に出す短い用途
label: BGM・音楽
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

**最小構成はシグネチャー曲3本**（例：前向き・温かい・静か）＋スティング。3本あれば、ほとんどの動画は「どれを敷くか選ぶだけ」で済む。
曲の条件：ボーカル無し／ナレと同じ帯域の楽器が前に出ない／最後は解決して終わる。決め台詞やつかみの瞬間を曲の小節の頭に合わせると気持ちよく見える。

音源はブランドキット `brandkit/<company>/music/` に置く。**曲ごとに出どころの記録 `SOURCE.md` を必ず添える**（下の「出どころの記録」）。（`../ai-video-production/references/brandkit.md`）。
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
- **ダウンロードは人が行う**（素材サイトから自動で一括取得しない）。使う前に、サイトの規約と曲・作者ごとの条件（作者の条件があればそちらが優先されることが多い）を確かめる。
- **曲のファイルは公開の場所に置かない**（Git リポジトリ・プラグイン・公開フォルダ）。多くの素材サイトは再配布・AI 学習への利用・ツールへの組み込みを禁じている。置くのは案件フォルダとブランドキットだけ。

## 出どころの記録（SOURCE.md）

フリー素材でも AI 生成でも、**使った曲には必ず `SOURCE.md` を1つ添える**（曲ファイルと同じフォルダ）。
後から規約を確かめ直せるように、また別の動画で使い回すときに条件を引き継げるようにするため。

```markdown
# SOURCE — <曲ファイル名>
- 種別: フリー素材 ／ AI 生成 ／ 委託制作
- 曲名 / 作者: <曲名> / <作者>
- URL: <曲のページ>
- サイトの規約: <規約の URL>（確かめた日: YYYY-MM-DD）
- 作者ごとの条件: <あり（内容）／サイトの規約に準拠>
- 商用利用: <可／不可>　SNS 動画での利用: <可／要確認（どの項目で判断したか）>
- クレジット表記: <要（文言）／不要>
- 加工: <切り出し 0:12〜0:47・ループ・フェード 等>（規約で可否を確かめた）
- AI 生成の場合: サービスとモデル <例 stable-audio-3>、生成日 YYYY-MM-DD、プロンプト全文
- 使った動画: <案件・動画名>
```

クレジット表記が要る曲は、その文言を動画の概要欄・投稿本文に入れる。

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

### ナレの区間だけ BGM を -20dB 下げる（ダッキング）

全体の音量を下げるだけだと、ナレの無い区間で音楽が痩せる。**ナレの間だけ -20dB 下げ、0.15秒で下げて 0.3秒で戻す**と、
間（ま）では音楽が戻ってくる。0.7秒より近いナレ区間はまとめる（音楽が細かく上下に揺れない）。

**方法A：区間を指定して下げる（確実・推奨）** — `scripts/duck_expr.py` が ffmpeg の volume 式を作る。
```bash
# ナレ音声（通しの1本）の無音検出で区間を取る。区間を確かめるだけなら --show-windows
EXPR=$(python3 scripts/duck_expr.py --from-audio narration.mp3)
#   区間が分かっているなら: python3 scripts/duck_expr.py --windows "2.0-5.0,7.0-9.0"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 voice.mp4)
ffmpeg -y -i voice.mp4 -i BGM.mp3 -filter_complex \
 "[1:a]atrim=0:$DUR,asetpts=N/SR/TB,aresample=48000,volume='pow(10,($EXPR)/20)':eval=frame,\
afade=t=in:st=0:d=1.2,afade=t=out:st=$(awk "BEGIN{print $DUR-2}"):d=2[b];\
  [0:a]aresample=48000[a0];[a0][b]amix=inputs=2:duration=first:normalize=0[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac final.mp4
```
- BGM の地の音量は、元の曲を先に `volume` で整えておく（ナレの無い区間でナレより少し下）。`normalize=0` にしないと amix が全体を勝手に下げる。
- 実測（2026-10・sine の BGM とナレ2区間で確認）：ナレの外 -27.1dB → ナレの間 -47.1dB（ちょうど -20dB）。

**方法B：ナレの音で自動に下げる（sidechaincompress）** — 区間を出さずに済むが、下がる量はナレの音量しだいで一定にならない。
```bash
ffmpeg -y -i BGM.wav -i narration.wav -filter_complex \
 "[1:a]asplit=2[sc][vo];[0:a][sc]sidechaincompress=threshold=0.02:ratio=20:attack=20:release=300:makeup=1[bg];\
  [bg][vo]amix=inputs=2:duration=first:normalize=0[a]" -map "[a]" mix.wav
```
- 同じ素材で約 -14dB だった（ratio・threshold で変わる）。「ナレの間だけ -20dB」を守りたいときは方法A。

仕上げに `volumedetect` で、ナレの区間と間の区間をそれぞれ測って差を確かめる（`ffmpeg -ss <秒> -t 0.5 -i mix.wav -af volumedetect -f null -`）。

## ユーザーへの出し方

- 新規ブランドなら、まず**シグネチャー音源の候補を3本**提示して選ばせる（1本ずつ聴かせない。並べて比べさせる）。
- 既存ブランドなら**音源は聞き返さない**。キットの `signature_*` を黙って使う（毎回聞くのが量産の敵）。
- フリー音源を使ったときは、ライセンス（商用可否・クレジット・Content IDリスク）を一言添える。

## やらないこと

- 動画1本ごとに新しい曲を生成する（→ シリーズに見えなくなる）
- ヒット曲・チャート曲を商用動画に使う
- ボーカル入りをナレの下に敷く
- ループ前提の音源で長尺を埋める（継ぎ目が"途切れ"に聞こえる）
