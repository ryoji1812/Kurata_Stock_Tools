"""
app.py — Max Sharpe Portfolio Analyzer
Run:  streamlit run app.py
"""
from __future__ import annotations
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

import streamlit.components.v1 as components

from lang import get_text, _L
from symbol_input_component import render_symbol_table, handle_fund
from analysis import run_analysis
import charts_altair as ca
import charts_mpl    as cm
from downloads import (
    build_analysis_xlsx, build_resolved_xlsx,
    build_output_json, build_zip,
)
from cloud_backup import upload_to_drive_async
from charts_altair import DEFAULT_COLORS as _ALT_DEFAULTS, DEFAULT_STYLES as _ALT_STYLE_DEFAULTS
from analysis import _load_benchmarks

st.set_page_config(
    page_title="Kurata Stock Tools",
    page_icon="📈",
    layout="wide",
)

st.markdown("""<style>
/* Tab panel border */
[role="tabpanel"] {
    border: 1px solid rgba(49, 51, 63, 0.16);
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 1rem !important;
}
</style>""", unsafe_allow_html=True)

BENCHMARKS_PATH = "benchmarks.json5"
COUNTRY_OPTIONS = ["JP","US","GB","DE","FR","CN","HK","IN"]

_EXTRA = {
    "JP": {
        "hint_dblclick":          "クリックで編集",
        "hint_cancel_edit":       "編集をキャンセル",
        "hint_click_to_edit":     "クリックで再編集",
        "status_confirmed_short": "確定",
        "status_searching":       "検索中…",
        "status_duplicate":       "重複",
        "msg_duplicate":          "重複のため除外されました",
        "status_pick":            "候補から選んでください",
    },
    "EN": {
        "hint_dblclick":          "Click to edit",
        "hint_cancel_edit":       "Cancel edit",
        "hint_click_to_edit":     "Click to re-edit",
        "status_confirmed_short": "OK",
        "status_searching":       "Searching…",
        "status_duplicate":       "Duplicate",
        "msg_duplicate":          "Duplicate — skipped",
        "status_pick":            "Pick from the suggestions",
    },
}

def _T(k): return get_text(k, st.session_state.get("lang","JP"))
def _labels(lang): return {**_L.get(lang,_L["JP"]), **_EXTRA.get(lang,_EXTRA["JP"])}


# ── Fund helpers ──────────────────────────────────────────────────────────────

def _new_fund(idx: int = 1) -> dict:
    """Create a blank fund dict."""
    return {
        # Widget keys are built from this id (not the tab index), so deleting a
        # fund can't shift another fund's widgets. (id(object()) repeats values.)
        "id": uuid.uuid4().hex,
        "name": f"{_T('fund_default_name')} {idx}",
        "ticker_rows": [],
        "_sym_last_seq": -9999,
        "_sym_search_results": None,
        "_dup_notice": [],
    }


def _fund_widget_keys(fid: str) -> list[str]:
    """Session-state keys of the widgets that belong to one fund."""
    return [f"fund_name_{fid}", f"_cp_fund_{fid}", f"_sel_fund_style_{fid}", f"sym_fund_{fid}"]


def _ensure_fund_ids(funds: list[dict]) -> None:
    """Give every fund a unique id (sessions created before ids were unique)."""
    seen: set = set()
    for f in funds:
        if not isinstance(f.get("id"), str) or f["id"] in seen:
            f["id"] = uuid.uuid4().hex
        seen.add(f["id"])


def _init():
    today = date.today()
    _sd_default = today - timedelta(days=3 * 365)
    for k, v in dict(
        lang="JP", portfolio_name="MyPortfolio",
        start_date=_sd_default, end_date=today,
        risk_free_rate=0.0, min_weight=0.0,
        user_country="JP", mdd_threshold=-50, min_req_months=36,
        analysis_result=None, chart_bytes={},
        # Multi-fund state
        funds=None,
        # Chart color state
        color_portfolio=_ALT_DEFAULTS["portfolio"],
        color_bench=list(_ALT_DEFAULTS["benchmarks"]),
        style_portfolio=_ALT_STYLE_DEFAULTS["portfolio"],
        style_bench=list(_ALT_STYLE_DEFAULTS["benchmarks"]),
    ).items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Initialize funds list with one default fund
    if st.session_state.funds is None:
        st.session_state.funds = [_new_fund(1)]
    _ensure_fund_ids(st.session_state.funds)

    # 旧セッションで start_date が None のまま残っている場合の救済
    if st.session_state.start_date is None:
        st.session_state.start_date = _sd_default
    if st.session_state.end_date is None or st.session_state.end_date > today:
        st.session_state.end_date = today


_DATE_JS = """
<script>
(function () {
  var parentDoc = window.parent.document;

  // ── 既存値の右シフトを防ぐための DOM クリア用 setter ──────────────────
  var nativeSetter = Object.getOwnPropertyDescriptor(
    window.parent.HTMLInputElement.prototype, 'value'
  ).set;

  // ── 個別入力欄へのパッチ ──────────────────────────────────────────────
  function patch(input) {
    if (input._datePatchDone) return;
    input._datePatchDone = true;
    input._clearPending  = false;

    // 数値キーボード要求
    input.setAttribute("inputmode",      "numeric");

    // iOS 自動変換・補正を全面無効化
    input.setAttribute("autocomplete",   "off");
    input.setAttribute("autocorrect",    "off");
    input.setAttribute("autocapitalize", "none");
    input.setAttribute("spellcheck",     "false");

    // 日本語キーボードの IME 変換イベントを React に届かせない
    ["compositionstart", "compositionend", "compositionupdate"].forEach(function(ev) {
      input.addEventListener(ev, function(e) { e.stopPropagation(); }, true);
    });

    // フォーカス時に「最初の1打でクリア」フラグを立てる
    input.addEventListener("focus", function () {
      input._clearPending = true;
    }, false);
    input.addEventListener("blur", function () {
      input._clearPending = false;
    }, false);
  }

  // ── 親ページへの keydown capture リスナー（React より先に動く） ────────
  // 重複登録防止
  if (!parentDoc._dateKeydownPatched) {
    parentDoc._dateKeydownPatched = true;

    parentDoc.addEventListener("keydown", function (e) {
      var input = e.target;
      if (!input || !input._datePatchDone) return;
      if (!input._clearPending)            return;
      if (!/^[0-9]$/.test(e.key))          return;

      // 最初の数字キーが React に届く前に DOM 値だけ空にする。
      // React はこのキーを「空フィールドへの入力」として処理するため
      // 既存の年桁との右シフト混入（例: 2022→2202）が起きなくなる。
      input._clearPending = false;
      nativeSetter.call(input, "");
      // ※ input/change イベントは発火しない → Streamlit state は変わらず
      //    React が後続の keydown を処理して年セクションを "2___" から開始する
    }, true); // capture = React のデリゲートより前
  }

  // ── MutationObserver で動的に追加された入力欄もパッチ ─────────────────
  function findAndPatch() {
    parentDoc.querySelectorAll('[data-testid="stDateInputField"] input').forEach(patch);
  }

  findAndPatch();
  new MutationObserver(findAndPatch).observe(
    parentDoc.body,
    { subtree: true, childList: true }
  );
})();
</script>
"""


def _inject_date_js():
    components.html(_DATE_JS, height=0)


# ── Fund tab "×" buttons ──────────────────────────────────────────────────────
# st.tabs() has no close button, so a "×" is inserted into each fund tab of the
# parent page. Clicking it clicks that fund's hidden st.button
# (key fund_close_<id>), which opens the confirm dialog on the Python side.
# The installer runs in the parent page's realm (window.parent.Function) and a
# MutationObserver re-inserts the "×" whenever Streamlit re-renders the tabs;
# each rerun only refreshes the fund-id list (window.__kstTabClose.fids).
_TAB_CLOSE_INSTALL = r"""
if (!window.__kstTabClose) {
  const S = window.__kstTabClose = { fids: [], hint: '' };
  // role="tablist" is the ARIA role, stable across Streamlit's tab implementations
  const fundList = () => [...document.querySelectorAll('[role="tablist"]')]
    .find(l => { const t = l.querySelector('[role="tab"]');
                 return t && /^(ファンド|Fund) 1$/.test(t.innerText.replace('×', '').trim()); });
  S.apply = () => {
    const list = fundList();
    if (!list) return;
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    tabs.forEach((tab, i) => {
      let x = tab.querySelector(':scope .kst-x');
      const fid = (S.fids.length > 1 && i < S.fids.length) ? S.fids[i] : null;
      if (!fid) { if (x) x.remove(); return; }
      if (!x) {
        x = document.createElement('span');
        x.className = 'kst-x'; x.textContent = '×'; x.setAttribute('role', 'button');
        const stop = e => { e.preventDefault(); e.stopPropagation(); };
        ['pointerdown', 'mousedown', 'mouseup'].forEach(t => x.addEventListener(t, stop));
        x.addEventListener('click', e => {
          stop(e);
          const b = document.querySelector('.st-key-fund_close_' + x.dataset.fid + ' button');
          if (b) b.click();
        });
        tab.appendChild(x);
      }
      if (x.dataset.fid !== fid) x.dataset.fid = fid;
      if (x.title !== S.hint) x.title = S.hint;
    });
  };
  new MutationObserver(() => S.apply())
    .observe(document.body, { subtree: true, childList: true });
}
"""


def _inject_tab_close_js(fund_ids: list[str], hint: str) -> None:
    components.html(f"""<script>
    (function () {{
      const P = window.parent;
      P.Function({json.dumps(_TAB_CLOSE_INSTALL)})();
      P.__kstTabClose.fids = {json.dumps(fund_ids)};
      P.__kstTabClose.hint = {json.dumps(hint)};
      P.__kstTabClose.apply();
    }})();
    </script>""", height=0)


def _delete_fund(fid: str) -> None:
    funds = st.session_state.funds
    st.session_state.funds = [f for f in funds if f["id"] != fid]
    for k in _fund_widget_keys(fid):
        st.session_state.pop(k, None)


def _confirm_delete_fund(fid: str) -> None:
    fund = next((f for f in st.session_state.funds if f["id"] == fid), None)
    if fund is None:
        return
    n_confirmed = sum(1 for r in fund.get("ticker_rows", []) if r.get("confirmed"))

    @st.dialog(_T("dlg_del_fund_title"))
    def _dialog():
        st.write(_T("msg_del_fund_confirm").format(name=fund["name"], n=n_confirmed))
        c_ok, c_cancel = st.columns(2)
        if c_ok.button(_T("btn_del_fund"), type="primary", key="dlg_del_fund_ok",
                       use_container_width=True):
            _delete_fund(fid)
            st.rerun()
        if c_cancel.button(_T("btn_cancel"), key="dlg_del_fund_cancel",
                           use_container_width=True):
            st.rerun()

    _dialog()


def _top_bar():
    c1, c2 = st.columns([6, 1])
    c1.markdown("## 📈 Kurata Stock Tools")
    with c2:
        _opts   = ["JP", "EN"]
        _labels = {"JP": "日本語", "EN": "English"}
        sel = st.selectbox(
            "",
            options=_opts,
            index=_opts.index(st.session_state.lang),
            format_func=lambda x: _labels[x],
            label_visibility="collapsed",
            key="lang_sel",
        )
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()
    st.info(_T("app_notice"), icon="ℹ️")
    st.divider()



def _period():
    st.markdown(
        f"<h3>{_T('section_period_settings')}</h3>",
        unsafe_allow_html=True,
    )
    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        sd = st.date_input(
            _T("label_start_date"),
            value=st.session_state.start_date,
            max_value=today,
            key="sd_cal",
        )
        st.session_state.start_date = sd
    with c2:
        ed = st.date_input(
            _T("label_end_date"),
            value=min(st.session_state.end_date, today),
            max_value=today,
            key="ed_cal",
        )
        st.session_state.end_date = ed
    _inject_date_js()
    _advanced()


def _advanced():
    with st.expander(_T("section_advanced"),expanded=False):
        c1,c2,c3=st.columns(3)
        with c1:
            st.session_state.risk_free_rate=st.number_input(
                _T("label_risk_free_rate"),value=float(st.session_state.risk_free_rate),
                min_value=0.0,step=0.1,format="%.2f",key="rfr")
            st.caption(_T("desc_risk_free_rate"))
        with c2:
            _mw=st.number_input(
                _T("label_min_weight"),value=float(st.session_state.min_weight),
                min_value=0.0,max_value=100.0,step=1.0,format="%.1f",key="mw")
            if _mw != st.session_state.min_weight and _mw != 0.0:
                st.toast(_T("warn_min_weight"), icon="⚠️")
            st.session_state.min_weight=_mw
            st.caption(_T("desc_min_weight"))
        with c3:
            idx=COUNTRY_OPTIONS.index(st.session_state.user_country) \
                if st.session_state.user_country in COUNTRY_OPTIONS else 0
            nc=st.selectbox(_T("label_user_country"),COUNTRY_OPTIONS,index=idx,key="ctry")
            if nc!=st.session_state.user_country:
                st.session_state.user_country=nc
            st.caption(_T("desc_user_country"))
        c4,c5=st.columns(2)
        with c4:
            st.session_state.mdd_threshold=st.slider(
                _T("label_mdd_threshold"),-100,0,step=5,
                value=int(st.session_state.mdd_threshold),format="%d%%",key="mdd")
            st.caption(_T("desc_mdd_threshold"))
        with c5:
            st.session_state.min_req_months=st.number_input(
                _T("label_min_months"),value=int(st.session_state.min_req_months),
                min_value=1,max_value=120,step=1,key="mon")
            st.caption(_T("desc_min_months"))


# ── Multi-fund vertical tabs ────────────────────────────────────────────────

_FUND_COLORS = ["#2563EB", "#E74C3C", "#16A085", "#8E44AD",
                "#F39C12", "#1ABC9C", "#E67E22", "#3498DB"]


def _fund_tabs():
    """Render the multi-fund tab interface using st.tabs()."""
    funds = st.session_state.funds

    st.subheader(_T("section_funds"))

    if not funds:
        # No tabs yet — show the add button on its own (right-aligned).
        _, col_add_empty = st.columns([10, 1])
        with col_add_empty:
            if st.button(
                "＋",
                key="add_fund",
                help=_T("btn_add_fund"),
                use_container_width=True,
            ):
                funds.append(_new_fund(len(funds) + 1))
                st.rerun()
        st.info(_T("fund_tab_empty"))
        return

    # Tab labels must be 100% STABLE across reruns — st.tabs() resets
    # to the first tab whenever ANY label string changes.
    # Use fixed index-based labels; the user-chosen name is shown inside.
    tab_labels = [f"{_T('fund_default_name')} {i+1}" for i in range(len(funds))]

    # Append fixed benchmark tabs
    bench_names = _bench_names()
    bench_colors = st.session_state.color_bench
    bench_styles = st.session_state.style_bench
    n_funds = len(funds)
    for bn in bench_names:
        tab_labels.append(f"📊 {bn}")

    # CSS overlay: right-align the "+" button on the tab bar.
    # Approach:
    #   1. Hide style-only stMarkdown containers — they would otherwise add a
    #      phantom 1rem flex gap between h3 and the button.
    #   2. Use align-self/margin-left auto to right-align the button container
    #      within the flex column (`float` doesn't work on flex items).
    #   3. Negative margin-bottom pulls the tab bar up to overlay the button.
    st.markdown(
        """
        <style>
        /* Hidden per-fund delete buttons — clicked by the tab "×" (see
           _TAB_CLOSE_INSTALL); kept in the DOM but never shown. */
        [class*="st-key-fund_close_"] { display: none !important; }

        /* "×" inside each fund tab */
        .kst-x {
            margin-left: 0.45rem;
            padding: 0 0.3rem;
            border-radius: 4px;
            font-size: 0.95em;
            line-height: 1.2;
            opacity: 0.5;
            cursor: pointer;
        }
        .kst-x:hover { opacity: 1; background: rgba(128, 128, 128, 0.22); }

        /* Eliminate the flex gap contribution of style-only markdown blocks.
           Note: ":only-child" can't be used because indentation whitespace in
           the Python string creates text nodes around the <style> tag — the
           style is not the sole child. Use descendant selector instead. */
        [data-testid="stElementContainer"]:has([data-testid="stMarkdown"] style) {
            display: none !important;
        }

        /* Right-align "+" button overlaid on tab bar */
        .st-key-add_fund {
            align-self: flex-end !important;
            margin-left: auto !important;
            margin-right: 0.5rem !important;
            margin-top: 0 !important;
            margin-bottom: -3rem !important;
            width: fit-content !important;
            max-width: fit-content !important;
            padding: 0 !important;
            position: relative;
            z-index: 10;
        }
        .st-key-add_fund button {
            min-height: 38px;
            padding: 0 0.75rem;
            font-weight: 600;
            white-space: nowrap;
        }

        /* Reserve right space so tabs don't slip under "+" */
        [data-baseweb="tab-list"] {
            padding-right: 4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("＋", key="add_fund", help=_T("btn_add_fund")):
        funds.append(_new_fund(len(funds) + 1))
        st.rerun()

    # Hidden delete triggers for the tab "×" (no "×" when only one fund)
    if n_funds > 1:
        for f in funds:
            if st.button("×", key=f"fund_close_{f['id']}"):
                _confirm_delete_fund(f["id"])

    tabs = st.tabs(tab_labels)

    # ── Fund tabs ─────────────────────────────────────────────────────────
    for i in range(n_funds):
        with tabs[i]:
            fund = funds[i]
            fid  = fund["id"]  # widget keys follow the fund, not the tab position

            # Fund name — widget key is the source of truth.
            # Sync to fund dict only via the key read, never triggering a
            # label-changing rerun.
            _fname_key = f"fund_name_{fid}"
            st.text_input(
                _T("fund_name_label"),
                value=fund["name"],
                placeholder=_T("fund_name_placeholder"),
                key=_fname_key,
            )
            # Always keep fund dict in sync (labels don't use this value)
            fund["name"] = st.session_state.get(_fname_key, fund["name"])

            # Chart style (color + line style) in expander
            c_key = f"_cp_fund_{fid}"
            s_key = f"_sel_fund_style_{fid}"
            c_default = _FUND_COLORS[i % len(_FUND_COLORS)]
            c_val = st.session_state.get(c_key, c_default)
            s_val = st.session_state.get(s_key, "solid")

            with st.expander(_T("section_chart_colors"), expanded=False):
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.color_picker(_T("fund_chart_style_label"),
                                    value=c_val, key=c_key)
                with sc2:
                    st.selectbox(_T("fund_line_style_label"), _STYLE_KEYS,
                                 key=s_key,
                                 index=_STYLE_KEYS.index(s_val) if s_val in _STYLE_KEYS else 0,
                                 format_func=lambda k: _T(f"style_{k}"))

            # Symbol table
            st.caption(_T("sym_table_hint"))
            lang    = st.session_state.lang
            country = st.session_state.user_country

            cv = render_symbol_table(
                rows           = fund.get("ticker_rows", []),
                lang           = lang,
                country        = country,
                labels         = _labels(lang),
                search_results = fund.get("_sym_search_results"),
                key            = f"sym_fund_{fid}",
            )

            action = handle_fund(cv, fund)
            if action == "new_results":
                st.rerun()
            if action == "rows_update":
                fund["_sym_search_results"] = None

            dupes = fund.pop("_dup_notice", []) if isinstance(fund.get("_dup_notice"), list) else []
            if dupes:
                st.toast(f"⚠️ {', '.join(dupes)} — {_T('msg_duplicate')}", icon="⚠️")

    # ── Benchmark tabs (fixed, style-only) ────────────────────────────────
    _BENCH_STYLE_DEFAULTS = ["dashed", "dotted", "dashdot", "solid", "dashed"]
    for bi, bn in enumerate(bench_names):
        with tabs[n_funds + bi]:
            c_key = f"_cp_bench_{bi}"
            s_key = f"_sel_bench_style_{bi}"
            c_val = bench_colors[bi] if bi < len(bench_colors) else "#9CA3AF"
            s_val = bench_styles[bi] if bi < len(bench_styles) else _BENCH_STYLE_DEFAULTS[bi % len(_BENCH_STYLE_DEFAULTS)]

            with st.expander(_T("section_chart_colors"), expanded=True):
                sc1, sc2 = st.columns(2)
                with sc1:
                    new_c = st.color_picker(_T("fund_chart_style_label"),
                                            value=c_val, key=c_key)
                with sc2:
                    new_s = st.selectbox(_T("fund_line_style_label"), _STYLE_KEYS,
                                         key=s_key,
                                         index=_STYLE_KEYS.index(s_val) if s_val in _STYLE_KEYS else 0,
                                         format_func=lambda k: _T(f"style_{k}"))

            # Sync back to session state lists
            if bi < len(bench_colors):
                bench_colors[bi] = new_c
            if bi < len(bench_styles):
                bench_styles[bi] = new_s
            else:
                bench_styles.append(new_s)

    st.session_state.color_bench = bench_colors
    st.session_state.style_bench = bench_styles

    # "×" on fund tabs (after the tabs so the 0-height iframe can't shift the
    # "+" overlay); an empty id list removes them when only one fund is left
    _inject_tab_close_js([f["id"] for f in funds] if n_funds > 1 else [],
                         _T("hint_close_fund"))


def _bench_names() -> list[str]:
    """Return display names for index benchmarks."""
    try:
        _, defs, _ = _load_benchmarks(BENCHMARKS_PATH, st.session_state.user_country)
        names = [b["name"] for b in defs]
    except Exception:
        names = []
    return names


_STYLE_KEYS = ["solid", "dashed", "dotted", "dashdot"]




def _get_custom_colors() -> dict:
    _FUND_COLORS_DEFAULT = ["#2563EB", "#E74C3C", "#16A085", "#8E44AD",
                            "#F39C12", "#1ABC9C", "#E67E22", "#3498DB"]
    funds = st.session_state.funds
    fund_colors = []
    fund_styles = []
    for i, fund in enumerate(funds):
        fid = fund["id"]
        fund_colors.append(st.session_state.get(
            f"_cp_fund_{fid}", _FUND_COLORS_DEFAULT[i % len(_FUND_COLORS_DEFAULT)]))
        fund_styles.append(st.session_state.get(f"_sel_fund_style_{fid}", "solid"))
    return {
        "fund_colors": fund_colors,
        "fund_styles": fund_styles,
        "benchmarks": list(st.session_state.color_bench),
        "bench_styles": list(st.session_state.style_bench),
        # Legacy single-fund compat
        "portfolio": fund_colors[0] if fund_colors else "#2563EB",
        "portfolio_style": fund_styles[0] if fund_styles else "solid",
    }


def _run_button():
    funds = st.session_state.funds
    all_ok = []
    bad_funds = []
    has_bad_rows = False

    for i, fund in enumerate(funds):
        rows = fund.get("ticker_rows", [])
        ok   = [r for r in rows if r.get("confirmed")]
        bad  = [r for r in rows if not r.get("confirmed")
                and not r.get("duplicate") and r.get("symbol", "").strip()]
        if ok:
            all_ok.extend(ok)
        else:
            bad_funds.append(fund["name"] or f"{_T('fund_default_name')} {i+1}")
        if bad:
            has_bad_rows = True

    bad_order = (
        st.session_state.start_date is not None
        and st.session_state.start_date >= st.session_state.end_date
    )
    st.write("")
    if not funds:
        st.info(_T("warn_no_funds"))
    elif not all_ok:
        st.info(_T("warn_no_confirmed"))
    elif bad_funds:
        st.warning(_T("warn_fund_no_confirmed").format(names=", ".join(bad_funds)))
    if has_bad_rows:
        st.warning(_T("warn_has_unconfirmed"))
    if bad_order:
        st.warning(_T("warn_date_order"))

    blocked = not all_ok or has_bad_rows or bad_order or bool(bad_funds)
    return st.button(_T("btn_run"), type="primary", disabled=blocked, key="run")


def _autosave(res, L: dict, chart_bytes: dict) -> None:
    """分析結果を ./portfolios/<name>_<timestamp>/ に自動保存する（zip 以外）。"""
    ts      = res.timestamp.replace("-", ".").replace(" ", "_").replace(":", ".")
    out_dir = Path("portfolios") / f"{res.portfolio_name}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "analysis_results.xlsx").write_bytes(build_analysis_xlsx(res, L))
    (out_dir / "resolved_symbols.xlsx").write_bytes(build_resolved_xlsx(res))
    (out_dir / "output.json").write_bytes(build_output_json(res, L))
    for fname, data in chart_bytes.items():
        if data:
            (out_dir / fname).write_bytes(data)
    upload_to_drive_async(out_dir)


def _analyse():
    L     = _L[st.session_state.lang]
    funds = st.session_state.funds

    # Build multi_funds input for analysis
    multi_funds = []
    for fund in funds:
        confirmed = [r for r in fund.get("ticker_rows", []) if r.get("confirmed")]
        if not confirmed:
            continue
        cdf = pd.DataFrame([
            dict(input=r["symbol"], symbol=r["symbol"], name=r.get("name", ""),
                 exchange=r.get("exchange", ""), country=r.get("country", ""))
            for r in confirmed
        ])
        multi_funds.append({
            "name": fund["name"] or f"Fund {len(multi_funds)+1}",
            "confirmed_df": cdf,
        })

    msgs = []; ph = st.empty()
    def _p(m): msgs.append(m); ph.info("  \n".join(msgs))
    try:
        res = run_analysis(
            confirmed_df    = multi_funds[0]["confirmed_df"],  # legacy param
            portfolio_name  = st.session_state.portfolio_name,
            start_date      = str(st.session_state.start_date),
            end_date        = str(st.session_state.end_date),
            risk_free_rate  = float(st.session_state.risk_free_rate) / 100,
            min_weight      = float(st.session_state.min_weight) / 100,
            user_country    = st.session_state.user_country,
            mdd_threshold   = float(st.session_state.mdd_threshold) / 100,
            min_req_months  = int(st.session_state.min_req_months),
            benchmarks_path = BENCHMARKS_PATH,
            lang_dict       = L,
            progress_cb     = _p,
            multi_funds     = multi_funds,
        )
        _p(_T("step_done"))
        st.session_state.analysis_result = res
        cc = _get_custom_colors()
        chart_bytes = {
            "cumulative_return_summary.png":    cm.mpl_cum_bar(res, L, custom=cc),
            "cumulative_return_timeseries.png": cm.mpl_cum_line(res, L, custom=cc),
            "rolling_sharpe.png":               cm.mpl_rolling_sharpe(res, L, custom=cc),
            "drawdown.png":                     cm.mpl_drawdown(res, L, custom=cc),
        }
        # Per-fund efficient frontier charts
        for fi, fr in enumerate(res.funds):
            suffix = f"_{fr.fund_name}" if len(res.funds) > 1 else ""
            chart_bytes[f"efficient_frontier{suffix}.png"] = \
                cm.mpl_efficient_frontier(res, L, fund_idx=fi)
        st.session_state.chart_bytes = chart_bytes
        _autosave(res, L, chart_bytes)
    except Exception as e:
        ph.error(f"{_T('analysis_error')}: {e}"); raise
    finally:
        ph.empty()


def _sec(t, d): st.subheader(_T(t)); st.markdown(_T(d))
def _dl(f):
    d = st.session_state.chart_bytes.get(f, b"")
    if d: st.download_button(_T("btn_download_png"), d, f, "image/png", key=f"dl_{f}")

def _results():
    res = st.session_state.analysis_result
    if res is None: return
    L = _L[st.session_state.lang]
    st.divider()

    # ── Per-fund weights ─────────────────────────────────────────────────
    _sec("section_weights", "desc_weights")
    if len(res.funds) == 1:
        # Single fund: same layout as before
        c1, c2 = st.columns([1.2, 1])
        with c1: st.dataframe(res.funds[0].weights_df, use_container_width=True, hide_index=True)
        with c2:
            try: st.altair_chart(ca.chart_weights(res, L, fund_idx=0), use_container_width=True)
            except Exception as e: st.warning(str(e))
    else:
        # Multiple funds: tabbed view
        fund_tabs = st.tabs([fr.fund_name for fr in res.funds])
        for fi, tab in enumerate(fund_tabs):
            with tab:
                c1, c2 = st.columns([1.2, 1])
                with c1: st.dataframe(res.funds[fi].weights_df, use_container_width=True, hide_index=True)
                with c2:
                    try: st.altair_chart(ca.chart_weights(res, L, fund_idx=fi), use_container_width=True)
                    except Exception as e: st.warning(str(e))

    st.divider(); _sec("section_performance", "desc_performance")
    _pct = st.column_config.NumberColumn(format="percent")
    _num = st.column_config.NumberColumn(format="%.3f")
    st.dataframe(
        res.comparison_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            L["col_sharpe"]:     _num,
            L["col_ann_return"]: _pct,
            L["col_ann_risk"]:   _pct,
            L["col_cum_return"]: _pct,
            L["col_var"]:        _pct,
            L["col_cvar"]:       _pct,
            L["col_beta"]:       _num,
            L["col_ir"]:         _num,
        },
    )
    xlsx_b = build_analysis_xlsx(res, L)
    res_b  = build_resolved_xlsx(res)
    st.download_button(_T("download_xlsx"), xlsx_b, "analysis_results.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="xl")

    cc = _get_custom_colors()

    st.divider(); _sec("section_cum_bar", "desc_cum_bar")
    try: st.altair_chart(ca.chart_cum_bar(res, L, custom_colors=cc), use_container_width=True)
    except Exception as e: st.warning(str(e))
    _dl("cumulative_return_summary.png")

    # ── Efficient frontier (per-fund) ─────────────────────────────────────
    st.divider(); _sec("section_frontier", "desc_frontier")
    if len(res.funds) == 1:
        try: st.altair_chart(ca.chart_efficient_frontier(res, L, fund_idx=0), use_container_width=True)
        except Exception as e: st.warning(str(e))
        _dl("efficient_frontier.png")
    else:
        ef_tabs = st.tabs([fr.fund_name for fr in res.funds])
        for fi, tab in enumerate(ef_tabs):
            with tab:
                try: st.altair_chart(ca.chart_efficient_frontier(res, L, fund_idx=fi), use_container_width=True)
                except Exception as e: st.warning(str(e))
                _dl(f"efficient_frontier_{res.funds[fi].fund_name}.png")

    st.divider(); _sec("section_cum_line", "desc_cum_line")
    try: st.altair_chart(ca.chart_cum_line(res, L, custom_colors=cc), use_container_width=True)
    except Exception as e: st.warning(str(e))
    _dl("cumulative_return_timeseries.png")

    st.divider(); _sec("section_rolling", "desc_rolling")
    try: st.altair_chart(ca.chart_rolling_sharpe(res, L, custom_colors=cc), use_container_width=True)
    except Exception as e: st.warning(str(e))
    _dl("rolling_sharpe.png")

    st.divider(); _sec("section_drawdown", "desc_drawdown")
    try: st.altair_chart(ca.chart_drawdown(res, L, custom_colors=cc), use_container_width=True)
    except Exception as e: st.warning(str(e))
    _dl("drawdown.png")

    st.divider(); st.subheader(_T("btn_download_all"))
    json_b = build_output_json(res, L)
    zip_b  = build_zip(xlsx_bytes=xlsx_b, resolved_bytes=res_b,
                       json_bytes=json_b, chart_bytes=st.session_state.chart_bytes)
    _ts = res.timestamp.replace("-", ".").replace(" ", "_").replace(":", ".")
    _zip_name = f"{res.portfolio_name}_{_ts}.zip"
    cz, cj, cr = st.columns(3)
    cz.download_button(_T("btn_download_all"), zip_b,
        _zip_name, "application/zip", key="zip")
    cj.download_button(_T("download_json"), json_b, "output.json",
        "application/json", key="json_dl")
    cr.download_button(_T("download_resolved"), res_b, "resolved_symbols.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="res_dl")


def main():
    _init(); _top_bar()
    st.markdown(_T("app_description"))
    st.write("")
    _period()
    _fund_tabs()
    st.write("")
    if _run_button():
        with st.spinner(""): _analyse()
        st.rerun()
    _results()
    st.divider()
    st.caption(_T("edinet_attribution"))

if __name__ == "__main__":
    main()
