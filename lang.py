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
            "配分比率を自動計算します。投資比率を指定して分析することもできます。"
        ),
        # ── Basic settings ─────────────────────────────────────────────────
        "label_portfolio_name": "ポートフォリオ名",
        "label_period":         "分析期間",
        "label_start_date":     "分析開始日",
        "label_end_date":       "分析終了日",
        # ── Advanced settings ──────────────────────────────────────────────
        "section_period":      "📅 期間設定",
        "section_period_settings": "📅 分析期間・設定",
        "section_advanced":    "⚙️ 詳細設定",
        "label_risk_free_rate": "無リスク金利",
        "desc_risk_free_rate":  "シャープレシオ計算に使う金利（% で入力）",
        "label_min_weight":     "最小投資比率",
        "desc_min_weight":      "各銘柄への最小割り当て比率（% で入力、0 = 制約なし）。比率を指定したファンドには適用されません",
        "warn_min_weight":      "最小投資比率を 0% 以外に設定すると、効率的フロンティアの図は表示されません",
        "label_user_country":   "対象国",
        "desc_user_country":    "銘柄検索の優先国とベンチマーク指数の選択に使用",
        "label_mdd_threshold":  "最大ドローダウン閾値",
        "desc_mdd_threshold":   "これを超える下落率の銘柄を効率的フロンティア上で赤くハイライト（除外はしない）",
        "label_min_months":     "短期銘柄判定（月数）",
        "desc_min_months":      "この月数未満の銘柄を、効率的フロンティアで▲（短期銘柄）表示",
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
        "col_weight_short":   "比率(%)",
        "btn_equalize":       "均等に配分",
        "weight_total":       "合計 {sum}%",
        "weight_mode_fixed":  "比率を指定",
        "help_weight_fixed":  "通常はチェック不要です（シャープレシオが最大になる投資比率を自動で計算します）。銘柄ごとの投資比率を自分で決めたいときだけ、チェックを入れて入力してください。",
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
        "warn_weight_blank":     "⚠️ {name}：比率が未入力の銘柄があります。",
        "warn_weight_invalid":   "⚠️ {name}：比率に数値でない値があります。",
        "warn_weight_sum":       "⚠️ {name}：投資比率の合計が {sum}% です。100% にしてください。",
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
        "section_weights_mixed": "投資比率",
        "desc_weights_mixed": (
            "「最適化」のファンドはシャープレシオが最大になるよう配分した比率、"
            "「比率を指定」のファンドは入力した比率です。"
        ),
        "tag_optimize":       "（最適化）",
        "tag_fixed":          "（指定）",
        "desc_frontier_fixed": "◆が指定した比率のポートフォリオ、黄色の■が同じ銘柄で最適化した場合のポートフォリオです。",
        "chart_fixed_pf":     "指定比率のポートフォリオ",
        "section_performance": "パフォーマンス比較",
        "desc_performance": (
            "ポートフォリオと市場指数の成績を比較します。"
            "ベータが1未満なら市場全体より値動きが小さく、"
            "情報比率が高いほどベンチマーク超過リターンの安定性が高いことを示します。"
        ),
        "note_performance": (
            "※この表は、分析期間中にこの投資比率で実際に保有していた場合の成績（実績値）です。"
            "レポートなどで成績を示すときは、この表の値を使ってください。"
            "効率的フロンティアの図の位置やExcelの「期待年率リターン」などは、投資比率を決めるための計算用の値です。"
            "安定した計算と正しい形の図にするため、リスクには値動きのぶれを抑える補正をかけており、"
            "この表の値とは少し異なりますが、問題はありません。"
        ),
        "data_note_title":   "データ期間についての注意（{funds}）",
        "data_note_sep":     "・",
        "data_note_ticker":  "「{sym} {name}」は{n}か月分",
        "data_note_short": (
            "**{fund}：分析期間の一部しか使えていません**\n\n"
            "{tickers}しかデータがありません（分析期間は{period}か月）。\n\n"
            "そのため、このファンドの投資比率を決める計算（効率的フロンティアの図を含む）では、"
            "**リターンとリスクを全銘柄とも、データがそろう{risk}か月（{start}〜）だけで計算**しています。"
            "パフォーマンス比較の表は分析期間全体（{period}か月）の実績なので、図と表の値は一致しません。\n\n"
            "このままの結果を使っても構いませんが、期間をそろえたい場合は、"
            "分析開始日を {start} にするか、この銘柄を外して比べることをおすすめします。"
        ),
        "data_note_zero": (
            "**{fund}：データの短い銘柄があります**\n\n"
            "{tickers}しかデータがありません（分析期間は{period}か月）。\n\n"
            "全銘柄がそろう月が少ないため、データのない期間（上場前など）を「リターン0%」とみなして計算しました。"
            "この銘柄はリスクやリターンが実際とずれて見えます。\n\n"
            "このままの結果を使っても構いませんが、より正確に比べたい場合は、"
            "分析期間を短くするか、この銘柄を外して比べることをおすすめします。"
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
        "btn_cancel":             "キャンセル",
        "hint_close_fund":        "このファンドを削除",
        "dlg_del_fund_title":     "ファンドの削除",
        "msg_del_fund_confirm":   "「{name}」（確定済み {n} 銘柄）を削除しますか？この操作は元に戻せません。",
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
            "黄色の■が今回の最適ポートフォリオ、赤い点は大きな下落を経験した銘柄です。"
        ),
        "msg_frontier_hidden": (
            "最小投資比率（{pct}%）を設定しているため、効率的フロンティアの図は表示していません。"
            "最小投資比率の制約があると、最適ポートフォリオ（黄色の■）が効率的フロンティアの曲線上に乗らず、"
            "図が正しい形になりません。図が必要な場合は、最小投資比率を 0% にして分析してください。"
        ),
        "section_cum_line": "累積リターン推移",
        "desc_cum_line":    "投資開始時を0%として時系列のリターン推移を表します。",
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
        "chart_risk":           "年率ボラティリティ (%)",
        "chart_return":         "年率期待リターン (%)",
        "chart_weight_pct":     "投資比率 (%)",
        "chart_frontier_curve": "効率的フロンティア",
        "chart_cml":            "資本市場線",
        "chart_optimal":        "最適ポートフォリオ",
        "chart_short_term":     "短期銘柄",
        "chart_high_mdd":       "高MDD銘柄",
        "chart_short_high_mdd": "短期・高MDD銘柄",
        "chart_asset":          "銘柄",
        "chart_series":         "系列",
        # ── Chart titles (for mpl) ─────────────────────────────────────────
        "cum_bar_title":  "累積リターン比較（ポートフォリオ vs ベンチマーク）",
        "cum_bar_ylabel": "累積リターン (%)",
        "ef_title":       "効率的フロンティア",
        "ef_xlabel":      "年率ボラティリティ (%)",
        "ef_ylabel":      "年率期待リターン (%)",
        "cum_line_title": "累積リターン推移",
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
        "excel_opt_fixed":   "比率指定（最適化なし）",
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
            "that **maximizes the Sharpe ratio** (return per unit of risk). "
            "You can also analyze with weights you specify."
        ),
        "label_portfolio_name": "Portfolio Name",
        "label_period":         "Analysis Period",
        "label_start_date":     "Start Date",
        "label_end_date":       "End Date",
        "section_period":      "📅 Analysis Period",
        "section_period_settings": "📅 Analysis Period & Settings",
        "section_advanced":    "⚙️ Advanced Settings",
        "label_risk_free_rate": "Risk-Free Rate",
        "desc_risk_free_rate":  "Rate used for Sharpe ratio calculation (enter as %)",
        "label_min_weight":     "Minimum Weight",
        "desc_min_weight":      "Minimum allocation per asset (enter as %, 0 = no constraint). Not applied to funds with specified weights",
        "warn_min_weight":      "With a min weight above 0%, the Efficient Frontier chart is not shown",
        "label_user_country":   "Country",
        "desc_user_country":    "Used to prioritize stock search and select benchmark indices",
        "label_mdd_threshold":  "MDD Threshold",
        "desc_mdd_threshold":   "Assets exceeding this drawdown are highlighted red on the frontier (not excluded)",
        "label_min_months":     "Short-term Threshold (months)",
        "desc_min_months":      "Assets with fewer months are marked ▲ (Short-term Asset) on the efficient frontier",
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
        "col_weight_short":   "Weight(%)",
        "btn_equalize":       "Split equally",
        "weight_total":       "Total {sum}%",
        "weight_mode_fixed":  "Specify weights",
        "help_weight_fixed":  "Usually leave this unchecked (the weights that maximize the Sharpe ratio are calculated automatically). Check it only when you want to enter each asset's weight yourself.",
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
        "warn_weight_blank":     "⚠️ {name}: some weights are not entered.",
        "warn_weight_invalid":   "⚠️ {name}: some weights are not numbers.",
        "warn_weight_sum":       "⚠️ {name}: weights add up to {sum}%. Make them 100%.",
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
        "section_weights_mixed": "Portfolio Weights",
        "desc_weights_mixed": (
            "Optimized funds use the weights that maximize the Sharpe ratio; "
            "funds with specified weights use the weights you entered."
        ),
        "tag_optimize":       " (optimized)",
        "tag_fixed":          " (specified)",
        "desc_frontier_fixed": "◆ = your specified weights; yellow ■ = the optimal portfolio of the same assets.",
        "chart_fixed_pf":     "Specified Weights",
        "section_performance": "Performance Summary",
        "desc_performance": (
            "Compares your portfolio against market benchmarks. "
            "Beta below 1 means lower market sensitivity. "
            "A higher Info Ratio means more consistent outperformance."
        ),
        "note_performance": (
            "* This table shows how the portfolio actually performed over the analysis period with these weights. "
            "Use these values when reporting performance. "
            "The positions on the efficient frontier chart and the Excel \"Expected Annual Return\" etc. are "
            "values calculated to decide the weights. To keep the calculation stable and the chart correctly shaped, "
            "the risk is adjusted to dampen noise in price movements, so it differs slightly from this table — "
            "this is expected."
        ),
        "data_note_title":   "Note on data length ({funds})",
        "data_note_sep":     ", ",
        "data_note_ticker":  "\"{sym} {name}\" has {n} months",
        "data_note_short": (
            "**{fund}: only part of the analysis period is used**\n\n"
            "{tickers} of data (analysis period: {period} months).\n\n"
            "When computing this fund's weights (including the efficient frontier chart), "
            "**returns and risk for every asset are estimated only from the {risk} months in which "
            "all assets have data (from {start})**. The performance table covers the whole period "
            "({period} months), so the chart and the table will not match.\n\n"
            "You can use the result as it is, but to align the periods we recommend setting the "
            "start date to {start} or comparing without this asset."
        ),
        "data_note_zero": (
            "**{fund}: some assets have short data**\n\n"
            "{tickers} of data (analysis period: {period} months).\n\n"
            "Few months have data for all assets, so months without data (e.g. before listing) "
            "were treated as 0% returns, so the risk and return of such assets are distorted.\n\n"
            "You can use the result as it is, but for a more accurate comparison we recommend "
            "shortening the analysis period or comparing without these assets."
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
        "btn_cancel":             "Cancel",
        "hint_close_fund":        "Delete this fund",
        "dlg_del_fund_title":     "Delete fund",
        "msg_del_fund_confirm":   "Delete \"{name}\" ({n} confirmed symbols)? This cannot be undone.",
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
            "Yellow ■ = optimal portfolio. Red dots = assets that experienced large drawdowns."
        ),
        "msg_frontier_hidden": (
            "The Efficient Frontier chart is not shown because a minimum weight ({pct}%) is set. "
            "With that constraint the optimal portfolio (yellow ■) does not lie on the frontier curve, "
            "so the chart would be misleading. Set the minimum weight to 0% to see it."
        ),
        "section_cum_line": "Cumulative Return Over Time",
        "desc_cum_line":    "Return evolution from 0% at start date.",
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
        "chart_risk":           "Annual Volatility (%)",
        "chart_return":         "Expected Annual Return (%)",
        "chart_weight_pct":     "Weight (%)",
        "chart_frontier_curve": "Efficient Frontier",
        "chart_cml":            "Capital Market Line",
        "chart_optimal":        "Optimal Portfolio",
        "chart_short_term":     "Short-term Asset",
        "chart_high_mdd":       "High Drawdown Asset",
        "chart_short_high_mdd": "Short-term & High Drawdown Asset",
        "chart_asset":          "Asset",
        "chart_series":         "Series",
        "cum_bar_title":  "Cumulative Return Comparison (Portfolio vs Benchmark)",
        "cum_bar_ylabel": "Cumulative Return (%)",
        "ef_title":       "Efficient Frontier",
        "ef_xlabel":      "Annual Volatility (%)",
        "ef_ylabel":      "Expected Annual Return (%)",
        "cum_line_title": "Cumulative Return Over Time",
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
        "excel_opt_fixed":   "Specified weights (no optimization)",
        "excel_exp_return":  "Expected Annual Return",
        "excel_ann_risk":    "Annual Risk (Std Dev)",
        "excel_sharpe":      "Sharpe Ratio",
        "excel_perf_title":  "--- Performance Comparison Summary ---",
    },
}


def get_text(key: str, lang: str = "JP") -> str:
    """Return translated string. Falls back to key name if not found."""
    return _L.get(lang, _L["JP"]).get(key, key)
