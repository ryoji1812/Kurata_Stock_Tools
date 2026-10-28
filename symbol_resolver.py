"""
symbol_resolver.py — Yahoo Finance ticker search and resolution.

Improvements over previous version:
  • Extended exchange-code → country mapping (TYO, OSA, TWO, etc.)
  • Symbol-suffix country inference (.T/.OS = JP, .L = GB, .HK = HK, etc.)
    so stocks like 7817.T are recognised even when the exchange code is unknown
  • When query contains a country suffix (.T, .L, …), also search the bare
    base code (e.g. "7817") for broader coverage
  • The "." fallback appending is skipped when the query already has a "."
    (avoids nonsense queries like "7817.T.")
"""

from __future__ import annotations

import re
import sys
import time
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from edinet_codelist import has_japanese, search_jp_names, jp_name_for

# ── Constants ──────────────────────────────────────────────────────────────────
YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_INTERVAL = 0.2

# ── Exchange code → country ───────────────────────────────────────────────────
_EXCH_TO_COUNTRY: dict[str, str] = {
    # Japan
    "JPX": "JP", "TSE": "JP", "TYO": "JP", "OSA": "JP",
    "SAP": "JP", "FKA": "JP", "NGO": "JP",
    # US
    "NMS": "US", "NYQ": "US", "NGM": "US", "PCX": "US",
    "BTS": "US", "ASE": "US",
    # HK
    "HKG": "HK",
    # UK
    "LSE": "GB", "IOB": "GB",
    # Germany
    "XETRA": "DE", "FRA": "DE", "GER": "DE", "HAM": "DE",
    # France
    "PAR": "FR",
    # China
    "SHH": "CN", "SHZ": "CN",
    # India
    "NSI": "IN", "BSE": "IN",
    # Taiwan
    "TWO": "TW", "TAI": "TW",
    # Korea
    "KSC": "KR", "KOE": "KR",
    # Australia
    "ASX": "AU",
    # Canada
    "TRT": "CA", "TRV": "CA",
    # Singapore
    "SES": "SG",
}

# ── Symbol suffix → country ───────────────────────────────────────────────────
_SUFFIX_TO_COUNTRY: dict[str, str] = {
    ".T":   "JP",
    ".OS":  "JP",
    ".FK":  "JP",
    ".L":   "GB",
    ".HK":  "HK",
    ".SS":  "CN",
    ".SZ":  "CN",
    ".DE":  "DE",
    ".F":   "DE",
    ".PA":  "FR",
    ".AS":  "NL",
    ".BR":  "BE",
    ".MC":  "ES",
    ".MI":  "IT",
    ".ST":  "SE",
    ".OL":  "NO",
    ".CO":  "DK",
    ".HE":  "FI",
    ".WA":  "PL",
    ".TW":  "TW",
    ".TWO": "TW",
    ".KS":  "KR",
    ".KQ":  "KR",
    ".AX":  "AU",
    ".TO":  "CA",
    ".V":   "CA",
    ".SI":  "SG",
    ".NS":  "IN",
    ".BO":  "IN",
}


# ── Country → candidate suffixes to try when search fails ───────────────────
# Used as a 4th search strategy in search_suggestions()
_COUNTRY_SUFFIXES: dict[str, list[str]] = {
    "JP": [".T", ".OS", ".FK"],
    "GB": [".L"],
    "HK": [".HK"],
    "DE": [".DE", ".F"],
    "FR": [".PA"],
    "CN": [".SS", ".SZ"],
    "IN": [".NS", ".BO"],
    "TW": [".TW", ".TWO"],
    "KR": [".KS", ".KQ"],
    "AU": [".AX"],
    "CA": [".TO"],
    "SG": [".SI"],
    "NL": [".AS"],
    "SE": [".ST"],
    "NO": [".OL"],
    "DK": [".CO"],
}


def _infer_country_from_symbol(symbol: str) -> str | None:
    sym = symbol.upper()
    for suffix in sorted(_SUFFIX_TO_COUNTRY, key=len, reverse=True):
        if sym.endswith(suffix.upper()):
            return _SUFFIX_TO_COUNTRY[suffix]
    return None


# ── Raw search (cached per session) ───────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _yahoo_search_cached(query: str, count: int = 20) -> list[dict]:
    wait = 1.0
    for attempt in range(3):
        time.sleep(REQUEST_INTERVAL)
        try:
            r = requests.get(
                YAHOO_SEARCH_URL,
                params={"q": query, "quotesCount": count, "newsCount": 0},
                headers=HEADERS,
                timeout=6,
            )
            if r.status_code == 429:
                time.sleep(wait); wait *= 2; continue
            r.raise_for_status()
            return r.json().get("quotes", [])
        except requests.RequestException:
            time.sleep(wait); wait *= 2
    return []


def _extract_equities(quotes: list[dict]) -> list[dict]:
    return [
        {
            "symbol":   q.get("symbol", ""),
            "name":     q.get("shortname") or q.get("longname") or "",
            "exchange": (q.get("exchange") or "").upper(),
        }
        for q in quotes
        if q.get("quoteType") == "EQUITY"
    ]


def _score_candidates(candidates: list[dict], preferred_country: str) -> list[dict]:
    scored = []
    for c in candidates:
        symbol  = c.get("symbol", "")
        country = _EXCH_TO_COUNTRY.get(c["exchange"])
        if not country:
            country = _infer_country_from_symbol(symbol)
        score = 0 if country == preferred_country else 10
        scored.append({**c, "country": country or "", "score": score})
    return sorted(scored, key=lambda x: x["score"])


def _merge(base: list[dict], extra: list[dict]) -> list[dict]:
    seen = {c["symbol"] for c in base}
    out  = list(base)
    for c in extra:
        if c["symbol"] not in seen:
            out.append(c)
            seen.add(c["symbol"])
    return sorted(out, key=lambda x: x["score"])


# ── Public API ─────────────────────────────────────────────────────────────────

def search_suggestions(query: str, preferred_country: str, count: int = 20) -> list[dict]:
    """_search_suggestions + 日本株には表示用の日本語名（name_ja）を付ける。

    name（Yahoo の名前）は出力用にそのまま残す。
    """
    results = _search_suggestions(query, preferred_country, count)
    for c in results:
        c.setdefault("name_ja", jp_name_for(c.get("symbol", "")))
    return results


def _search_suggestions(query: str, preferred_country: str, count: int = 20) -> list[dict]:
    """
    Search Yahoo Finance and return a prioritised list of equity candidates.

    Four strategies tried in order, stopping when preferred-country hit found:
      1. Query as-is
      2. Strip country suffix  ("7817.T" → "7817")
      3. Append "."           ("7817"   → "7817.")  — only when no "." in query
      4. Try country suffixes ("7817"   → "7817.T", "7817.OS", ...)
         This covers stocks not indexed in Yahoo Finance search by bare code.
    """
    if not query:
        return []

    # 0. 日本語の銘柄名 → EDINET コードリストで検索（Yahoo 検索は日本語不可）
    if has_japanese(query):
        return search_jp_names(query)

    prioritized: list[dict] = []

    def _add(q: str) -> bool:
        """Search q, merge results, return True if preferred-country hit found."""
        nonlocal prioritized
        extra = _score_candidates(
            _extract_equities(_yahoo_search_cached(q, count)),
            preferred_country,
        )
        prioritized = _merge(prioritized, extra)
        return any(c["country"] == preferred_country for c in prioritized)

    # 1. As-is
    if _add(query):
        return prioritized[:8]

    # 2. Strip suffix  (e.g. "7817.T" → "7817")
    bare = re.sub(r'\.[A-Za-z]+$', '', query)
    if bare != query:
        if _add(bare):
            return prioritized[:8]

    # 3. Append "."  (e.g. "7817" → "7817.")  — skip when "." already present
    if "." not in query:
        if _add(query + "."):
            return prioritized[:8]

    # 4. Country-specific suffixes  (e.g. "7817" → "7817.T", "7817.OS", ...)
    base = bare if bare != query else query
    for suffix in _COUNTRY_SUFFIXES.get(preferred_country, []):
        candidate = base + suffix
        if candidate != query:           # avoid re-searching same string
            if _add(candidate):
                return prioritized[:8]

    # 5. Yahoo Finance Japan HTML fallback（国際 API にない JP 株向け）
    #    4 桁の日本株コードで preferred_country が JP なのに候補がない場合のみ実行
    if preferred_country == "JP" and not any(c["country"] == "JP" for c in prioritized):
        jp_base = re.sub(r"\.[A-Za-z]+$", "", bare if bare != query else query)
        if re.match(r"^\d{4}$", jp_base):
            hit = _yahoo_jp_lookup(jp_base)
            if hit:
                prioritized = _merge(prioritized, [hit])

    # 6. 汎用フォールバック — yfinance 直接検索（全国対応）
    #    上記すべてで preferred_country の候補が見つからない場合に試みる
    if not any(c["country"] == preferred_country for c in prioritized):
        base6 = bare if bare != query else query
        already = {c["symbol"] for c in prioritized}
        to_try: list[str] = []
        for suffix in _COUNTRY_SUFFIXES.get(preferred_country, []):
            candidate = base6 + suffix
            if candidate not in already:
                to_try.append(candidate)
        if "." not in base6:
            to_try.append(base6)

        for sym in to_try:
            hit = _yf_direct_lookup(sym)
            if hit:
                country = (_EXCH_TO_COUNTRY.get(hit["exchange"])
                           or _infer_country_from_symbol(sym) or "")
                hit["country"] = country
                hit["score"] = 0 if country == preferred_country else 10
                prioritized = _merge(prioritized, [hit])
                if any(c["country"] == preferred_country for c in prioritized):
                    break

    return prioritized[:8]


@st.cache_data(ttl=300, show_spinner=False)
def _yahoo_jp_lookup(code: str) -> dict | None:
    """finance.yahoo.co.jp の HTML で JP 株を検証し候補 dict を返す。"""
    base   = re.sub(r"\.[A-Za-z]+$", "", code)
    ticker = f"{base}.T"
    try:
        r = requests.get(
            f"https://finance.yahoo.co.jp/quote/{ticker}",
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"},
            timeout=8,
        )
        if r.status_code != 200:
            return None
        # 複数パターンで銘柄名を抽出（サイト側の形式変更に対応）
        name = None
        for pattern in [
            r"<title>(.+?)【",           # 旧形式: "銘柄名【7817.T】..."
            r"<title>(.+?)\s*[-|｜]",   # 新形式: "銘柄名 - Yahoo ファイナンス"
            r"<title>(.+?)[\s（(]",      # 括弧形式
        ]:
            m = re.search(pattern, r.text)
            if m and m.group(1).strip():
                name = m.group(1).strip()
                break
        # 名前が取れなくても 200 が返れば ticker を候補として返す
        if name is None:
            name = ticker
        return {"symbol": ticker, "name": name, "exchange": "JPX", "country": "JP", "score": 0}
    except Exception as e:
        print(f"[symbol_resolver] _yahoo_jp_lookup({ticker}) 失敗: {e}", file=sys.stderr)
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _yahoo_jp_fetch_monthly(ticker: str, start: str, end: str) -> "pd.Series":
    """Yahoo Finance Japan のデイリー履歴をページネーションで取得し月次 Close Series を返す。

    Yahoo Finance 国際 API にない JP 株（例: 7817.T）向けのフォールバック。
    ページあたり 20 営業日、resample('ME').last() で月次変換する。
    """
    import pandas as pd

    start_dt, end_dt = pd.Timestamp(start), pd.Timestamp(end)
    daily: dict = {}

    for page in range(1, 120):  # 安全上限 120 ページ（約 10 年分）
        try:
            r = requests.get(
                f"https://finance.yahoo.co.jp/quote/{ticker}/history",
                params={"timeFrame": "d", "page": page},
                headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"},
                timeout=10,
            )
            if r.status_code != 200:
                break
        except Exception:
            break

        soup   = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            break

        found  = False
        oldest = None
        for tr in tables[0].find_all("tr"):
            th  = tr.find("th")
            tds = tr.find_all("td")
            if not (th and tds):
                continue
            date_str = th.get_text(strip=True)
            if not re.match(r"\d{4}/\d+/\d+", date_str):
                continue
            try:
                dt    = pd.Timestamp(date_str.replace("/", "-"))
                vals  = [td.get_text(strip=True) for td in tds]
                # td[5] = 調整後終値、td[3] = 終値（td[5] が空なら td[3] を使用）
                raw   = vals[5] if len(vals) > 5 and vals[5] else vals[3]
                price = float(raw.replace(",", ""))
                found  = True
                oldest = dt
                if start_dt <= dt <= end_dt:
                    daily[dt] = price
            except (ValueError, IndexError):
                continue

        if not found or (oldest is not None and oldest < start_dt):
            break
        time.sleep(REQUEST_INTERVAL)

    if not daily:
        import pandas as pd
        return pd.Series(dtype=float)

    import pandas as pd
    return pd.Series(daily).sort_index().resample("MS").last()


@st.cache_data(ttl=300, show_spinner=False)
def _yf_direct_lookup(symbol: str) -> dict | None:
    """Directly validate a ticker via yfinance when search API returns nothing."""
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        # fast_info.last_price is None for invalid tickers
        price = getattr(fi, "last_price", None)
        if price is None or price == 0:
            return None
        info = t.get_info() or {}
        name = info.get("shortName") or info.get("longName") or symbol
        exch = info.get("exchange") or ""
        return {"symbol": symbol, "name": name,
                "exchange": exch.upper(), "country": "", "score": 0}
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def resolve_edinet_pick(symbol: str) -> dict | None:
    """銘柄名検索で選んだ銘柄を、証券コード入力時と同じ Yahoo の情報に置き換える。

    出力（グラフ・Excel）の銘柄名を証券コード入力時と揃えるため、
    4 桁コードで通常の検索を行い、同じ symbol の候補を返す。
    """
    code = re.sub(r"\.[A-Za-z]+$", "", symbol)
    for c in search_suggestions(code, "JP"):
        if c["symbol"].upper() == symbol.upper():
            return c
    return None


def best_match(query: str, preferred_country: str) -> dict | None:
    """
    Return best match for a query.
    Falls back to direct yfinance lookup for JP numeric codes
    when the Yahoo Finance search API returns nothing.
    """
    candidates = search_suggestions(query, preferred_country)
    if candidates:
        return candidates[0]

    # --- Fallback: try yfinance directly ---
    # Useful for JP stocks not indexed by Yahoo Finance search (e.g. 7817)
    suffixes_for_country = {
        "JP": [".T", ".OS"],
        "US": [],
        "GB": [".L"],
        "HK": [".HK"],
        "DE": [".DE", ".F"],
        "FR": [".PA"],
        "CN": [".SS", ".SZ"],
        "IN": [".NS", ".BO"],
    }
    # Build list of symbols to try directly
    to_try: list[str] = []
    bare = re.sub(r'\.[A-Za-z]+$', '', query)

    if "." in query:
        to_try.append(query.upper())        # try as-is first
        to_try.append(bare)                 # then bare code
    else:
        for suf in suffixes_for_country.get(preferred_country, []):
            to_try.append(query.upper() + suf)
        to_try.append(query.upper())

    for sym in to_try:
        hit = _yf_direct_lookup(sym)
        if hit:
            # Infer country from symbol or exchange
            country = _EXCH_TO_COUNTRY.get(hit["exchange"]) \
                      or _infer_country_from_symbol(sym) or ""
            hit["country"] = country
            return hit

    return None