# scf2026-website

SCF2026 (Superconductors and Correlated materials Forum in 2026) の公式ウェブサイトのソースコード

## 開発・確認手順
1. VS Codeの拡張機能「Live Server」を使用して `index.html` を開く。
2. ローカル環境でプレビューを適宜確認しながら編集を行う。

## 運用のルール
* **`main` ブランチは直接編集しないでください。**
* 必ず作業用のブランチ（`feature/○○` など）を作成して作業を行う。
* 変更が完了したらGitHubへプッシュし、Pull Requestを作成して管理者（先生）にレビューを依頼する。

## 公開について
* このリポジトリの `main` ブランチに変更がマージ（合流）されると、GitHub Pagesを通じて自動的に実際のウェブサイトが更新される。

## 鳥取砂丘 Lunch & Sightseeing Map

- ページ: `sakyu-map.html`（公開想定パス: `/scf2026-website/sakyu-map.html`）
- トップページのナビゲーションとプログラム欄から移動できます。
- 従来どおり静的HTML/CSS/JavaScriptで動作します。ビルド・APIキー・サーバー側処理は不要です。
- `sakyu-map.css` は既存の `poster.html` の基本レイアウト・テーマ変数・フォントを再利用した新ページ専用CSSです。既存ページのCSSや共通モバイルメニューは変更していません。
- 表示方法とフィルターは同じ状態を共有します。「すべて」のリストは21地点と独立したイベント一覧、イベントの地図は会場B・Cの2地点を表示します。
- 近接ピンはクリック・Enter・SpaceでSpiderfy展開します。マーカーの座標はJSONの値をそのまま使用します。

### データ更新

`data/spots.json`（01〜16、A〜E）と `data/events.json`（EV01〜EV03）がWeb・今後のPDFの共通データです。店舗情報をHTMLやJavaScriptに複製せず、JSONを更新してください。

- `venueRef` でイベントを会場スポットに紐付けます。イベント専用ピンは作成しません。
- `officialUrl: null` は公式サイトボタンを非表示にします。
- `status` は運営用で、参加者向け画面には表示しません。
- フッターの最終確認日は全データの `lastVerified` の最大値です。
- `sessions` は実際の開催時間、`scfEventHours` はSCF観光時間内に参加可能な時間として別々に表示します。
- 提供された営業情報・座標は変更していません。`recheck` 対象は04 スカット、05 ジェラート専門店さんこうえん、06 海鮮丼 鯛喜、07 砂丘の家レイガーデン、11 SUGAR HIGH、14 鳥取牛骨拉麺 八起、15 砂丘コーヒー、16 サンコスモスです。

### 地図ライブラリ

互換性を固定するため、配布ファイルを `vendor/` に同梱しています。ランタイムにCDNからJavaScriptを取得する必要はありません。

- [Leaflet 1.9.4](https://leafletjs.com/) — BSD-2-Clause、`vendor/leaflet/LICENSE`
- [Leaflet.markercluster 1.5.3](https://github.com/Leaflet/Leaflet.markercluster) — MIT、`vendor/leaflet.markercluster/MIT-LICENCE.txt`
- 取得元: `https://unpkg.com/leaflet@1.9.4/`、`https://unpkg.com/leaflet.markercluster@1.5.3/`
- 地図タイル: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`。帰属表示を常時表示し、[OSMタイル利用方針](https://operations.osmfoundation.org/policies/tiles/)に沿って通常のブラウザキャッシュを利用します。先読み・一括取得・オフライン保存は行いません。地図画像の表示にはインターネット接続が必要です。

### ローカル確認

Live Server、またはリポジトリ直下で次を実行してください。

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

`http://127.0.0.1:8765/sakyu-map.html` を開きます。JSONをfetchするため、`file://` で直接開かずHTTPサーバーを利用してください。

### 操作テスト（開発時のみ）

PythonとGoogle Chromeがある環境で、一時環境などにPlaywrightをインストールします。これはテスト専用で、サイトの公開依存ではありません。

```sh
python3 -m venv /tmp/scf-map-test-env
/tmp/scf-map-test-env/bin/pip install playwright
/tmp/scf-map-test-env/bin/python -m unittest discover -s tests -v
```

`SCF_SCREENSHOT_DIR=/tmp/scf-map-screenshots` を指定すると画面画像も保存します。テストは一時HTTPサーバーを起動し、GitHub Pagesと同じプロジェクト配下のパスで確認します。21地点・3イベント、カテゴリ、状態共有、同一座標のSpiderfy、ボトムシート、キーボード操作、イベント詳細、リンク、360/390/430/768/1024/1440px幅と既存ナビゲーションを検証します。

### 公開前の確認事項

通常のmainへのマージで公開できます。GitHub Pagesの設定変更や追加のビルド作業はありません。参考資料 `2026sakyu.pdf` は実装時点でリポジトリに含まれていないため、同資料とのデザイン照合は未実施です。今回PDF版は作成していません。
