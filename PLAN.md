# Plan: gunnersaurus TUI（改訂版）

## Context

Arsenal マスコット「ガンナーザウルス」のドット絵をターミナルに表示するループアニメーション TUI アプリ。
ASCII アートではなく、PNG ピクセルデータを True Color ANSI + 半ブロック文字（▀）でそのままターミナルに再現する。
GitHub Profile の見栄えを良くするためのポートフォリオ OSS として公開する。

- コマンド名: `gunnersaurus`
- リポジトリ: `github.com/yuki-f-saka/gunnersaurus`
- 動作: 起動するとガンナーザウルスがまばたきループアニメーションし続ける。Ctrl+C で終了

---

## 技術スタック

- **Python 3.10+**
- **Pillow** — PNG 読み込み・ピクセル操作・フレーム生成
- **True Color ANSI** — `\033[38;2;R;G;Bm`（前景）/ `\033[48;2;R;G;Bm`（背景）
- **半ブロック文字 ▀（U+2580）** — 1ターミナル行で縦2ピクセルを表現
- **rich** — ちらつきなしのアニメーションループ（`rich.live.Live`）
- ASCII 文字・ANSI 8色は使わない

---

## レンダリング方式

```
ターミナル 1行 = ピクセル 2行分

  pixel[x, y*2]   → ▀ の前景色（上半分）  \033[38;2;R;G;Bm
  pixel[x, y*2+1] → ▀ の背景色（下半分）  \033[48;2;R;G;Bm

アルファ値 < 128 のピクセル → 黒 (0,0,0) 扱い
各行末に \033[0m でリセット
```

---

## まばたきアニメーションのフレーム生成方針

1. `images/Gemini_Generated_Image_wd07e1wd07e1wd07.png` をベーススプライトとして読み込む
2. 目の領域を色・座標で特定（白〜黄系の明るいピクセルが頭部上方に集中している箇所）
3. 目の開閉を以下のように合成して複数フレームを生成:
   - Frame 0–3: 目開き（ベース画像のまま）
   - Frame 4:   目半閉じ（目領域の上半分を肌色で塗りつぶし）
   - Frame 5:   目閉じ（目領域全体を肌色で塗りつぶし）
   - Frame 6:   目半閉じ
   - Frame 7–9: 目開き
4. 各フレームを `render_frame(img)` で ▀ 文字列に変換してループ再生

---

## プロジェクト構成

```
gunnersaurus/
├── gunnersaurus.py          # エントリポイント（Ctrl+C 処理・起動）
├── renderer.py              # PNG Image → ▀ True Color 文字列
├── animation.py             # フレーム生成（まばたき）+ アニメーションループ
├── images/
│   └── Gemini_Generated_Image_wd07e1wd07e1wd07.png   # ベーススプライト
├── requirements.txt         # pillow, rich
├── .gitignore
└── README.md
```

---

## セッション計画

### Session 1: スプライト画像の準備 ✅ 完了

**成果物**: `images/Gemini_Generated_Image_wd07e1wd07e1wd07.png`（ガンナーザウルスのドット絵）

---

### Session 2: PNG → ▀ True Color レンダリング

**目標**: `python gunnersaurus.py` で PNG がターミナルにドット絵として表示される

**作業内容**:
- `renderer.py` を実装
  - Pillow で PNG 読み込み（RGBA モード）
  - 2ピクセル行 → 1ターミナル行の変換ループ
  - `\033[38;2;R;G;Bm▀\033[48;2;R;G;Bm` 形式の文字列生成
  - アルファ < 128 は `(0,0,0)` 扱い
- `gunnersaurus.py` でとりあえず1フレーム表示して終了

**完了条件**: 実行するとドット絵がターミナルに忠実に表示される

---

### Session 3: まばたきアニメーションループ

**目標**: `python gunnersaurus.py` でスムーズなまばたきループ、Ctrl+C で正常終了

**作業内容**:
- `animation.py` を実装
  - 目ピクセルの座標検出（色閾値ベース）
  - まばたきフレーム生成（目領域を肌色で上書き）
  - `rich.live.Live` で一定間隔（100ms）ごとにフレームを切り替え
  - 起動時にカーソル非表示、終了時に復元
- Ctrl+C → graceful shutdown（カーソル表示復元してターミナルを壊さない）

**完了条件**: スムーズなループ、Ctrl+C で正常終了

---

### Session 4: ポリッシュ + GitHub 公開

**目標**: `pipx install git+https://github.com/yuki-f-saka/gunnersaurus` で動く OSS

**作業内容**:
- `pyproject.toml` / `setup.py` 整備（`gunnersaurus` コマンドとして登録）
- `requirements.txt` + `.gitignore`
- README.md: 概要・インストール方法・デモ GIF（`vhs` で録画）
- `git push` + GitHub Profile の README に紹介追加

**完了条件**: GitHub リポジトリが完成し、pipx install でインストール・実行できる

---

## 参考

- 半ブロック文字レンダリング: `▀`（U+2580）= 上半分塗りつぶし
- True Color ANSI: `\033[38;2;R;G;Bm`（前景）/ `\033[48;2;R;G;Bm`（背景）
- rich Live: https://rich.readthedocs.io/en/stable/live.html
- ベーススプライト: `images/Gemini_Generated_Image_wd07e1wd07e1wd07.png`
