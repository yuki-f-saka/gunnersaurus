# Plan: gunnersaurus TUI

## Context

Arsenal マスコット「ガンナーザウルス」を ASCII アートでターミナルに表示するループアニメーション TUI アプリ。Ghostty のゴーストマスコットと同様のアプローチ。GitHub Profile の見栄えを良くするためのポートフォリオ OSS として公開する。

- バイナリ名: `gunnersaurus`
- リポジトリ: `github.com/yuki-f-saka/gunnersaurus`（新規独立リポジトリ）
- 動作: 起動するとガンナーザウルスがループアニメーションし続ける。Ctrl+C で終了

---

## 技術スタック

- **Go 1.21+**（`//go:embed` でアセットをバイナリに埋め込み）
- **ANSI エスケープコード**（カーソル制御・Arsenal 赤のカラーリング）
- **外部ライブラリなし** or **lipgloss のみ**（bubbletea は不要。インタラクションなし）
- フレームデータ: `assets/frames.json`（JSON 配列でフレーム文字列を管理）

---

## プロジェクト構成

```
gunnersaurus/
├── cmd/
│   └── gunnersaurus/
│       └── main.go          # エントリポイント（最小限）
├── internal/
│   └── animation/
│       ├── frames.go        # //go:embed + フレーム読み込み
│       └── render.go        # ANSI レンダリング・ループ制御
├── assets/
│   └── frames.json          # ASCII アートフレーム配列
├── go.mod
├── .gitignore
└── README.md
```

---

## セッション計画

### Session 0: リポジトリ作成（最初にやること）

**目標**: GitHub にリポジトリを作成し、PLAN.md をコミット

**作業内容**:
- `gh repo create yuki-f-saka/gunnersaurus --public` でリポジトリ作成
- ローカルに clone
- このプランファイルを `PLAN.md` として配置してコミット・プッシュ

**完了条件**: `github.com/yuki-f-saka/gunnersaurus` が存在し、PLAN.md がある

---

### Session 1: ASCII アートデザイン

**目標**: `assets/frames.json` を完成させる

**作業内容**:
- tmux で左ペイン: Claude Code / 右ペイン: `cat` プレビュー用ターミナル
- ガンナーザウルスの ASCII アートを描く（サイズ目安: 幅 40 × 高さ 20 程度）
- idle ループ用フレームを 8〜12 枚設計（首を振る、しっぽを振るなど）
- フレームを JSON 形式で保存: `{"frames": ["frame1\n...", "frame2\n...", ...]}`
- Arsenal カラーのための ANSI コードをフレームに埋め込む（赤 `\033[31m`）

**完了条件**: `cat assets/frames.json` で確認したとき、各フレームが意図通りに見える

---

### Session 2: Go プロジェクト初期化 + 単体フレーム描画

**目標**: `go run ./cmd/gunnersaurus` で1フレームが正しく描画される

**作業内容**:
- `git init` + `go mod init github.com/yuki-f-saka/gunnersaurus`
- `internal/animation/frames.go`: `//go:embed assets/frames.json` でフレーム読み込み
- `internal/animation/render.go`: 1フレームを ANSI コードで描画する関数
- `cmd/gunnersaurus/main.go`: フレーム0を描画して終了

**完了条件**: `go run ./cmd/gunnersaurus` を実行するとターミナルにガンナーザウルスが表示される

---

### Session 3: アニメーションループ実装

**目標**: `go run ./cmd/gunnersaurus` でスムーズなループアニメーション

**作業内容**:
- `render.go` にアニメーションループを実装
  - `time.Ticker` で 80ms ごとにフレームを進める（約 12fps）
  - スクリーンクリアでなくカーソル先頭移動（`\033[H`）で描画してちらつきを防ぐ
- `os/signal` で Ctrl+C をキャッチ → カーソル表示を復元して終了
- 起動時にカーソルを非表示 (`\033[?25l`)、終了時に復元 (`\033[?25h`)

**完了条件**: ループがスムーズに動き、Ctrl+C で正常終了してターミナルが壊れない

---

### Session 4: ポリッシュ + GitHub 公開

**目標**: `go install github.com/yuki-f-saka/gunnersaurus@latest` で動く OSS

**作業内容**:
- README.md: 概要・インストール方法・デモ GIF（`vhs` で録画）
- `.gitignore` 追加
- GitHub で `yuki-f-saka/gunnersaurus` リポジトリを作成
- `git push` + GitHub Profile の README に紹介を追加

**完了条件**: GitHub のリポジトリページが完成し、`go install` でインストールできる

---

## 各セッションの開始方法

新しいセッションでは以下を伝えるだけで続きから始められる:

> 「このファイルを読んでセッション N を始めて: ~/.claude/plans/merry-chasing-falcon.md」

---

## 参考

- Ghostty のアニメーション方式: JSON フレーム配列 + ANSI コード埋め込み
- gostty（Go 実装の参考）: https://github.com/ashish0kumar/gostty
- フレームサイズ: 77×41 が Ghostty 標準。ガンナーザウルスは 40×20 程度でコンパクトに
