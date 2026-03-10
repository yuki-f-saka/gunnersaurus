# gunnersaurus

ターミナルでガンナーザウルス（Arsenal FC マスコット）が踊る ASCII アートアニメーション TUI アプリ。

```
   ____
  /\  /\
 / \  / \
(  ( )( )  )
 \ /  \ /
  |    |
  |____|
```

> Ctrl+C で終了

---

## インストール

```sh
go install github.com/yuki-f-saka/gunnersaurus@latest
```

Go 1.21+ が必要です。

## 使い方

```sh
gunnersaurus
```

起動するとガンナーザウルスがターミナルでループアニメーションします。`Ctrl+C` で終了。

## ビルド

```sh
git clone https://github.com/yuki-f-saka/gunnersaurus.git
cd gunnersaurus
go build ./cmd/gunnersaurus
./gunnersaurus
```

## ライセンス

MIT
