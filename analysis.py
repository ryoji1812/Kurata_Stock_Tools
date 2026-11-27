"""
analysis.py — Core portfolio analysis pipeline.
Ported from ex13.ipynb cells 19–25.

run_analysis() is the single entry point.
Returns an AnalysisResult dataclass with everything needed for charts/downloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import json5
import numpy as np
import pandas as pd
import yfinance as yf
from pypfopt import EfficientFrontier, expected_returns, risk_models
from symbol_resolver import _yahoo_jp_fetch_monthly, _infer_country_from_symbol


# ── Result containers ─────────────────────────────────────────────────────────

@dataclass
class FundResult:
    """Per-fund optimization result."""
    fund_name:          str
    confirmed_df:       pd.DataFrame          # symbol / name / exchange / country
    fund_tickers:       list[str]
    weights:            dict[str, float]       # {symbol: weight}
    weights_df:         pd.DataFrame           # display table
    expected_return:    float
    volatility:         float
    sharpe:             float
    short_term_tickers: list[str]
    knockout_tickers:   list[str]
    portfolio_returns:  pd.Series
    mu:                 pd.Series
    S:                  pd.DataFrame
    # Data-length diagnostics (months of price data)
    period_months:      int = 0                # months in the analysis period
    risk_months:        int = 0                # months used for the covariance
    risk_zero_filled:   bool = False           # missing months were filled with 0%
    risk_start:         str = ""               # first month all assets have prices (YYYY-MM-DD)
    data_months:        dict[str, int] = field(default_factory=dict)
    # User-specified weights: no optimization. opt_* is the max-Sharpe portfolio
    # of the same assets (the ★ on the frontier); the fund itself is drawn as ◆.
    fixed_weights:      bool = False
    opt_return:         float | None = None
    opt_volatility:     float | None = None
    opt_sharpe:         float | None = None


@dataclass
class AnalysisResult:
    # Settings snapshot
    portfolio_name:  str
    start_date:      str
    end_date:        str
    risk_free_rate:  float
    min_weight:      float
    user_country:    str
    mdd_threshold:   float
    min_req_months:  int
    timestamp:       str

    # Multiple funds
    funds:             list[FundResult]

    # Shared data
    prices:            pd.DataFrame
    bench_tickers:     list[str]
    benchmark_labels:  dict[str, str]

    # Returns & metrics
    bench_returns:     pd.DataFrame
    comparison_df:     pd.DataFrame           # full perf table

    # ── Legacy single-fund accessors (for backward compat) ────────────────
    @property
    def confirmed_df(self) -> pd.DataFrame:
        return self.funds[0].confirmed_df if self.funds else pd.DataFrame()

    @property
    def fund_tickers(self) -> list[str]:
        return self.funds[0].fund_tickers if self.funds else []

    @property
    def weights(self) -> dict[str, float]:
        return self.funds[0].weights if self.funds else {}

    @property
    def weights_df(self) -> pd.DataFrame:
        return self.funds[0].weights_df if self.funds else pd.DataFrame()

    @property
    def expected_return(self) -> float:
        return self.funds[0].expected_return if self.funds else 0.0

    @property
    def volatility(self) -> float:
        return self.funds[0].volatility if self.funds else 0.0

    @property
    def sharpe(self) -> float:
        return self.funds[0].sharpe if self.funds else 0.0

    @property
    def short_term_tickers(self) -> list[str]:
        return self.funds[0].short_term_tickers if self.funds else []

    @property
    def knockout_tickers(self) -> list[str]:
        return self.funds[0].knockout_tickers if self.funds else []

    @property
    def portfolio_returns(self) -> pd.Series:
        return self.funds[0].portfolio_returns if self.funds else pd.Series()

    @property
    def mu(self) -> pd.Series:
        return self.funds[0].mu if self.funds else pd.Series()

    @property
    def S(self) -> pd.DataFrame:
        return self.funds[0].S if self.funds else pd.DataFrame()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_benchmarks(json5_path: str, user_country: str):
    with open(json5_path, "r", encoding="utf-8") as f:
        data = json5.load(f)
    cfg        = data.get(user_country) or data["DEFAULT"]
    benchmarks = sorted(cfg["benchmarks"], key=lambda x: x.get("priority", 99))
    return cfg, benchmarks, data


def _max_drawdown(series: pd.Series) -> float:
    cummax = series.cummax()
    return float((series / cummax - 1.0).min())


def _perf_stats(series: pd.Series) -> tuple[float, float, float]:
    ann_ret = float(series.mean() * 12)
    ann_vol = float(series.std() * np.sqrt(12))
    cum_ret = float((1 + series).prod() - 1)
    return ann_ret, ann_vol, cum_ret


def _sharpe(ann_ret: float, ann_vol: float, rfr: float) -> float:
    if ann_vol == 0:
        return float("nan")
    return round((ann_ret - rfr) / ann_vol, 3)


def _calc_portfolio_returns(
    returns_df: pd.DataFrame, weights: pd.Series
) -> pd.Series:
    result: dict = {}
    for date, row in returns_df.iterrows():
        listed = row.dropna()
        if listed.empty:
            continue
        w     = weights[listed.index]
        w_sum = float(w.sum())
        if w_sum == 0:
            continue
        result[date] = float((listed * (w / w_sum)).sum())
    return pd.Series(result)


def _calc_risk_metrics(series: pd.Series, bench: pd.Series, L: dict) -> dict:
    aligned = pd.concat([series, bench], axis=1).dropna()
    cov     = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    beta    = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else float("nan")
    var_95  = float(np.percentile(series.dropna(), 5))
    cvar_95 = float(series[series <= var_95].mean())
    excess  = series - bench.reindex(series.index)
    ir = (excess.mean() / excess.std() * np.sqrt(12)) if excess.std() > 0 else float("nan")
    return {
        L["col_beta"]:  round(beta, 3),
        L["col_var"]:   round(var_95, 4),
        L["col_cvar"]:  round(cvar_95, 4),
        L["col_ir"]:    round(ir, 3),
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_analysis(
    confirmed_df: pd.DataFrame,
    portfolio_name:  str,
    start_date:      str,
    end_date:        str,
    risk_free_rate:  float,
    min_weight:      float,
    user_country:    str,
    mdd_threshold:   float,
    min_req_months:  int,
    benchmarks_path: str,
    lang_dict:       dict,                    # _L[lang] for column names
    progress_cb:     Callable[[str], None] | None = None,
    comparison_fund_symbols: list[str] | None = None,
    comparison_fund_name:    str | None = None,
    *,
    multi_funds: list[dict] | None = None,
) -> AnalysisResult:
    """
    Full analysis pipeline. Returns AnalysisResult.
    progress_cb(message) is called at each step for UI feedback.

    multi_funds: list of dicts with keys "name" and "confirmed_df".
                 When provided, confirmed_df / comparison_fund_* params are ignored.
    """
    L = lang_dict

    def _progress(msg: str):
        if progress_cb:
            progress_cb(msg)

    # ── Normalize fund inputs ─────────────────────────────────────────────
    if multi_funds:
        fund_inputs = multi_funds
    else:
        # Legacy: single main fund + optional comparison
        fund_inputs = [{"name": portfolio_name, "confirmed_df": confirmed_df}]
        if comparison_fund_symbols:
            comp_cdf = pd.DataFrame([
                {"input": s, "symbol": s, "name": "", "exchange": "", "country": ""}
                for s in comparison_fund_symbols
            ])
            fund_inputs.append({
                "name": comparison_fund_name or "Comparison Fund",
                "confirmed_df": comp_cdf,
            })

    # ── Step 1: Load benchmarks ───────────────────────────────────────────
    country_cfg, benchmark_defs, benchmark_master = _load_benchmarks(
        benchmarks_path, user_country
    )
    benchmark_tickers = [b["symbol"] for b in benchmark_defs]
    benchmark_labels  = {b["symbol"]: b["name"] for b in benchmark_defs}

    # ── Step 2: Download prices ───────────────────────────────────────────
    _progress(L.get("step_download", "Downloading prices..."))

    # Collect all tickers from all funds
    all_fund_tickers: list[str] = []
    all_confirmed_dfs: list[pd.DataFrame] = []
    for fi in fund_inputs:
        cdf = fi["confirmed_df"]
        ticks = cdf["symbol"].dropna().unique().tolist()
        all_fund_tickers.extend(ticks)
        all_confirmed_dfs.append(cdf)
    all_fund_tickers_unique = sorted(set(all_fund_tickers))
    all_tickers = sorted(set(all_fund_tickers_unique + benchmark_tickers))

    prices_raw = yf.download(
        all_tickers,
        start    = start_date,
        end      = end_date,
        interval = "1mo",
        progress = False,
        auto_adjust = True,
    )

    if isinstance(prices_raw.columns, pd.MultiIndex):
        prices = prices_raw["Close"].copy()
    else:
        prices = prices_raw.copy()

    prices = prices.dropna(axis=1, how="all")

    # Yahoo Finance 国際 API にない JP 株への価格フォールバック
    _missing = [t for t in all_fund_tickers_unique
                if t not in prices.columns or prices[t].isna().all()]
    for t in _missing:
        if _infer_country_from_symbol(t) == "JP":
            _progress(L.get("step_download", "Downloading prices...")
                      + f" ({t} → Yahoo Finance Japan…)")
            jp_s = _yahoo_jp_fetch_monthly(t, start_date, end_date)
            if not jp_s.empty:
                prices[t] = jp_s.reindex(prices.index, method="ffill")

    available_fund_tickers = [t for t in all_fund_tickers_unique if t in prices.columns]
    bench_tickers = [t for t in benchmark_tickers if t in prices.columns]
    prices = prices[[t for t in prices.columns
                     if t in available_fund_tickers or t in bench_tickers]]

    # FX conversion
    _base_currency  = country_cfg.get("base_currency", "USD")
    _fx_tickers_map = country_cfg.get("fx_tickers", {})
    _country_to_currency = {
        cc: benchmark_master[cc]["base_currency"]
        for cc in benchmark_master
        if cc not in ("DEFAULT",) and "base_currency" in benchmark_master.get(cc, {})
    }

    _all_confirmed = pd.concat(all_confirmed_dfs, ignore_index=True)
    _fx_cache: dict[str, pd.Series] = {}
    for t in available_fund_tickers:
        row = _all_confirmed.loc[_all_confirmed["symbol"] == t, "country"]
        if row.empty:
            continue
        src_ccy  = _country_to_currency.get(row.values[0])
        if src_ccy and src_ccy != _base_currency:
            fx_entry = _fx_tickers_map.get(src_ccy)
            if not fx_entry:
                continue
            if isinstance(fx_entry, dict):
                fx_ticker = fx_entry["ticker"]
                fx_invert = fx_entry.get("invert", False)
            else:
                fx_ticker = fx_entry
                fx_invert = False
            if fx_ticker not in _fx_cache:
                fx_raw = yf.download(
                    fx_ticker, start=start_date, end=end_date,
                    interval="1mo", progress=False, auto_adjust=True,
                )
                if isinstance(fx_raw.columns, pd.MultiIndex):
                    fx_s = fx_raw["Close"].squeeze()
                else:
                    fx_s = fx_raw.squeeze()
                _fx_cache[fx_ticker] = fx_s.reindex(prices.index, method="ffill")
            fx_rate = _fx_cache[fx_ticker]
            prices[t] = prices[t] / fx_rate if fx_invert else prices[t] * fx_rate

    returns_all = prices.pct_change()
    bench_returns = returns_all[bench_tickers].dropna(how="all") if bench_tickers else pd.DataFrame()

    # ── Step 3–7: Optimize each fund ──────────────────────────────────────
    fund_results: list[FundResult] = []

    for fi_idx, fi in enumerate(fund_inputs):
        fund_name = fi["name"]
        cdf       = fi["confirmed_df"]
        f_tickers = [t for t in cdf["symbol"].dropna().unique().tolist()
                     if t in prices.columns]

        if not f_tickers:
            continue

        _progress(L.get("step_shortterm", "Checking short-term assets...")
                  + (f" ({fund_name})" if len(fund_inputs) > 1 else ""))
        month_counts = prices[f_tickers].notna().sum()
        short_term = [t for t in f_tickers if month_counts[t] < min_req_months]

        _progress(L.get("step_mdd", "Computing max drawdown...")
                  + (f" ({fund_name})" if len(fund_inputs) > 1 else ""))
        mdd_dict: dict[str, float] = {}
        for t in f_tickers:
            s = prices[t].dropna()
            if len(s) >= 2:
                mdd_dict[t] = _max_drawdown(s)
        knockout = [t for t, v in mdd_dict.items() if v <= mdd_threshold]

        fund_returns = returns_all[f_tickers].dropna(how="all")

        _progress(L.get("step_optimize", "Optimizing portfolio...")
                  + (f" ({fund_name})" if len(fund_inputs) > 1 else ""))
        # Expected returns and covariance come from the same sample: the months in
        # which every asset has data (standard MPT practice — mixing windows makes
        # the inputs inconsistent).
        _ret_cov = fund_returns.dropna()
        risk_zero_filled = False
        if len(_ret_cov) < max(12, len(f_tickers) + 1):
            risk_zero_filled = bool(fund_returns.isna().any().any())
            _ret_cov = fund_returns.fillna(0)
        mu = expected_returns.mean_historical_return(
            _ret_cov, returns_data=True, frequency=12, compounding=False
        )
        S = risk_models.CovarianceShrinkage(
            _ret_cov, returns_data=True, frequency=12
        ).ledoit_wolf()
        # First month with a price for every asset (= the start date that aligns the period)
        risk_start = (_ret_cov.index.min() - pd.DateOffset(months=1)
                      if not risk_zero_filled and len(_ret_cov) else None)

        n_assets = len(f_tickers)
        fixed = fi.get("weights")   # user-specified weights → min weight does not apply
        eff_min_w = 0.0 if fixed else (min(min_weight, 1.0 / n_assets) if n_assets > 0 else min_weight)
        opt_rfr = risk_free_rate if float(mu.max()) > risk_free_rate else 0.0

        def _build_ef(_mu=mu, _S=S, _emw=eff_min_w) -> EfficientFrontier:
            ef_ = EfficientFrontier(_mu, _S)
            if _emw > 0:
                ef_.add_constraint(lambda w: w >= _emw)
            return ef_

        ef = _build_ef()
        try:
            ef.max_sharpe(risk_free_rate=opt_rfr)
        except Exception:
            ef = _build_ef()
            ef.min_volatility()

        weights      = ef.clean_weights()
        exp_ret, vol, sharpe_val = ef.portfolio_performance(risk_free_rate=risk_free_rate)
        opt_perf     = None
        if fixed:
            # Keep the optimum only as the ★ reference; the fund uses the given weights
            # (renormalized in case an asset had no price data).
            opt_perf = (exp_ret, vol, sharpe_val)
            raw      = {t: float(fixed.get(t, 0.0)) for t in f_tickers}
            total    = sum(raw.values())
            weights  = {t: (w / total if total > 0 else 0.0) for t, w in raw.items()}
            w_vec    = pd.Series(weights)[mu.index]
            exp_ret  = float(w_vec @ mu)
            vol      = float(np.sqrt(w_vec @ S.loc[mu.index, mu.index] @ w_vec))
            sharpe_val = (exp_ret - risk_free_rate) / vol if vol > 0 else float("nan")
        w_series     = pd.Series(weights)
        pf_returns   = _calc_portfolio_returns(fund_returns, w_series)

        # Weights display table
        sym_to_name = dict(zip(cdf["symbol"], cdf.get("name", cdf["symbol"])))
        w_rows = [
            [f"{sym} / {sym_to_name.get(sym, sym)}", round(w * 100, 2)]
            for sym, w in weights.items() if w > 0
        ]
        w_rows.append([L["col_total"], round(sum(w for w in weights.values() if w > 0) * 100, 2)])
        w_df = pd.DataFrame(w_rows, columns=[L["col_ticker_name"], L["col_weight"]])

        fund_results.append(FundResult(
            fund_name          = fund_name,
            confirmed_df       = cdf,
            fund_tickers       = f_tickers,
            weights            = dict(weights),
            weights_df         = w_df,
            expected_return    = float(exp_ret),
            volatility         = float(vol),
            sharpe             = float(sharpe_val),
            short_term_tickers = short_term,
            knockout_tickers   = knockout,
            portfolio_returns  = pf_returns,
            mu                 = mu,
            S                  = S,
            # Counted in months of prices (n returns = n + 1 prices), as in month_counts
            period_months      = int(prices[f_tickers].notna().any(axis=1).sum()),
            risk_months        = len(_ret_cov) + 1,
            risk_zero_filled   = risk_zero_filled,
            risk_start         = risk_start.strftime("%Y-%m-%d") if risk_start is not None else "",
            data_months        = {t: int(month_counts[t]) for t in f_tickers},
            fixed_weights      = bool(fixed),
            opt_return         = float(opt_perf[0]) if opt_perf else None,
            opt_volatility     = float(opt_perf[1]) if opt_perf else None,
            opt_sharpe         = float(opt_perf[2]) if opt_perf else None,
        ))

    # ── Step 8: Risk metrics + comparison table ───────────────────────────
    _progress(L.get("step_risk", "Computing risk metrics..."))
    _primary_bench = bench_tickers[0] if bench_tickers else None

    # Use the first fund's index as the reference for alignment
    _ref_idx = fund_results[0].portfolio_returns.index if fund_results else pd.Index([])

    comp_rows: list[list] = []
    for fr in fund_results:
        pr = _perf_stats(fr.portfolio_returns)
        comp_rows.append([fr.fund_name,
                          _sharpe(pr[0], pr[1], risk_free_rate),
                          pr[0], pr[1], pr[2]])
    for sym in bench_tickers:
        br = _perf_stats(bench_returns[sym].reindex(_ref_idx).dropna())
        comp_rows.append([benchmark_labels[sym],
                          _sharpe(br[0], br[1], risk_free_rate),
                          br[0], br[1], br[2]])

    comparison_df = pd.DataFrame(
        comp_rows,
        columns=[L["col_portfolio"], L["col_sharpe"],
                 L["col_ann_return"], L["col_ann_risk"], L["col_cum_return"]]
    )

    if _primary_bench:
        _bench_clipped = bench_returns[_primary_bench].reindex(_ref_idx).dropna()
        for fr in fund_results:
            pm = _calc_risk_metrics(fr.portfolio_returns, _bench_clipped, L)
            for col, val in pm.items():
                comparison_df.loc[comparison_df[L["col_portfolio"]] == fr.fund_name, col] = val
        for sym in bench_tickers:
            bm = _calc_risk_metrics(
                bench_returns[sym].reindex(_ref_idx).dropna(), _bench_clipped, L
            )
            for col, val in bm.items():
                comparison_df.loc[comparison_df[L["col_portfolio"]] == benchmark_labels[sym], col] = val

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return AnalysisResult(
        portfolio_name     = portfolio_name,
        start_date         = start_date,
        end_date           = end_date,
        risk_free_rate     = risk_free_rate,
        min_weight         = min_weight,
        user_country       = user_country,
        mdd_threshold      = mdd_threshold,
        min_req_months     = min_req_months,
        timestamp          = timestamp,
        funds              = fund_results,
        prices             = prices,
        bench_tickers      = bench_tickers,
        benchmark_labels   = benchmark_labels,
        bench_returns      = bench_returns,
        comparison_df      = comparison_df,
    )
