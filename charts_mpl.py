"""
charts_mpl.py — Matplotlib chart builders.
Each function returns PNG bytes (io.BytesIO content) for st.download_button.
Supports multiple funds via result.funds list.
"""

from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import japanize_matplotlib  # noqa: F401 — enables Japanese fonts

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier

from analysis import AnalysisResult

FIG_W, FIG_H  = 12, 6
DPI           = 120
GRID_ALPHA    = 0.35
BAR_ALPHA     = 0.85
_PF_COLOR     = "#2563EB"
_BENCH_COLOR  = "#9CA3AF"
_SHORT_COLOR  = "#F59E0B"
_MDD_COLOR    = "#EF4444"
_OPT_COLOR    = "#EAB308"
_OPT_EDGE     = "#A16207"   # darker edge of the optimal square
_FIXED_COLOR  = "#1F2937"   # charcoal — user-specified weights (◆, white edge)

# Per-benchmark defaults (cycling)
_BENCH_COLORS_M = ["#E67E22", "#16A085", "#8E44AD", "#E74C3C", "#2C3E50"]
_DEFAULT_BENCH_STYLES = ["dashed", "dotted", "dashdot", "solid", "dashed"]

# Per-fund defaults
_FUND_COLORS = ["#2563EB", "#E74C3C", "#16A085", "#8E44AD",
                "#F39C12", "#1ABC9C", "#E67E22", "#3498DB"]

STYLE_TO_LS = {
    "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.",
}

def _resolve_multi(n_funds: int, n_bench: int, custom: dict | None = None):
    """Return (fund_colors, fund_ls, bench_colors, bench_ls)."""
    c = custom or {}
    fc_list = c.get("fund_colors", _FUND_COLORS)
    fs_list = c.get("fund_styles", ["solid"] * n_funds)
    fund_colors = [fc_list[i % len(fc_list)] for i in range(n_funds)]
    fund_ls = [STYLE_TO_LS.get(fs_list[i % len(fs_list)], "-") for i in range(n_funds)]
    bl = c.get("benchmarks", _BENCH_COLORS_M)
    bs = c.get("bench_styles", _DEFAULT_BENCH_STYLES)
    bench_colors = [bl[i % len(bl)] for i in range(n_bench)]
    bench_ls = [STYLE_TO_LS.get(bs[i % len(bs)], "--") for i in range(n_bench)]
    return fund_colors, fund_ls, bench_colors, bench_ls

def _resolve(n_bench: int, custom: dict | None = None):
    """Legacy: Return (pf_color, bench_colors, pf_ls, bench_ls)."""
    c = custom or {}
    pf_c = c.get("portfolio", _PF_COLOR)
    bl   = c.get("benchmarks", _BENCH_COLORS_M)
    pf_s = STYLE_TO_LS.get(c.get("portfolio_style", "solid"), "-")
    bs   = c.get("bench_styles", _DEFAULT_BENCH_STYLES)
    return (
        pf_c,
        [bl[i % len(bl)] for i in range(n_bench)],
        pf_s,
        [STYLE_TO_LS.get(bs[i % len(bs)], "--") for i in range(n_bench)],
    )


def _to_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=DPI)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── 1. Cumulative return bar ──────────────────────────────────────────────────

def mpl_cum_bar(result: AnalysisResult, L: dict, custom: dict | None = None) -> bytes:
    df = result.comparison_df[[L["col_portfolio"], L["col_cum_return"]]].copy()
    df[L["col_cum_return"]] = (
        df[L["col_cum_return"]].astype(str)
        .str.replace("%", "", regex=False).astype(float)
        * 100   # stored as a fraction (1.12 = 112%)
    )
    df = df.sort_values(L["col_cum_return"], ascending=False)

    labels_list = df[L["col_portfolio"]].tolist()
    values = df[L["col_cum_return"]].tolist()

    n_funds = len(result.funds)
    n_bench = len(result.bench_tickers)
    fc, fls, bc, bls = _resolve_multi(n_funds, n_bench, custom)

    fund_names = [fr.fund_name for fr in result.funds]
    bench_names = [result.benchmark_labels[s] for s in result.bench_tickers]
    _cmap = {}
    for i, fn in enumerate(fund_names):
        _cmap[fn] = fc[i]
    for i, bn in enumerate(bench_names):
        _cmap[bn] = bc[i]
    colors = [_cmap.get(lb, _BENCH_COLOR) for lb in labels_list]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    bars = ax.bar(range(len(labels_list)), values, color=colors, alpha=BAR_ALPHA)
    ax.set_title(L["cum_bar_title"], fontsize=14)
    ax.set_ylabel(L["cum_bar_ylabel"], fontsize=11)
    ax.set_xticks(range(len(labels_list)))
    ax.set_xticklabels(labels_list, rotation=30, ha="right", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=GRID_ALPHA)
    for rect, val in zip(bars, values):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(),
                f"{val:.2f}%", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    return _to_bytes(fig)


# ── 2. Efficient frontier ─────────────────────────────────────────────────────

_MARKER_S = 36   # one marker size for every point and legend symbol (matplotlib's default dot size)


def mpl_efficient_frontier(result: AnalysisResult, L: dict, fund_idx: int = 0) -> bytes:
    fr = result.funds[fund_idx] if fund_idx < len(result.funds) else None
    if fr is None:
        fig, ax = plt.subplots(figsize=(10, 6))
        plt.tight_layout()
        return _to_bytes(fig)

    mu  = fr.mu
    S   = fr.S
    rfr = result.risk_free_rate

    fig, ax = plt.subplots(figsize=(10, 6))   # 縦横比 3:5

    # Frontier curve
    target_returns = np.linspace(float(mu.min()), float(mu.max()), 50)
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
    if vols:
        ax.plot(vols, rets, linestyle="--", color="gray", label=L["chart_frontier_curve"])

    # Optimum: for a fund with user-specified weights, that of the same assets
    fixed = getattr(fr, "fixed_weights", False)
    o_vol, o_ret, o_sh = ((fr.opt_volatility, fr.opt_return, fr.opt_sharpe) if fixed
                          else (fr.volatility, fr.expected_return, fr.sharpe))

    # CML
    if vols:
        cml_x = np.linspace(0, max(vols) * 1.1, 50)
        cml_y = rfr * 100 + o_sh * cml_x
        ax.plot(cml_x, cml_y, label=L["chart_cml"], color=_PF_COLOR)

    # Long-term assets
    long_tickers = [t for t in fr.fund_tickers if t not in fr.short_term_tickers]
    if long_tickers:
        vv = [float(np.sqrt(S.loc[t, t])) * 100 for t in long_tickers]
        rr = [float(mu[t]) * 100 for t in long_tickers]
        # no per-asset name labels: with many assets they clutter the PNG
        ax.scatter(vv, rr, s=_MARKER_S, label=L["chart_asset"], zorder=5)

    # Shape = short-term (triangle) or not (circle); color = high MDD (red) or not.
    # A short-term asset that is also high-MDD is a red triangle, so neither hides the other.
    def _pts(tickers):
        tickers = [t for t in tickers if t in S.index and t in mu.index]
        return ([float(np.sqrt(S.loc[t, t])) * 100 for t in tickers],
                [float(mu[t]) * 100 for t in tickers])

    short_set = set(fr.short_term_tickers or [])
    mdd_set   = set(fr.knockout_tickers or [])
    for tickers, kw, label, z in (
        ([t for t in fr.short_term_tickers if t not in mdd_set],
         dict(color=_SHORT_COLOR, marker="^"), L["chart_short_term"], 6),
        ([t for t in fr.knockout_tickers if t not in short_set],
         dict(color=_MDD_COLOR), L["chart_high_mdd"], 7),
        ([t for t in fr.short_term_tickers if t in mdd_set],
         dict(color=_MDD_COLOR, marker="^"), L["chart_short_high_mdd"], 7),
    ):
        vv, rr = _pts(tickers)
        if vv:
            ax.scatter(vv, rr, s=_MARKER_S, label=label, zorder=z, **kw)

    # Optimal point: yellow square (all markers share _MARKER_S, in the legend too)
    ax.scatter(o_vol * 100, o_ret * 100,
               marker="s", s=_MARKER_S, color=_OPT_COLOR, edgecolors=_OPT_EDGE, linewidths=1.0,
               zorder=8, label=L["chart_optimal"])
    if fixed:
        ax.scatter(fr.volatility * 100, fr.expected_return * 100,
                   marker="D", s=_MARKER_S, color=_FIXED_COLOR, edgecolors="white", linewidths=1.0,
                   zorder=9, label=L["chart_fixed_pf"])

    _title = L["ef_title"]
    if len(result.funds) > 1:
        _title += f" — {fr.fund_name}"
    ax.set_title(_title, fontsize=14)
    ax.set_xlabel(L["ef_xlabel"], fontsize=11)
    ax.set_ylabel(L["ef_ylabel"], fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=GRID_ALPHA)
    plt.tight_layout()
    return _to_bytes(fig)


# ── 3. Cumulative return line ─────────────────────────────────────────────────

def mpl_cum_line(result: AnalysisResult, L: dict, custom: dict | None = None) -> bytes:
    n_funds = len(result.funds)
    n_bench = len(result.bench_tickers)
    fc, fls, bc, bls = _resolve_multi(n_funds, n_bench, custom)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    # All funds
    for fi, fr in enumerate(result.funds):
        pf_cum = (1 + fr.portfolio_returns).cumprod() - 1
        zero   = pd.Series([0.0], index=[pf_cum.index[0] - pd.DateOffset(months=1)])
        pf_cum = pd.concat([zero, pf_cum])
        ax.plot(pf_cum.index, pf_cum * 100,
                label=fr.fund_name, color=fc[fi], linewidth=2.5, linestyle=fls[fi])

    # Benchmarks
    _ref_idx = result.funds[0].portfolio_returns.index if result.funds else pd.Index([])
    for i, sym in enumerate(result.bench_tickers):
        label   = result.benchmark_labels[sym]
        bseries = result.bench_returns[sym].dropna()
        if not _ref_idx.empty:
            bseries = bseries.loc[_ref_idx[0]:]
        cum     = (1 + bseries).cumprod() - 1
        zero    = pd.Series([0.0], index=[cum.index[0] - pd.DateOffset(months=1)])
        cum     = pd.concat([zero, cum])
        ax.plot(cum.index, cum * 100,
                label=label, color=bc[i], linewidth=1.5, linestyle=bls[i])

    ax.set_title(L["cum_line_title"], fontsize=14)
    ax.set_xlabel(L["chart_date"], fontsize=11)
    ax.set_ylabel(L["chart_cum_ret"], fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=GRID_ALPHA)
    plt.tight_layout()
    return _to_bytes(fig)
