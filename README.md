# 世界遺産マップ

世界遺産・登録抹消・暫定リストを地図で見るアプリ（PWA）。スマホでホーム画面に追加すると全画面で開き、一度開けばオフラインでも使えます。

## ファイル

- `index.html` … アプリ本体
- `heritage_map.json` … 遺産の一覧と位置
- `world-50m.json` … 背景の国境データ（[Natural Earth](https://www.naturalearthdata.com/)、world-atlas）
- `photos/` … ポップアップの写真。`index.json` に写真のある遺産の番号、`pNN.json` に画像（遺産の番号 % 20 番目のファイル）
- `vendor/` … [Leaflet](https://leafletjs.com/) 1.9.4、Leaflet.markercluster 1.5.3、topojson-client 3.1.0
- `manifest.webmanifest`, `sw.js`, `icons/` … PWA 用

## 写真について

写真は Wikimedia Commons のもので、撮影者とライセンスを各ポップアップに表示しています。各写真のライセンス（CC BY-SA など）はそれぞれの Commons のページに従います。

## 更新のしかた

ファイルを変えたら `sw.js` の `VERSION` を上げてください（スマホに保存された古い版が入れ替わります）。
