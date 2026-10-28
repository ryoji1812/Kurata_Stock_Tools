"""
lang.py — Language dictionary and translation helper.
All UI text is defined here. Use get_text(key, lang) to translate.
"""

_L: dict[str, dict[str, str]] = {
    "JP": {
        # ── App ────────────────────────────────────────────────────────────
        "app_notice": (
            "本アプリは **日経ストックリーグ** 向けのポートフォリオ分析ツールです。"
            "過去の株価データをもとに最適配分を計算し、**分析結果・データの提供のみ**を目的としています。"
            "投資の利益を確実に保証するものではありません。"
        ),
        "app_description": (
            "候補銘柄を入力すると、**シャープレシオ（リターン÷リスク）が最大**になる"
            "配分比率を自動計算します。"
        ),
        # ── Basic settings ─────────────────────────────────────────────────
        "label_portfolio_name": "ポートフォリオ名",
        "label_period":         "分析期間",
        "label_start_date":     "分析開始日",
        "label_end_date":       "分析終了日",
        # ── Advanced settings ──────────────────────────────────────────────
        "section_period":      "📅 期間設定",
        "section_period_settings": "分析期間・設定",
        "section_advanced":    "⚙️ 詳細設定",
        "label_risk_free_rate": "無リスク金利",
        "desc_risk_free_rate":  "シャープレシオ計算に使う金利（% で入力）",
        "label_min_weight":     "最小投資比率",
        "desc_min_weight":      "各銘柄への最小割り当て比率（% で入力、0 = 制約なし）",
        "warn_min_weight":      "最小投資比率を 0% 以外に設定すると効率的フロンティアの信頼性が低下します",
        "label_user_country":   "対象国",
        "desc_user_country":    "銘柄検索の優先国とベンチマーク指数の選択に使用",
        "label_mdd_threshold":  "最大ドローダウン閾値",
        "desc_mdd_threshold":   "これを超える下落率の銘柄を効率的フロンティア上で赤くハイライト（除外はしない）",
        "label_min_months":     "短期銘柄判定（月数）",
        "desc_min_months":      "この月数未満のデータしかない銘柄を短期銘柄として点線表示",
        # ── Symbol input ───────────────────────────────────────────────────
        "section_symbols":    "📋 銘柄入力",
        "sym_table_hint":     "証券コードまたは日本株の銘柄名（例: トヨタ）を入力し、候補から選んで確定してください。複数を「,」や改行で区切って一度に貼り付けることもできます。",
        "edinet_attribution": "銘柄名検索には、EDINET（金融庁）が公開する「EDINETコードリスト」を加工して使用しています。"
                              "出典: [EDINET（金融庁）](https://disclosure2.edinet-fsa.go.jp/) ／ "
                              "[公共データ利用規約（第1.0版）](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0) ／ "
                              "加工: Ryoji Okoshi",
        "col_symbol":         "コード",
        "col_name":           "銘柄名",
        "col_exchange":       "取引所",
        "col_country":        "国",
        "col_status":         "状態",
        "status_confirmed":   "✅ 確定",
        "status_not_found":   "⚠️ 見つかりません",
        "btn_add_symbol":     "＋ 銘柄を追加",
        "btn_run":            "▶ 分析を実行",
        "placeholder_symbol": "例: 6861",
        "suggestion_header":  "候補（クリックで確定）",
        "warn_has_unconfirmed":  "⚠️ 未確認の銘柄があります。全銘柄を確定してから実行してください。",
        "warn_no_confirmed":     "⚠️ 銘柄が入力されていません。",
        "warn_no_start_date":    "⚠️ 分析開始日を選択してください。",
        "warn_date_order":       "⚠️ 分析開始日は終了日より前にしてください。",
        # ── Progress ───────────────────────────────────────────────────────
        "step_download":  "株価データを取得中...",
        "step_shortterm": "短期銘柄を確認中...",
        "step_mdd":       "最大ドローダウンを計算中...",
        "step_optimize":  "ポートフォリオを最適化中...",
        "step_risk":      "リスク指標を計算中...",
        "step_bench":     "ベンチマークと比較中...",
        "step_done":      "✅ 分析完了",
        "analysis_error": "分析中にエラーが発生しました",
        # ── Results sections ───────────────────────────────────────────────
        "section_weights":    "最適投資比率",
        "desc_weights": (
            "シャープレシオが最大になるよう各銘柄への配分比率を最適化した結果です。"
            "比率が高い銘柄ほど、この期間でリスクあたりのリターンが高かったことを示します。"
        ),
        "section_performance": "パフォーマンス比較",
        "desc_performance": (
            "ポートフォリオと市場指数の成績を比較します。"
            "ベータが1未満なら市場全体より値動きが小さく、"
            "情報比率が高いほどベンチマーク超過リターンの安定性が高いことを示します。"
            "※上部の「期待年率リターン／シャープレシオ」は最適化の理論推定値です。"
            "この表の値は実際の月次リターン系列から計算した実績値のため、数値が異なります。"
        ),
        "section_comparison_funds": "比較ファンド（任意）",
        "comp_fund_hint": "比較対象のファンドの銘柄を入力してください。メインと同じ最適化処理を行い、1つのファンドとして全比較チャートに表示されます。",
        "comp_fund_name_label": "比較ファンド名",
        "comp_fund_name_placeholder": "例: テック系ファンド",
        # ── Multi-fund UI ──────────────────────────────────────────────────
        "section_funds":          "📋 ファンド管理",
        "fund_list_header":       "ファンド一覧",
        "fund_name_label":        "ファンド名",
        "fund_name_placeholder":  "例: テック系ファンド",
        "fund_symbols_label":     "投資銘柄",
        "btn_add_fund":           "＋ ファンドを追加",
        "btn_del_fund":           "削除",
        "fund_default_name":      "ファンド",
        "fund_confirmed_count":   "銘柄 確定済み",
        "fund_chart_style_label": "グラフの色",
        "fund_line_style_label":  "線のスタイル",
        "fund_tab_empty":         "ファンドを追加してください",
        "warn_no_funds":          "⚠️ ファンドが作成されていません。",
        "warn_fund_no_confirmed": "⚠️ 確定済み銘柄のないファンドがあります: {names}",
        "section_chart_colors": "グラフのスタイル設定",
        "color_portfolio_label": "ポートフォリオ",
        "color_bench_label": "ベンチマーク",
        "col_header_series": "系列名",
        "col_header_color": "色",
        "col_header_style": "線のスタイル",
        "style_solid": "実線",
        "style_dashed": "破線",
        "style_dotted": "点線",
        "style_dashdot": "一点鎖線",
        "section_cum_bar":  "累積リターン比較",
        "desc_cum_bar":     "分析期間全体の合計リターンを棒グラフで比較します。",
        "section_frontier": "効率的フロンティア",
        "desc_frontier": (
            "横軸がリスク（値動きの大きさ）、縦軸がリターン（利益率）です。"
            "★が今回の最適ポートフォリオ、赤い点は大きな下落を経験した銘柄です。"
        ),
        "section_cum_line": "累積リターン推移",
        "desc_cum_line":    "投資開始時を0%として時系列のリターン推移を表します。",
        "section_rolling":  "ローリング・シャープレシオ（12ヶ月窓）",
        "desc_rolling": (
            "直近12ヶ月のリスクあたりリターンの推移です。"
            "0を下回る期間は損失局面を示します。"
        ),
        "section_drawdown": "ドローダウン推移",
        "desc_drawdown":    "過去のピークからの下落率を時系列で示します。深いほど大きな損失局面です。",
        # ── DataFrame columns ──────────────────────────────────────────────
        "col_portfolio":   "ポートフォリオ/指数",
        "col_sharpe":      "シャープレシオ",
        "col_ann_return":  "年率平均リターン",
        "col_ann_risk":    "年率リスク",
        "col_cum_return":  "累積リターン",
        "col_beta":        "ベータ",
        "col_var":         "VaR(95%)",
        "col_cvar":        "CVaR(95%)",
        "col_ir":          "情報比率",
        "col_ticker_name": "銘柄名/証券コード",
        "col_weight":      "投資比率 (%)",
        "col_total":       "合計",
        # ── Chart axis / legend labels ─────────────────────────────────────
        "chart_date":           "日付",
        "chart_cum_ret":        "累積リターン (%)",
        "chart_sharpe":         "シャープレシオ",
        "chart_drawdown_pct":   "ドローダウン (%)",
        "chart_risk":           "年率ボラティリティ (%)",
        "chart_return":         "年率期待リターン (%)",
        "chart_weight_pct":     "投資比率 (%)",
        "chart_frontier_curve": "効率的フロンティア",
        "chart_cml":            "資本市場線",
        "chart_optimal":        "最適ポートフォリオ",
        "chart_short_term":     "短期銘柄",
        "chart_high_mdd":       "高MDD銘柄",
        "chart_asset":          "銘柄",
        "chart_series":         "系列",
        # ── Chart titles (for mpl) ─────────────────────────────────────────
        "cum_bar_title":  "累積リターン比較（ポートフォリオ vs ベンチマーク）",
        "cum_bar_ylabel": "累積リターン (%)",
        "ef_title":       "効率的フロンティア",
        "ef_xlabel":      "年率ボラティリティ (%)",
        "ef_ylabel":      "年率期待リターン (%)",
        "cum_line_title": "累積リターン推移",
        "roll_title":     "ローリング・シャープレシオ（{w}ヶ月窓）",
        "roll_ylabel":    "シャープレシオ",
        "dd_title":       "ドローダウン推移",
        "dd_ylabel":      "ドローダウン (%)",
        # ── Download buttons ──────────────────────────────────────────────
        "btn_download_png":   "📥 グラフをダウンロード (.png)",
        "btn_download_all":   "📦 全ファイルをダウンロード (.zip)",
        "download_xlsx":      "📊 Excelをダウンロード",
        "download_json":      "📄 JSONをダウンロード",
        "download_resolved":  "📋 銘柄解決ログ (.xlsx)",
        # ── Excel internals ────────────────────────────────────────────────
        "sheet_input":       "入力シート",
        "sheet_result":      "結果シート",
        "col_code":          "証券コード",
        "col_start":         "取得開始（yyyymmdd）",
        "col_end":           "取得終了（yyyymmdd）",
        "excel_title":       "--- ポートフォリオ分析結果 ---",
        "excel_calc_date":   "最終計算日時",
        "excel_opt_type":    "最適化タイプ",
        "excel_opt_tangent": "接点",
        "excel_exp_return":  "期待年率リターン",
        "excel_ann_risk":    "年率リスク (標準偏差)",
        "excel_sharpe":      "シャープレシオ",
        "excel_perf_title":  "--- パフォーマンス比較サマリー ---",
    },
    # ─────────────────────────────────────────────────────────────────────
    "EN": {
        "app_notice": (
            "This tool is designed for **Nikkei Stock League** portfolio analysis. "
            "It calculates optimal allocations based on historical data and is intended solely "
            "to **provide analysis and data** — it does not guarantee investment returns."
        ),
        "app_description": (
            "Enter your candidate stocks and this tool automatically calculates the allocation "
            "that **maximizes the Sharpe ratio** (return per unit of risk)."
        ),
        "label_portfolio_name": "Portfolio Name",
        "label_period":         "Analysis Period",
        "label_start_date":     "Start Date",
        "label_end_date":       "End Date",
        "section_period":      "📅 Analysis Period",
        "section_period_settings": "Analysis Period & Settings",
        "section_advanced":    "⚙️ Advanced Settings",
        "label_risk_free_rate": "Risk-Free Rate",
        "desc_risk_free_rate":  "Rate used for Sharpe ratio calculation (enter as %)",
        "desc_min_weight":      "Minimum allocation per asset (enter as %, 0 = no constraint)",
        "warn_min_weight":      "Setting min weight above 0% reduces the reliability of the Efficient Frontier",
        "label_user_country":   "Country",
        "desc_user_country":    "Used to prioritize stock search and select benchmark indices",
        "label_mdd_threshold":  "MDD Threshold",
        "desc_mdd_threshold":   "Assets exceeding this drawdown are highlighted red on the frontier (not excluded)",
        "label_min_months":     "Short-term Threshold (months)",
        "desc_min_months":      "Assets with fewer months of data are shown as dashed lines",
        "section_symbols":    "📋 Stock Symbols",
        "sym_table_hint":     "Enter ticker symbols (or a Japanese company name, e.g. トヨタ) and select from suggestions to confirm. You can paste multiple entries separated by commas or new lines.",
        "edinet_attribution": "Company-name search uses the EDINET Code List published by EDINET (Financial Services Agency of Japan), processed for this app. "
                              "Source: [EDINET (FSA)](https://disclosure2.edinet-fsa.go.jp/) / "
                              "[Public Data License v1.0](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0) / "
                              "Processed by: Ryoji Okoshi",
        "col_symbol":         "Symbol",
        "col_name":           "Name",
        "col_exchange":       "Exchange",
        "col_country":        "Country",
        "col_status":         "Status",
        "status_confirmed":   "✅ Confirmed",
        "status_not_found":   "⚠️ Not found",
        "btn_add_symbol":     "＋ Add Symbol",
        "btn_run":            "▶ Run Analysis",
        "placeholder_symbol": "e.g. AAPL",
        "suggestion_header":  "Suggestions (click to confirm)",
        "warn_has_unconfirmed":  "⚠️ Some symbols are not confirmed. Please confirm all symbols before running.",
        "warn_no_confirmed":     "⚠️ No symbols entered.",
        "warn_no_start_date":    "⚠️ Please select a start date.",
        "warn_date_order":       "⚠️ Start date must be before the end date.",
        "step_download":  "Downloading price data...",
        "step_shortterm": "Checking short-term assets...",
        "step_mdd":       "Computing max drawdown...",
        "step_optimize":  "Optimizing portfolio...",
        "step_risk":      "Computing risk metrics...",
        "step_bench":     "Comparing benchmarks...",
        "step_done":      "✅ Analysis complete",
        "analysis_error": "An error occurred during analysis",
        "section_weights":    "Optimal Portfolio Weights",
        "desc_weights": (
            "Weights optimized to maximize the Sharpe ratio. "
            "A higher weight means the asset delivered more return per unit of risk during this period."
        ),
        "section_performance": "Performance Summary",
        "desc_performance": (
            "Compares your portfolio against market benchmarks. "
            "Beta below 1 means lower market sensitivity. "
            "A higher Info Ratio means more consistent outperformance. "
            "* The Expected Return / Sharpe Ratio shown above are optimizer estimates (theoretical). "
            "Values in this table are realized figures computed from actual monthly returns."
        ),
        "section_comparison_funds": "Comparison Fund (Optional)",
        "comp_fund_hint": "Enter symbols for a comparison fund. It will be optimized with the same process as your main portfolio and shown as a single fund in all charts.",
        "comp_fund_name_label": "Comparison Fund Name",
        "comp_fund_name_placeholder": "e.g. Tech Fund",
        # ── Multi-fund UI ──────────────────────────────────────────────────
        "section_funds":          "📋 Fund Management",
        "fund_list_header":       "Funds",
        "fund_name_label":        "Fund Name",
        "fund_name_placeholder":  "e.g. Tech Fund",
        "fund_symbols_label":     "Holdings",
        "btn_add_fund":           "+ Add Fund",
        "btn_del_fund":           "Delete",
        "fund_default_name":      "Fund",
        "fund_confirmed_count":   "symbols confirmed",
        "fund_chart_style_label": "Chart Color",
        "fund_line_style_label":  "Line Style",
        "fund_tab_empty":         "Please add a fund.",
        "warn_no_funds":          "⚠️ No funds created.",
        "warn_fund_no_confirmed": "⚠️ Some funds have no confirmed symbols: {names}",
        "section_chart_colors": "Chart Style",
        "color_portfolio_label": "Portfolio",
        "color_bench_label": "Benchmark",
        "col_header_series": "Series",
        "col_header_color": "Color",
        "col_header_style": "Line Style",
        "style_solid": "Solid",
        "style_dashed": "Dashed",
        "style_dotted": "Dotted",
        "style_dashdot": "Dash-dot",
        "section_cum_bar":  "Cumulative Return Comparison",
        "desc_cum_bar":     "Total return over the full analysis period, shown as a bar chart.",
        "section_frontier": "Efficient Frontier",
        "desc_frontier": (
            "X-axis = risk (volatility), Y-axis = expected return. "
            "★ = optimal portfolio. Red dots = assets that experienced large drawdowns."
        ),
        "section_cum_line": "Cumulative Return Over Time",
        "desc_cum_line":    "Return evolution from 0% at start date.",
        "section_rolling":  "Rolling Sharpe Ratio (12-month window)",
        "desc_rolling": (
            "12-month rolling risk-adjusted returns. "
            "Values below 0 indicate a loss period."
        ),
        "section_drawdown": "Drawdown",
        "desc_drawdown":    "Percentage decline from the prior peak at each point in time. Deeper = larger loss.",
        "col_portfolio":   "Portfolio/Index",
        "col_sharpe":      "Sharpe Ratio",
        "col_ann_return":  "Annual Return",
        "col_ann_risk":    "Annual Risk",
        "col_cum_return":  "Cumulative Return",
        "col_beta":        "Beta",
        "col_var":         "VaR(95%)",
        "col_cvar":        "CVaR(95%)",
        "col_ir":          "Info Ratio",
        "col_ticker_name": "Symbol/Name",
        "col_weight":      "Weight (%)",
        "col_total":       "Total",
        "chart_date":           "Date",
        "chart_cum_ret":        "Cumulative Return (%)",
        "chart_sharpe":         "Sharpe Ratio",
        "chart_drawdown_pct":   "Drawdown (%)",
        "chart_risk":           "Annual Volatility (%)",
        "chart_return":         "Expected Annual Return (%)",
        "chart_weight_pct":     "Weight (%)",
        "chart_frontier_curve": "Efficient Frontier",
        "chart_cml":            "Capital Market Line",
        "chart_optimal":        "Optimal Portfolio",
        "chart_short_term":     "Short-term Asset",
        "chart_high_mdd":       "High Drawdown Asset",
        "chart_asset":          "Asset",
        "chart_series":         "Series",
        "cum_bar_title":  "Cumulative Return Comparison (Portfolio vs Benchmark)",
        "cum_bar_ylabel": "Cumulative Return (%)",
        "ef_title":       "Efficient Frontier",
        "ef_xlabel":      "Annual Volatility (%)",
        "ef_ylabel":      "Expected Annual Return (%)",
        "cum_line_title": "Cumulative Return Over Time",
        "roll_title":     "Rolling Sharpe Ratio ({w}-month window)",
        "roll_ylabel":    "Sharpe Ratio",
        "dd_title":       "Drawdown",
        "dd_ylabel":      "Drawdown (%)",
        "btn_download_png":   "📥 Download Chart (.png)",
        "btn_download_all":   "📦 Download All Files (.zip)",
        "download_xlsx":      "📊 Download Excel",
        "download_json":      "📄 Download JSON",
        "download_resolved":  "📋 Symbol Log (.xlsx)",
        "sheet_input":       "Input",
        "sheet_result":      "Results",
        "col_code":          "Ticker Code",
        "col_start":         "Start (yyyymmdd)",
        "col_end":           "End (yyyymmdd)",
        "excel_title":       "--- Portfolio Analysis Results ---",
        "excel_calc_date":   "Calculation Date",
        "excel_opt_type":    "Optimization Type",
        "excel_opt_tangent": "Tangent",
        "excel_exp_return":  "Expected Annual Return",
        "excel_ann_risk":    "Annual Risk (Std Dev)",
        "excel_sharpe":      "Sharpe Ratio",
        "excel_perf_title":  "--- Performance Comparison Summary ---",
    },
}


def get_text(key: str, lang: str = "JP") -> str:
    """Return translated string. Falls back to key name if not found."""
    return _L.get(lang, _L["JP"]).get(key, key)
