"""
charts_altair.py — Altair interactive chart builders.
Each function takes an AnalysisResult + lang dict and returns an alt.Chart.
Supports multiple funds via result.funds list.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import altair as alt

from analysis import AnalysisResult
from pypfopt import EfficientFrontier


# ── Palette ────────────────────────────────────────────────────────────────────
_PORTFOLIO_COLOR = "#2563EB"   # blue
_BENCH_COLOR     = "#9CA3AF"   # gray
_SHORT_COLOR     = "#F59E0B"   # amber
_MDD_COLOR       = "#EF4444"   # red
_OPTIMAL_COLOR   = "#EAB308"   # yellow

# Per-benchmark defaults (cycling)
_BENCH_COLORS = ["#E67E22", "#16A085", "#8E44AD", "#E74C3C", "#2C3E50"]
_DEFAULT_BENCH_STYLES = ["dashed", "dotted", "dashdot", "solid", "dashed"]

# Per-fund defaults
_FUND_COLORS = ["#2563EB", "#E74C3C", "#16A085", "#8E44AD",
                "#F39C12", "#1ABC9C", "#E67E22", "#3498DB"]

STYLE_TO_DASH = {
    "solid": [], "dashed": [6, 4], "dotted": [2, 2], "dashdot": [8, 4, 2, 4],
}
DEFAULT_COLORS = {"portfolio": _PORTFOLIO_COLOR, "benchmarks": list(_BENCH_COLORS)}
DEFAULT_STYLES = {"portfolio": "solid", "benchmarks": list(_DEFAULT_BENCH_STYLES)}

def _resolve_multi(n_funds: int, n_bench: int, custom: dict | None = None):
    """Return (fund_colors, fund_dashes, bench_colors, bench_dashes, fund_widths, bench_widths)."""
    c = custom or {}
    # Fund colors/styles
    fc_list = c.get("fund_colors", _FUND_COLORS)
    fs_list = c.get("fund_styles", ["solid"] * n_funds)
    fund_colors = [fc_list[i % len(fc_list)] for i in range(n_funds)]
    fund_dashes = [STYLE_TO_DASH.get(fs_list[i % len(fs_list)], []) for i in range(n_funds)]
    fund_widths = [2.5] * n_funds
    # Bench colors/styles
    bl = c.get("benchmarks", _BENCH_COLORS)
    bs = c.get("bench_styles", _DEFAULT_BENCH_STYLES)
    bench_colors = [bl[i % len(bl)] for i in range(n_bench)]
    bench_dashes = [STYLE_TO_DASH.get(bs[i % len(bs)], [6, 4]) for i in range(n_bench)]
    bench_widths = [1.5] * n_bench
    return fund_colors, fund_dashes, bench_colors, bench_dashes, fund_widths, bench_widths

def _resolve(n_bench: int, custom: dict | None = None):
    """Legacy: Return (pf_color, bench_colors, pf_dash, bench_dashes)."""
    c = custom or {}
    pf_c = c.get("portfolio", _PORTFOLIO_COLOR)
    bl   = c.get("benchmarks", _BENCH_COLORS)
    pf_s = STYLE_TO_DASH.get(c.get("portfolio_style", "solid"), [])
    bs   = c.get("bench_styles", _DEFAULT_BENCH_STYLES)
    return (
        pf_c,
        [bl[i % len(bl)] for i in range(n_bench)],
        pf_s,
        [STYLE_TO_DASH.get(bs[i % len(bs)], [6, 4]) for i in range(n_bench)],
    )

# ── Time axis helper ───────────────────────────────────────────────────────────
# 1月のみ "YYYY.1"、それ以外は月番号のみ "2", "3", ... と表示し、毎月縦グリッドを描画
_MONTH_LABEL_EXPR = (
    "month(datum.value) === 0 "
    "? (year(datum.value) + '.' + (month(datum.value) + 1)) "
    ": '' + (month(datum.value) + 1)"
)


def _time_x(title: str) -> alt.X:
    """月次グリッド線付き・1月に西暦表示の時系列 X 軸を返す。"""
    return alt.X(
        "date:T",
        title=title,
        axis=alt.Axis(
            tickCount="month",
            grid=True,
            gridColor="lightgray",
            gridOpacity=0.4,
            labelExpr=_MONTH_LABEL_EXPR,
        ),
    )


# ── 1. Weights bar chart ──────────────────────────────────────────────────────

def chart_weights(result: AnalysisResult, L: dict, fund_idx: int = 0) -> alt.Chart:
    fr = result.funds[fund_idx]
    df = fr.weights_df.copy()
    # Drop the "Total" row for the chart
    total_label = L["col_total"]
    df = df[df[L["col_ticker_name"]] != total_label].copy()
    df = df.sort_values(L["col_weight"], ascending=False)

    chart = (
        alt.Chart(df)
        .mark_bar(color=_PORTFOLIO_COLOR)
        .encode(
            x=alt.X(f'{L["col_weight"]}:Q',
                    title=L["chart_weight_pct"],
                    axis=alt.Axis(format=".1f")),
            y=alt.Y(f'{L["col_ticker_name"]}:N',
                    title=None,
                    sort="-x"),
            tooltip=[
                alt.Tooltip(f'{L["col_ticker_name"]}:N'),
                alt.Tooltip(f'{L["col_weight"]}:Q', format=".2f",
                            title=L["chart_weight_pct"]),
            ],
        )
        .properties(height=max(200, len(df) * 32))
    )
    return chart


# ── 2. Cumulative return bar chart ────────────────────────────────────────────

def chart_cum_bar(result: AnalysisResult, L: dict, custom_colors: dict | None = None) -> alt.Chart:
    df = result.comparison_df[[L["col_portfolio"], L["col_cum_return"]]].copy()
    df[L["col_cum_return"]] = (
        df[L["col_cum_return"]]
        .astype(str).str.replace("%", "", regex=False)
        .astype(float)
    )
    df = df.sort_values(L["col_cum_return"], ascending=False).reset_index(drop=True)

    n_funds = len(result.funds)
    n_bench = len(result.bench_tickers)
    fc, fd, bc, bd, fw, bw = _resolve_multi(n_funds, n_bench, custom_colors)

    fund_names  = [fr.fund_name for fr in result.funds]
    bench_names = [result.benchmark_labels[s] for s in result.bench_tickers]

    _color_map = {}
    for i, fn in enumerate(fund_names):
        _color_map[fn] = fc[i]
    for i, bn in enumerate(bench_names):
        _color_map[bn] = bc[i]

    df["_color"] = df[L["col_portfolio"]].map(
        lambda n: _color_map.get(n, _BENCH_COLOR)
    )
    df["_label"] = df[L["col_cum_return"]].map(lambda v: f"{v:.2f}%")

    _x = alt.X(f'{L["col_portfolio"]}:N',
                title=None,
                sort=alt.EncodingSortField(field=L["col_cum_return"], order="descending"),
                axis=alt.Axis(labelAngle=-30))
    _y = alt.Y(f'{L["col_cum_return"]}:Q', title=L["cum_bar_ylabel"])
    _color = alt.Color("_color:N", scale=None, legend=None)
    _tooltip = [
        alt.Tooltip(f'{L["col_portfolio"]}:N'),
        alt.Tooltip(f'{L["col_cum_return"]}:Q', format=".2f", title=L["chart_cum_ret"]),
    ]

    bars = (
        alt.Chart(df)
        .mark_bar()
        .encode(x=_x, y=_y, color=_color, tooltip=_tooltip)
    )

    labels = (
        alt.Chart(df)
        .mark_text(baseline="bottom", dy=-4, fontSize=11)
        .encode(
            x=_x,
            y=_y,
            text=alt.Text("_label:N"),
            color=_color,
        )
    )

    return (bars + labels).properties(height=350)


# ── 3. Efficient Frontier ─────────────────────────────────────────────────────

def chart_efficient_frontier(result: AnalysisResult, L: dict, fund_idx: int = 0) -> alt.LayerChart:
    fr  = result.funds[fund_idx]
    mu  = fr.mu
    S   = fr.S
    rfr = result.risk_free_rate

    # Build frontier curve
    target_returns = np.linspace(float(mu.min()), float(mu.max()), 60)
    vols, rets = [], []
    for r in target_returns:
        try:
            ef_tmp = EfficientFrontier(mu, S)
            ef_tmp.efficient_return(r)
            rp, vp, _ = ef_tmp.portfolio_performance()
            vols.append(float(vp) * 100)
            rets.append(float(rp) * 100)
        except Exception:
            pass

    frontier_df = pd.DataFrame({"vol": vols, "ret": rets})

    # Build asset scatter data
    asset_rows = []
    sym_to_name = dict(zip(fr.confirmed_df["symbol"],
                           fr.confirmed_df.get("name", fr.confirmed_df["symbol"])))
    for t in fr.fund_tickers:
        try:
            v = float(np.sqrt(S.loc[t, t])) * 100
            r = float(mu[t]) * 100
        except Exception:
            continue
        if t in fr.knockout_tickers:
            atype = L["chart_high_mdd"]
        elif t in fr.short_term_tickers:
            atype = L["chart_short_term"]
        else:
            atype = L["chart_asset"]
        asset_rows.append({
            "vol": v, "ret": r,
            "name": f"{t} / {sym_to_name.get(t, t)}",
            "type": atype,
        })
    asset_df = pd.DataFrame(asset_rows)

    # Optimal point
    opt_df = pd.DataFrame([{
        "vol": fr.volatility * 100,
        "ret": fr.expected_return * 100,
        "name": f"★ {fr.fund_name}",
    }])

    # CML
    if vols:
        cml_x = np.linspace(0, max(vols) * 1.1, 40)
        cml_y = rfr * 100 + fr.sharpe * cml_x
        cml_df = pd.DataFrame({"vol": cml_x, "ret": cml_y})
    else:
        cml_df = pd.DataFrame({"vol": [], "ret": []})

    # Color + shape scales
    color_domain = [L["chart_asset"], L["chart_short_term"], L["chart_high_mdd"]]
    color_range  = [_PORTFOLIO_COLOR, _SHORT_COLOR, _MDD_COLOR]
    shape_domain = [L["chart_asset"], L["chart_short_term"], L["chart_high_mdd"]]
    shape_range  = ["circle", "triangle-up", "circle"]

    # Layers
    frontier_line = (
        alt.Chart(frontier_df)
        .mark_line(strokeDash=[6, 3], color="gray", strokeWidth=1.5)
        .encode(x="vol:Q", y="ret:Q")
    )

    cml_line = (
        alt.Chart(cml_df)
        .mark_line(color=_PORTFOLIO_COLOR, strokeWidth=1.5)
        .encode(x="vol:Q", y="ret:Q")
    )

    if not asset_df.empty:
        asset_scatter = (
            alt.Chart(asset_df)
            .mark_point(size=80, filled=True, opacity=0.85)
            .encode(
                x=alt.X("vol:Q", title=L["chart_risk"]),
                y=alt.Y("ret:Q", title=L["chart_return"]),
                color=alt.Color("type:N",
                                scale=alt.Scale(domain=color_domain, range=color_range),
                                legend=alt.Legend(title=None)),
                shape=alt.Shape("type:N",
                                scale=alt.Scale(domain=shape_domain, range=shape_range),
                                legend=None),
                tooltip=[
                    alt.Tooltip("name:N", title=L["chart_asset"]),
                    alt.Tooltip("vol:Q", format=".2f", title=L["chart_risk"]),
                    alt.Tooltip("ret:Q", format=".2f", title=L["chart_return"]),
                    alt.Tooltip("type:N"),
                ],
            )
        )
    else:
        asset_scatter = alt.Chart(pd.DataFrame()).mark_point()

    optimal_point = (
        alt.Chart(opt_df)
        .mark_text(fontSize=26, color=_OPTIMAL_COLOR, fontWeight="bold", dy=-2)
        .encode(
            x="vol:Q", y="ret:Q",
            text=alt.value("★"),
            tooltip=[alt.Tooltip("name:N"), alt.Tooltip("vol:Q", format=".2f"),
                     alt.Tooltip("ret:Q", format=".2f")],
        )
    )

    return (
        alt.layer(frontier_line, cml_line, asset_scatter, optimal_point)
        .properties(height=504)   # 縦横比 3:5（基準幅 840px）
        .configure_legend(orient="bottom", columns=3)
    )


# ── 4. Cumulative return line chart ───────────────────────────────────────────

def chart_cum_line(result: AnalysisResult, L: dict, custom_colors: dict | None = None) -> alt.Chart:
    rows: list[dict] = []

    # All funds
    for fr in result.funds:
        pf = fr.portfolio_returns
        pf_cum = (1 + pf).cumprod() - 1
        zero_date = pf_cum.index[0] - pd.DateOffset(months=1)
        pf_cum = pd.concat([pd.Series([0.0], index=[zero_date]), pf_cum])
        for date, val in pf_cum.items():
            rows.append({
                "date": pd.Timestamp(date),
                "value": float(val) * 100,
                "series": fr.fund_name,
            })

    # Benchmarks
    _ref_idx = result.funds[0].portfolio_returns.index if result.funds else pd.Index([])
    for sym in result.bench_tickers:
        label = result.benchmark_labels[sym]
        bseries = result.bench_returns[sym].dropna()
        if bseries.empty or _ref_idx.empty:
            continue
        bseries = bseries.loc[_ref_idx[0]:]
        cum = (1 + bseries).cumprod() - 1
        zero_date = cum.index[0] - pd.DateOffset(months=1)
        cum = pd.concat([pd.Series([0.0], index=[zero_date]), cum])
        for date, val in cum.items():
            rows.append({
                "date": pd.Timestamp(date),
                "value": float(val) * 100,
                "series": label,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return alt.Chart(pd.DataFrame()).mark_line()

    # Assign per-series styles
    n_funds = len(result.funds)
    n_bench = len(result.bench_tickers)
    fc, fd, bc, bd, fw, bw = _resolve_multi(n_funds, n_bench, custom_colors)

    fund_names  = [fr.fund_name for fr in result.funds]
    bench_names = [result.benchmark_labels[s] for s in result.bench_tickers]
    all_series  = fund_names + bench_names
    colors      = fc + bc
    widths      = fw + bw
    dashes      = fd + bd

    chart = (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=_time_x(L["chart_date"]),
            y=alt.Y("value:Q", title=L["chart_cum_ret"]),
            color=alt.Color("series:N",
                            scale=alt.Scale(domain=all_series, range=colors),
                            legend=alt.Legend(title=None)),
            strokeWidth=alt.StrokeWidth(
                "series:N",
                scale=alt.Scale(domain=all_series, range=widths),
                legend=None,
            ),
            strokeDash=alt.StrokeDash(
                "series:N",
                scale=alt.Scale(domain=all_series, range=dashes),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("date:T", title=L["chart_date"], format="%Y-%m"),
                alt.Tooltip("series:N", title=L["chart_series"]),
                alt.Tooltip("value:Q", format=".2f", title=L["chart_cum_ret"]),
            ],
        )
        .properties(height=420)
        .configure_legend(orient="bottom", columns=3)
    )
    return chart
