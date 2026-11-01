# 📈 Max Sharpe Portfolio Analyzer


<p align="center">
  <a href="https://kurata.streamlit.app/">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg">
  </a>
</p>

## Demo : [アプリを開く](https://kurata.streamlit.app/)


現代ポートフォリオ理論（MPT）に基づき、**シャープレシオを最大化する最適な資産配分**を求める株式ポートフォリオ分析ツールです。

> ⚠️ **免責事項**: 本ツールは過去データに基づく分析を行います。過去の運用実績は将来の運用成果を保証するものではありません。投資判断はご自身の責任で行ってください。

---

## 特徴

- **最適化**: PyPortfolioOpt による最大シャープレシオ（Ledoit-Wolf 共分散推定）
- **データ取得**: Yahoo Finance から月次株価を自動取得（上場廃止銘柄のフォールバック対応）
- **多国市場対応**: 日本・米国・英国・独・仏・中国・香港・インドの主要ベンチマークと自動 FX 換算
- **UI / Notebook の二形態**: ブラウザ操作できる Streamlit アプリと、カスタマイズ自由な Jupyter Notebook
- **日英バイリンガル UI**: Web アプリの表示言語を日本語 / 英語で切替可能
- **豊富なチャート**: 累積リターン・効率的フロンティア・ローリングシャープレシオ・最大ドローダウン
- **エクスポート**: Excel・JSON・ZIP（チャート画像込み）で結果をダウンロード

---

## 動作環境

- Python 3.10 以上
- 主要ライブラリ

| ライブラリ | バージョン | 用途 |
|---|---|---|
| streamlit | ≥1.35.0 | Web UI |
| yfinance | ≥0.2.40 | 株価データ取得 |
| PyPortfolioOpt | ≥1.5.5 | ポートフォリオ最適化 |
| pandas / numpy | ≥2.0 / ≥1.26 | データ処理 |
| altair / matplotlib | ≥5.3 / ≥3.8 | チャート描画 |
| openpyxl | ≥3.1.2 | Excel 出力 |

---

## インストール

```bash
git clone https://github.com/mayjet/StockSharpeKit.git
cd StockSharpeKit
pip install -r requirements.txt
```

---

## 使い方

### 1. Web アプリ（Streamlit）

ローカルの場合は

```bash
streamlit run app.py
```

ブラウザが自動で開きます（デフォルト: http://localhost:8501）。

**操作フロー**

1. **銘柄入力**: ティッカーコードを入力し、候補から銘柄を確認・登録
2. **パラメータ設定**: ポートフォリオ名・分析期間・無リスク金利・対象国などを設定
3. **実行**: 「分析実行」ボタンをクリック → 価格ダウンロードと最適化が自動で走る
4. **結果確認**: 最適ウェイト・パフォーマンス比較・各種チャートを確認
5. **ダウンロード**: Excel・JSON・ZIP 形式でエクスポート

> 結果は `portfolios/<ポートフォリオ名>_<日時>/` に自動保存されます。

#### Docker を使う場合

```bash
docker compose -f build/docker-compose.yml up
```

---

### 2. Jupyter Notebook

```bash
jupyter notebook portfolio_analysis_notebook.ipynb
```

分析したい銘柄コードを `tickers.txt` に1行1コード（または複数をカンマ区切り）で記述してから実行します。

```
# tickers.txt の例
9433
6861,4733
```

Notebook はデータ取得・前処理・最適化・可視化・エクスポートの全工程をセルごとに確認しながら実行できます。分析ロジックのカスタマイズや実験的な検証に適しています。

---

## 設定ファイル

### `benchmarks.json5`

国・地域ごとのベンチマーク指数と FX 換算ティッカーを定義します。

| キー | ベンチマーク | 基準通貨 |
|---|---|---|
| `JP` | 日経 225・TOPIX | JPY |
| `US` | S&P 500・NASDAQ 100・DJIA | USD |
| `GB` | FTSE 100 | GBP |
| `DE` | DAX | EUR |
| `HK` | ハンセン指数 | HKD |
| `IN` | NIFTY 50 | INR |
| `DEFAULT` | S&P 500 | USD |

### `tickers.txt`（Notebook 用）

Notebook 実行時に読み込む銘柄コードのリスト。1行につき1コードまたはカンマ区切りで複数指定できます。

---

## 出力・エクスポート

| ファイル | 内容 |
|---|---|
| `analysis_results.xlsx` | 入力設定・最適ウェイト・パフォーマンス指標（3シート） |
| `resolved_symbols.xlsx` | 確認済みティッカーとメタデータ |
| `output.json` | ウェイト・リターン・リスク指標（機械可読形式） |
| `*.png` | 各種チャート画像（ZIP でまとめてダウンロード可能） |
| `portfolios/<name>_<datetime>/` | 上記を含む自動保存フォルダ |

---
