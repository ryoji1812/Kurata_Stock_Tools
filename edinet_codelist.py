"""
edinet_codelist.py — 日本語の銘柄名から証券コードを検索する。

データ源: EDINET コードリスト（金融庁, 公共データ利用規約 第1.0版）
  • 1 日 1 回 EDINET から自動取得（st.cache_resource, ttl=86400）
  • 取得に失敗した場合は同梱の data/edinet_jp_listed.csv を使用
    （同梱ファイルの更新: python edinet_codelist.py）

検索は「上場」かつ証券コードを持つ提出者のみが対象。
社名・ヨミ（カナ）の両方を、全角半角・ひらがなカタカナ・「株式会社」の
違いを吸収したうえで 完全一致 > 前方一致 > 部分一致 の順に並べる。
"""

from __future__ import annotations

import csv
import io
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import requests
import streamlit as st

EDINET_CODELIST_URL = (
    "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
)
FALLBACK_PATH = Path(__file__).parent / "data" / "edinet_jp_listed.csv"
_FIELDS = ["code", "name", "name_en", "yomi"]

# ── 文字種の判定・正規化 ──────────────────────────────────────────────────────
_JA_RE = re.compile(r"[぀-ヿ㐀-鿿豈-﫿ｦ-ﾟ々]")
_CORP_RE = re.compile(r"株式会社|\(株\)|カブシキガイシャ|カブシキカイシャ")
_SPACE_RE = re.compile(r"[\s・]+")


def has_japanese(text: str) -> bool:
    """ひらがな・カタカナ・漢字を含むか。"""
    return bool(_JA_RE.search(text or ""))


def _to_katakana(s: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = _to_katakana(s)
    s = _CORP_RE.sub("", s)
    return _SPACE_RE.sub("", s).upper()


def _display_name(name: str) -> str:
    """候補表示用: 全角英数を半角にし「株式会社」を外す。"""
    s = unicodedata.normalize("NFKC", name or "")
    return _CORP_RE.sub("", s).strip() or name


# ── 一覧の取得 ────────────────────────────────────────────────────────────────

def _parse_edinet_csv(text: str) -> list[dict]:
    """EdinetcodeDlInfo.csv（1 行目はメタ情報）から上場銘柄を抽出する。"""
    lines = text.splitlines()
    reader = csv.DictReader(lines[1:])
    out = []
    for r in reader:
        code = (r.get("証券コード") or "").strip()
        if r.get("上場区分") != "上場" or not code:
            continue
        out.append({
            "code":    code[:4],  # 5 桁（末尾 0）→ 4 桁
            "name":    (r.get("提出者名") or "").strip(),
            "name_en": (r.get("提出者名（英字）") or "").strip(),
            "yomi":    (r.get("提出者名（ヨミ）") or "").strip(),
        })
    return out


def _download() -> list[dict]:
    r = requests.get(EDINET_CODELIST_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(csv_name).decode("cp932")
    records = _parse_edinet_csv(text)
    if len(records) < 1000:  # 形式変更などで中身が取れていない
        raise ValueError(f"EDINET コードリストの件数が少なすぎます: {len(records)}")
    return records


def _read_fallback() -> list[dict]:
    if not FALLBACK_PATH.exists():
        return []
    with open(FALLBACK_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@st.cache_resource(ttl=86400, show_spinner=False)  # 読み取り専用。コピーを避ける
def load_codelist() -> list[dict]:
    try:
        records = _download()
    except Exception as e:
        print(f"[edinet_codelist] 自動取得に失敗、同梱ファイルを使用: {e}", file=sys.stderr)
        records = _read_fallback()
    for r in records:
        r["_n"] = _normalize(r["name"])
        r["_y"] = _normalize(r["yomi"])
    return records


# ── 検索 ──────────────────────────────────────────────────────────────────────

def _match_rank(q: str, target: str) -> int | None:
    if not target:
        return None
    if target == q:
        return 0
    if target.startswith(q):
        return 1
    if q in target:
        return 2
    return None


def search_jp_names(query: str, limit: int = 8) -> list[dict]:
    """日本語の銘柄名で検索し、symbol_resolver と同じ形の候補 dict を返す。"""
    q = _normalize(query)
    if not q:
        return []
    hits = []
    for r in load_codelist():
        # 同じ一致度なら社名での一致をヨミでの一致より優先（例: トヨタ → 豊田通商は後ろ）
        rn, ry = _match_rank(q, r["_n"]), _match_rank(q, r["_y"])
        ranks = []
        if rn is not None:
            ranks.append(rn * 2)
        if ry is not None:
            ranks.append(ry * 2 + 1)
        if ranks:
            hits.append((min(ranks), len(r["_n"]), r["code"], r))
    hits.sort(key=lambda h: h[:3])
    return [
        {
            "symbol":   f"{r['code']}.T",
            "name":     _display_name(r["name"]),
            "name_ja":  _display_name(r["name"]),
            "exchange": "JPX",
            "country":  "JP",
            "score":    0,
            "src":      "edinet",
        }
        for *_, r in hits[:limit]
    ]


# ── 証券コード → 日本語名（表示用）──────────────────────────────────────────

@st.cache_resource(ttl=86400, show_spinner=False)
def _by_code() -> dict[str, dict]:
    return {r["code"]: r for r in load_codelist()}


_JP_SYMBOL_RE = re.compile(r"^([0-9A-Z]{4})\.(T|OS|FK)$")


def jp_name_for(symbol: str) -> str:
    """日本株の symbol（例: 7203.T）に対応する日本語の社名。該当なしは空文字。"""
    m = _JP_SYMBOL_RE.match((symbol or "").upper())
    r = _by_code().get(m.group(1)) if m else None
    return _display_name(r["name"]) if r else ""


# ── 同梱ファイルの更新 ────────────────────────────────────────────────────────

def update_fallback() -> int:
    records = _download()
    FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FALLBACK_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        w.writerows({k: r[k] for k in _FIELDS} for r in records)
    return len(records)


if __name__ == "__main__":
    print(f"{FALLBACK_PATH} を更新しました: {update_fallback()} 件")
