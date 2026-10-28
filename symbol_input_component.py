"""
symbol_input_component.py
─────────────────────────
declare_component based symbol input table.

Behaviors
  Return key
    · suggestions already shown → confirm top immediately in JS (no roundtrip)
    · no suggestions yet        → search_now → Python returns → JS auto-confirms top

  Single newline paste  ("9433\n" or "9433↵")
    → confirm current row → add one empty row → focus new row

  Multi-token paste  ("9433\n4733\n…"  or  "9433,4733,…")
    → JS expands rows immediately (visual instant)
    → bulk_paste sent to Python
    → results return → each row confirmed / marked not-found

  Normal typing
    → 200 ms debounced search → suggestions dropdown

Python ↔ JS protocol
  JS → Python  (setComponentValue)
    {action:"search",      query, row_id, seq}
    {action:"search_now",  query, row_id, seq}   ← Return without suggestions
    {action:"bulk_paste",  tickers, row_ids, seq}
    {action:"rows_update", rows}                 ← confirm / delete / reorder

  Python → JS  (props)
    search_results:
      {single:true,  row_id, results, seq, auto_confirm:bool}
      {bulk:true,    results:[{row_id, symbol, name, exchange, country}], seq}
"""

from __future__ import annotations
import os, tempfile
import streamlit as st
import streamlit.components.v1 as _cv1
from symbol_resolver import search_suggestions, best_match, resolve_edinet_pick
from edinet_codelist import has_japanese, jp_name_for

# ── Component singleton ───────────────────────────────────────────────────────
_COMP = None
_TMPD = None

def _get_component():
    global _COMP, _TMPD
    if _COMP is None:
        _TMPD = tempfile.mkdtemp(prefix="mspa_sym_")
        with open(os.path.join(_TMPD, "index.html"), "w", encoding="utf-8") as f:
            f.write(_HTML)
        _COMP = _cv1.declare_component("mspa_sym_v4", path=_TMPD)
    return _COMP


def render_symbol_table(rows, lang, country, labels, search_results=None, key="sym"):
    return _get_component()(
        rows=rows, lang=lang, country=country,
        labels=labels, search_results=search_results, key=key,
    )


# ── Japanese company-name helpers ─────────────────────────────────────────────
def _name_pick_item(name: str, rid) -> dict:
    """Bulk-paste result for a Japanese name: never auto-confirmed, user picks."""
    found = bool(search_suggestions(name, "JP"))
    return {"row_id": rid, "symbol": None, "name": "", "exchange": "",
            "country": "", "duplicate": False, "pick": found}


def _resolve_name_picks(rows: list) -> list:
    """Rows confirmed via name search get the same Yahoo name/exchange as code input."""
    for r in rows:
        if r.get("confirmed") and r.get("src") == "edinet":
            hit = resolve_edinet_pick(r.get("symbol", ""))
            if hit:
                r.update(name=hit.get("name", ""), exchange=hit.get("exchange", ""),
                         country=hit.get("country", ""))
    return rows


# ── Python-side handler ───────────────────────────────────────────────────────
def handle(cv: dict | None, prefix: str = "") -> str:
    """
    Returns:
      "new_results"  – fresh search results stored; caller should st.rerun()
      "rows_update"  – rows changed; no rerun needed (session_state already updated)
      "none"         – nothing to do

    prefix: session-state key namespace (e.g. "comp_" for comparison funds).
            Default "" keeps backward compatibility with the portfolio input.
    """
    if not cv:
        return "none"

    _k_rows    = f"{prefix}ticker_rows"
    _k_seq     = f"{prefix}_sym_last_seq"
    _k_sr      = f"{prefix}_sym_search_results"
    _k_dup     = f"{prefix}_dup_notice"

    action = cv.get("action", "")
    seq    = int(cv.get("seq", -1))
    last   = st.session_state.get(_k_seq, -9999)

    # ── Single search (debounced or Return) ───────────────────────────────
    if action in ("search", "search_now"):
        if seq == last:
            return "none"                          # already processed
        query = cv.get("query", "").strip()
        rid   = cv.get("row_id")
        if not query:
            return "none"
        st.session_state[_k_seq] = seq
        results = search_suggestions(query, st.session_state.get("user_country","JP"))
        st.session_state[_k_sr] = {
            "single":       True,
            "row_id":       rid,
            "results":      results,
            "seq":          seq,
            # Return → auto-confirm top (code input only; names always need a pick)
            "auto_confirm": action == "search_now" and not has_japanese(query),
        }
        return "new_results"

    # ── Bulk paste ────────────────────────────────────────────────────────
    if action == "bulk_paste":
        if seq == last:
            return "none"
        tickers = cv.get("tickers", [])
        row_ids = cv.get("row_ids", [])
        st.session_state[_k_seq] = seq
        country = st.session_state.get("user_country", "JP")

        # Dedup against already confirmed rows
        confirmed_syms = {
            r["symbol"].upper()
            for r in st.session_state.get(_k_rows, [])
            if r.get("confirmed")
        }
        bulk, dupes = [], []
        seen = set()
        for ticker, rid in zip(tickers, row_ids):
            if has_japanese(ticker):
                bulk.append(_name_pick_item(ticker, rid))
                continue
            t = ticker.upper()
            if t in confirmed_syms or t in seen:
                dupes.append(ticker)
                bulk.append({"row_id": rid, "symbol": None,
                             "name":"","exchange":"","country":"","duplicate":True})
                continue
            hit = best_match(ticker, country)
            sym = hit["symbol"].upper() if hit else None
            if sym and (sym in confirmed_syms or sym in seen):
                dupes.append(ticker)
                bulk.append({"row_id": rid, "symbol": None,
                             "name":"","exchange":"","country":"","duplicate":True})
                continue
            bulk.append({
                "row_id":   rid,
                "symbol":   hit["symbol"]           if hit else None,
                "name":     hit.get("name","")      if hit else "",
                "exchange": hit.get("exchange","")  if hit else "",
                "country":  hit.get("country","")   if hit else "",
                "name_ja":  jp_name_for(hit["symbol"]) if hit else "",
                "duplicate": False,
            })
            if sym:
                seen.add(sym)

        st.session_state[_k_sr] = {
            "bulk": True, "results": bulk, "seq": seq,
        }
        if dupes:
            st.session_state[_k_dup] = dupes
        return "new_results"

    # ── Rows updated by JS ────────────────────────────────────────────────
    if action == "rows_update":
        st.session_state[_k_rows] = _resolve_name_picks(cv.get("rows", []))
        st.session_state[_k_sr]   = None
        return "rows_update"

    return "none"


def handle_fund(cv: dict | None, fund: dict) -> str:
    """
    Process component value for a multi-fund entry.
    fund: mutable dict with keys 'ticker_rows', '_sym_last_seq', '_sym_search_results'.
    Modifies fund in-place.

    Returns same strings as handle(): "new_results" | "rows_update" | "none"
    """
    if not cv:
        return "none"

    action = cv.get("action", "")
    seq    = int(cv.get("seq", -1))
    last   = fund.get("_sym_last_seq", -9999)

    if action in ("search", "search_now"):
        if seq == last:
            return "none"
        query = cv.get("query", "").strip()
        rid   = cv.get("row_id")
        if not query:
            return "none"
        fund["_sym_last_seq"] = seq
        results = search_suggestions(query, st.session_state.get("user_country", "JP"))
        fund["_sym_search_results"] = {
            "single":       True,
            "row_id":       rid,
            "results":      results,
            "seq":          seq,
            "auto_confirm": action == "search_now" and not has_japanese(query),
        }
        return "new_results"

    if action == "bulk_paste":
        if seq == last:
            return "none"
        tickers = cv.get("tickers", [])
        row_ids = cv.get("row_ids", [])
        fund["_sym_last_seq"] = seq
        country = st.session_state.get("user_country", "JP")

        confirmed_syms = {
            r["symbol"].upper()
            for r in fund.get("ticker_rows", [])
            if r.get("confirmed")
        }
        bulk, dupes = [], []
        seen = set()
        for ticker, rid in zip(tickers, row_ids):
            if has_japanese(ticker):
                bulk.append(_name_pick_item(ticker, rid))
                continue
            t = ticker.upper()
            if t in confirmed_syms or t in seen:
                dupes.append(ticker)
                bulk.append({"row_id": rid, "symbol": None,
                             "name": "", "exchange": "", "country": "", "duplicate": True})
                continue
            hit = best_match(ticker, country)
            sym = hit["symbol"].upper() if hit else None
            if sym and (sym in confirmed_syms or sym in seen):
                dupes.append(ticker)
                bulk.append({"row_id": rid, "symbol": None,
                             "name": "", "exchange": "", "country": "", "duplicate": True})
                continue
            bulk.append({
                "row_id":   rid,
                "symbol":   hit["symbol"]           if hit else None,
                "name":     hit.get("name", "")     if hit else "",
                "exchange": hit.get("exchange", "")  if hit else "",
                "country":  hit.get("country", "")   if hit else "",
                "name_ja":  jp_name_for(hit["symbol"]) if hit else "",
                "duplicate": False,
            })
            if sym:
                seen.add(sym)

        fund["_sym_search_results"] = {
            "bulk": True, "results": bulk, "seq": seq,
        }
        fund["_dup_notice"] = dupes if dupes else []
        return "new_results"

    if action == "rows_update":
        fund["ticker_rows"] = _resolve_name_picks(cv.get("rows", []))
        fund["_sym_search_results"] = None
        return "rows_update"

    return "none"


# ─────────────────────────────────────────────────────────────────────────────
# Component HTML / CSS / JS
# ─────────────────────────────────────────────────────────────────────────────
_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  font-size:13px;color:var(--fg);background:transparent;
  padding:0 2px 4px;

  --bg:   #ffffff; --bg2:  #f0f2f6;
  --fg:   #31333f; --fg2:  #6b6b6b;
  --bdr:  rgba(49,51,63,.16);
  --bdr2: rgba(49,51,63,.08);
  --pri:  #0077c7; --pri2: #005fa3;
  --ok:   #1e8a44; --err:  #c0392b;
  --chip-bg: #f2f4f8;
  --sug-h:   #e8f4ff;
}

/* ── Theme: read Streamlit parent CSS vars ─── */
/* Applied by JS applyTheme() on each render   */

/* ── Table ───────────────────────────────────────── */
.tbl{width:100%;border:1px solid var(--bdr);border-radius:8px;
     background:var(--bg);overflow:visible}
.thead{display:grid;grid-template-columns:var(--cols);
       background:var(--bg2);border-bottom:2px solid var(--bdr);
       border-radius:8px 8px 0 0;padding:0 2px}
.th{padding:7px 8px 5px;font-size:10.5px;font-weight:700;color:var(--fg2);
    text-transform:uppercase;letter-spacing:.07em;white-space:nowrap;overflow:hidden}

/* ── Row ────────────────────────────────────────── */
.trow{display:grid;grid-template-columns:var(--cols);
      border-bottom:1px solid var(--bdr2);position:relative}
.trow:last-child{border-bottom:none}
.trow:hover{background:color-mix(in srgb,var(--bg2) 50%,var(--bg))}
.td{padding:5px 8px;display:flex;align-items:center;
    min-height:48px;overflow:visible}
.td-text{font-size:13px;color:var(--fg);
         overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.td-meta{font-size:12px;color:var(--fg2);
         overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── Symbol chip ────────────────────────────────── */
.chip{display:inline-flex;align-items:center;justify-content:center;
      border:1.5px solid var(--bdr);border-radius:5px;padding:4px 10px;
      font-family:'SF Mono','Fira Code','Courier New',monospace;
      font-size:14px;font-weight:700;background:var(--chip-bg);color:var(--fg);
      cursor:pointer;user-select:none;white-space:nowrap;min-width:64px;
      transition:border-color .13s,color .13s}
.chip:hover{border-color:var(--pri);color:var(--pri2)}
.chip::after{content:'✎';font-size:9px;margin-left:6px;opacity:0;transition:opacity .13s}
.chip:hover::after{opacity:.5}

/* ── Input ──────────────────────────────────────── */
.inp-wrap{position:relative;width:100%}
.sym-inp{
  width:100%;padding:6px 10px;
  border:2px solid var(--pri);border-radius:5px;
  font-family:'SF Mono','Fira Code','Courier New',monospace;
  font-size:14px;font-weight:700;outline:none;
  background:var(--bg);color:var(--fg);
  transition:box-shadow .12s}
.sym-inp::placeholder{font-family:inherit;font-weight:400;color:var(--fg2);font-size:13px}
.sym-inp:focus{box-shadow:0 0 0 3px color-mix(in srgb,var(--pri) 20%,transparent)}
.sym-inp.locked{opacity:.45;pointer-events:none}

/* ── Searching indicator ────────────────────────── */
.srch-ind{font-size:11px;color:var(--fg2);margin-top:3px;
          display:flex;align-items:center;gap:4px}
.spin{display:inline-block;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Suggestion list ────────────────────────────── */
.sug-list{
  position:absolute;top:calc(100% + 3px);left:0;z-index:9999;
  /* wider than the code column so company names are readable */
  min-width:100%;width:max-content;max-width:min(360px,calc(100vw - 24px));
  background:var(--bg);border:1px solid var(--bdr);border-radius:0 0 7px 7px;
  box-shadow:0 6px 20px rgba(0,0,0,.13);overflow:hidden;
  max-height:240px;overflow-y:auto;list-style:none}
.sug-item{padding:7px 10px 4px;cursor:pointer;border-bottom:1px solid var(--bdr2);
          transition:background .1s}
.sug-item:last-child{border-bottom:none}
.sug-item:hover,.sug-item.hi{background:var(--sug-h)}
.sug-code{font-family:'SF Mono','Fira Code',monospace;font-weight:700;
          font-size:14px;color:var(--pri)}
.sug-name{font-size:10.5px;color:var(--fg2);margin-top:1px;
          overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sug-list::-webkit-scrollbar{width:4px}
.sug-list::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:2px}

/* ── Badges ─────────────────────────────────────── */
.b-ok {color:var(--ok);font-size:12.5px;font-weight:600}
.b-err{color:var(--err);font-size:11.5px}
.b-dup{color:#b77f00;font-size:11.5px}

/* ── Buttons ────────────────────────────────────── */
.btn-del,.btn-cancel{
  background:none;border:none;cursor:pointer;font-size:13px;
  padding:3px 5px;border-radius:4px;line-height:1;
  color:var(--fg2);transition:color .1s,background .1s}
.btn-del:hover{color:var(--err);background:color-mix(in srgb,var(--err) 10%,transparent)}
.btn-cancel{font-size:12px}
.btn-cancel:hover{color:var(--pri)}

/* ── Add button ─────────────────────────────────── */
.add-btn{
  width:100%;padding:8px 0;
  border:1.5px dashed var(--bdr);border-top:none;
  border-radius:0 0 8px 8px;background:none;cursor:pointer;
  color:var(--fg2);font-size:22px;font-weight:300;line-height:1;
  display:flex;align-items:center;justify-content:center;
  transition:all .13s;margin-top:-1px}
.add-btn:hover{border-color:var(--pri);color:var(--pri);
               background:color-mix(in srgb,var(--pri) 7%,transparent)}
</style>
</head>
<body>
<div id="root"></div>
<script>
/* ── Streamlit bridge ────────────────────────────── */
const post = d => window.parent.postMessage(Object.assign({isStreamlitMessage:true},d),'*');
const ST = {
  ready: ()  => post({type:'streamlit:componentReady',apiVersion:1}),
  h:     h   => post({type:'streamlit:setFrameHeight',height:h}),
  val:   v   => post({type:'streamlit:setComponentValue',value:v}),
};
window.addEventListener('message', ev => {
  if(ev.data && ev.data.type==='streamlit:render')
    onRender(ev.data.args||{}, ev.data.theme||null);
});

/* ── Theme ─────────────────────────────────────────
   Streamlit passes theme as a.theme in onRender args.
   Keys: base("light"|"dark"), backgroundColor,
         secondaryBackgroundColor, textColor, primaryColor
   ─────────────────────────────────────────────────── */
let _theme = null;

/* Streamlit exact palettes */
const _SL={bg:'#ffffff',bg2:'#f0f2f6',fg:'#31333f',fg2:'#555867',pri:'#ff4b4b'};
const _SD={bg:'#0e1117',bg2:'#262730',fg:'#fafafa', fg2:'#a3a8b8',pri:'#ff4b4b'};

function _luma(c){
  const m=c.match(/\d+/g);
  if(m&&m.length>=3)return(+m[0]*299+(+m[1])*587+(+m[2])*114)/1000;
  return 200;
}
function _isDark(){
  if(_theme&&_theme.base) return _theme.base==='dark';
  try{
    const el=window.parent.document.documentElement;
    let v=el.style.getPropertyValue('--background-color').trim();
    if(!v)v=window.parent.getComputedStyle(el).getPropertyValue('--background-color').trim();
    if(v)return _luma(v)<128;
  }catch(e){}
  try{
    const bg=window.parent.getComputedStyle(window.parent.document.body).backgroundColor;
    if(bg&&bg!=='rgba(0, 0, 0, 0)'&&bg!=='transparent')return _luma(bg)<128;
  }catch(e){}
  return false;
}
function applyTheme(){
  const dark=_isDark();
  const p=dark?_SD:_SL;
  const bg  =(_theme&&_theme.backgroundColor)         ||p.bg;
  const bg2 =(_theme&&_theme.secondaryBackgroundColor)||p.bg2;
  const fg  =(_theme&&_theme.textColor)               ||p.fg;
  const pri =(_theme&&_theme.primaryColor)            ||p.pri;
  const s=document.body.style;
  s.setProperty('--bg',      bg);
  s.setProperty('--bg2',     bg2);
  s.setProperty('--fg',      fg);
  s.setProperty('--fg2',     dark?'#a3a8b8':'#555867');
  s.setProperty('--bdr',     dark?'rgba(250,250,250,.18)':'rgba(49,51,63,.16)');
  s.setProperty('--bdr2',    dark?'rgba(250,250,250,.09)':'rgba(49,51,63,.08)');
  s.setProperty('--pri',     pri);
  s.setProperty('--pri2',    dark?'#ff6b6b':'#cc3a3a');
  s.setProperty('--ok',      dark?'#4caf80':'#1e8a44');
  s.setProperty('--err',     dark?'#ef5b5b':'#c0392b');
  s.setProperty('--chip-bg', dark?'#1a1c24':'#f2f4f8');
  s.setProperty('--sug-h',   dark?'rgba(255,75,75,.14)':'rgba(255,75,75,.07)');
}
/* Watch parent for runtime theme switch */
try{
  new window.parent.MutationObserver(()=>applyTheme())
    .observe(window.parent.document.documentElement,
             {attributes:true,attributeFilter:['style','data-theme','class']});
}catch(e){}
/* ── State ────────────────────────────────────────── */
let rows=[], labels={}, seq=0, lastSrSeq=-1, initialized=false, _rid=0;
const _sugData={}; /* rowId -> sug array; avoids JSON-in-HTML attribute issues */
let _sugHovered=false;
let _deferredRender=false;
let _sugVisible=false; /* true AFTER suggestions are rendered in DOM (not just set in JS) */

function safeRender(){
  /* Defer only when suggestions are ALREADY VISIBLE in DOM.
     _sugVisible is set to true INSIDE render() after drawing suggestions.
     So the very first render that shows suggestions is NOT deferred —
     only subsequent Streamlit reruns while suggestions are displayed. */
  if(_sugVisible||_sugHovered){ _deferredRender=true; return; }
  /* rebuilding the <input> mid-IME-conversion would drop the conversion */
  if(rows.some(r=>r.composing)){ _deferredRender=true; return; }
  _deferredRender=false;
  render();
}
const T = k => labels[k]||k;
const COLS = 'minmax(80px,120px) 1fr minmax(68px,100px) 46px 76px 72px';

/* ── Row factory ──────────────────────────────────── */
function nr(inp=''){return{id:_rid++,inp,confirmed:false,
  symbol:'',name:'',exchange:'',country:'',
  notFound:false,duplicate:false,searching:false,prev:null,sug:[],hi:-1,
  name_ja:'',src:'',pick:false,composing:false};}
/* display name: Japanese company name for JP stocks, else the Yahoo name.
   (row.name stays the Yahoo name — it is what charts / Excel use) */
const dispName=r=>r.name_ja||r.name||'';

/* ── Tokeniser ────────────────────────────────────── */
/* Japanese = hiragana / katakana / kanji (same ranges as edinet_codelist.has_japanese) */
const JA=/[぀-ヿ㐀-鿿豈-﫿ｦ-ﾟ々]/;
function _tokCodes(s){
  return s.split(/\s+/)
    .map(t=>t.replace(/^[^A-Za-z0-9\^]/,'')
             .replace(/[^A-Za-z0-9.\-\^]$/,'').toUpperCase())
    .filter(t=>t&&/^[A-Z0-9\^][A-Z0-9.\-\^]*$/.test(t));
}
function tok(raw){
  let s=raw.replace(/["'“”‘’「」]/g,' ');
  s=s.replace(/\r\n/g,'\n').replace(/\r/g,'\n');
  /* Company names may contain spaces -> split names only on line/list separators */
  return s.split(/[\n,、。;|\t]+/)
    .flatMap(p=>JA.test(p) ? [p.trim()] : _tokCodes(p))
    .filter(Boolean);
}

/* ── Debounce ──────────────────────────────────────── */
const tmr={};
function deb(k,fn,ms){clearTimeout(tmr[k]);tmr[k]=setTimeout(fn,ms);}

/* ── Confirm ───────────────────────────────────────── */
function _showSpinner(row){
  const el=document.getElementById('ind_'+row.id);
  if(el) el.style.display='flex';
}
function _clearSugFor(row){
  const w=document.getElementById('sugwrap_'+row.id);
  if(w) w.innerHTML='';
  const el=document.getElementById('ind_'+row.id);
  if(el) el.style.display='none';
  row.sug=[];
  _sugVisible=rows.some(r=>(r.sug||[]).length>0);
  if(!_sugVisible&&_deferredRender){_deferredRender=false;render();}
  else fitHeight();
}
/* Size the iframe to what is actually drawn: the table plus any open dropdown
   (dropdowns are absolutely positioned, so they hang below the table) */
let _lastH=-1;
function fitHeight(){
  let h=document.getElementById('root').getBoundingClientRect().bottom;
  document.querySelectorAll('.sug-list').forEach(el=>{
    h=Math.max(h,el.getBoundingClientRect().bottom);
  });
  h=Math.ceil(h)+8;
  /* every setFrameHeight makes Streamlit re-send props (→ render()),
     so only post real changes */
  if(h!==_lastH){ _lastH=h; ST.h(h); }
}
function _buildSugHtml(row){
  const sg=row.sug||[],hi=row.hi;
  if(!sg.length) return '';
  _sugData[row.id]=sg;
  let h=`<ul class="sug-list"
    onmouseenter="_sugHovered=true"
    onmouseleave="_sugHovered=false;if(_deferredRender&&!_sugVisible)render()">`;
  sg.forEach((s,si)=>{
    const nm=dispName(s)||(s.exchange||s.country||'');
    const disp=nm.length>28?nm.slice(0,26)+'…':nm;
    h+=`<li class="sug-item${si===hi?' hi':''}"
      onmousedown="pickSug(${row.id},${si})">
      <div class="sug-code">${esc(s.symbol)}</div>
      <div class="sug-name">${esc(disp)}</div>
    </li>`;
  });
  return h+'</ul>';
}
function _renderSuggestionsFor(row){
  /* Surgically update only the suggestion dropdown — no full DOM rebuild */
  const wrap=document.getElementById('sugwrap_'+row.id);
  const ind =document.getElementById('ind_'+row.id);
  if(!wrap){ render(); return; } /* fallback: wrapper not in DOM yet */
  wrap.innerHTML=_buildSugHtml(row);
  if(ind) ind.style.display='none';
  _sugVisible=(row.sug||[]).length>0;
  fitHeight();
}
function pickSug(rowId,si){
  const row=rows.find(r=>r.id===rowId);
  const s=(_sugData[rowId]||[])[si];
  if(row&&s) confirmRow(row,s);
}
function confirmRow(row,s){
  Object.assign(row,{confirmed:true,symbol:s.symbol,name:s.name||'',name_ja:s.name_ja||'',
    exchange:s.exchange||'',country:s.country||'',
    inp:s.symbol,notFound:false,duplicate:false,searching:false,
    sug:[],hi:-1,prev:null,src:s.src||'',pick:false});
  /* pasted company names waiting for a pick → move on to the next one */
  const nextPick=rows.find(r=>r.pick&&!r.confirmed);
  if(nextPick){
    render();notifyRows();
    setTimeout(()=>{const el=document.getElementById('i'+nextPick.id);if(el)el.focus();},30);
    return;
  }
  /* auto-add new empty row when confirming the last row */
  const isLast=rows[rows.length-1].id===row.id;
  if(isLast){
    const next=nr();rows.push(next);render();notifyRows();
    setTimeout(()=>{const el=document.getElementById('i'+next.id);if(el)el.focus();},30);
  }else{render();notifyRows();}
}
function notifyRows(){
  ST.val({action:'rows_update', rows:rows.map(r=>({
    id:r.id,
    /* a pasted name still waiting for a pick keeps its text, so the
       run button treats it as unconfirmed instead of silently skipping it */
    symbol:(!r.confirmed&&r.pick)?r.inp:r.symbol,
    name:r.name,name_ja:r.name_ja||'',exchange:r.exchange,
    country:r.country,confirmed:r.confirmed,
    notFound:r.notFound,duplicate:r.duplicate,src:r.src||'',
  }))});
}

/* ── Return key: confirm highlighted or fire search ─ */
function onReturn(row){
  if(row.sug.length>0){
    confirmRow(row, row.sug[row.hi>=0?row.hi:0]); return;
  }
  const q=row.inp.trim().toUpperCase();
  if(!q) return;
  clearTimeout(tmr['s'+row.id]);
  row.searching=true; render();
  seq++;
  /* code → search & auto-confirm top; company name → only show candidates */
  ST.val({action:JA.test(q)?'search':'search_now', query:q, row_id:row.id, seq});
}

/* ── Paste event ────────────────────────────────────── */
function onPaste(row, e){
  const raw = e.clipboardData.getData('text');
  if(!raw) return;

  const lines = raw.replace(/\r\n/g,'\n').replace(/\r/g,'\n').split('\n')
                   .map(l=>l.trim()).filter(Boolean);
  const tks   = tok(raw);

  /* Single token (possibly one line) → normal input, no special handling */
  if(tks.length<=1) return;   // let default paste + debounced search handle it

  e.preventDefault();         // block default paste

  const idx = rows.findIndex(r=>r.id===row.id);
  if(idx===-1) return;

  /* Create rows immediately for visual instant feedback */
  const newRows = tks.map(t=>Object.assign(nr(t),{searching:true}));
  rows.splice(idx,1,...newRows);
  render();

  /* Request bulk confirmation from Python */
  seq++;
  ST.val({action:'bulk_paste',
          tickers: tks,
          row_ids: newRows.map(r=>r.id),
          seq});
}

/* ── Input handler ──────────────────────────────────── */
function onInp(row, val){
  row.inp=val; row.notFound=false; row.duplicate=false;
  /* IME conversion in progress → wait for compositionend (a rerun mid-
     conversion would wipe the text being converted) */
  if(row.composing) return;
  if(!val.trim()){row.sug=[];row.searching=false;_clearSugFor(row);return;}
  row.searching=true;
  _showSpinner(row); /* surgical: only spinner, no full re-render */
  deb('s'+row.id, ()=>{
    seq++;
    ST.val({action:'search', query:val.trim().toUpperCase(), row_id:row.id, seq});
  }, 300);
}

/* ── IME composition ────────────────────────────────── */
/* Composition events have no on* HTML attribute → delegate from document
   (inputs are recreated by every render()) */
const _rowOf=el=>(el&&el.classList&&el.classList.contains('sym-inp'))
  ? rows.find(r=>'i'+r.id===el.id) : null;
document.addEventListener('compositionstart',e=>{
  const row=_rowOf(e.target); if(row) row.composing=true;
});
document.addEventListener('compositionend',e=>{
  const row=_rowOf(e.target); if(!row) return;
  row.composing=false;
  const val=e.target.value;
  if(_deferredRender&&!_sugVisible){ _deferredRender=false; render(); }
  onInp(row, val);
});

/* ── Focus: pasted name waiting for a pick → show its candidates ─ */
function onFoc(row){
  if(!row||!row.pick||row.confirmed||row.sug.length||!row.inp.trim()) return;
  row.searching=true; _showSpinner(row);
  seq++;
  ST.val({action:'search', query:row.inp.trim().toUpperCase(), row_id:row.id, seq});
}

/* ── Keyboard ────────────────────────────────────────── */
function onKd(e,row){
  /* Enter that commits an IME conversion is not a "confirm" */
  if(e.isComposing||e.keyCode===229) return;
  if(e.key==='Enter'){e.preventDefault();onReturn(row);return;}
  if(e.key==='Escape'){row.sug=[];render();return;}
  if(e.key==='ArrowDown'){e.preventDefault();
    row.hi=Math.min(row.hi+1,(row.sug.length||1)-1);_renderSuggestionsFor(row);return;}
  if(e.key==='ArrowUp'){e.preventDefault();
    row.hi=Math.max(row.hi-1,0);_renderSuggestionsFor(row);return;}
}

/* ── Row ops ─────────────────────────────────────────── */
function delRow(id){
  const i=rows.findIndex(r=>r.id===id);
  if(i!==-1)rows.splice(i,1);
  if(!rows.length)rows.push(nr());
  render(); notifyRows();
}
function addRow(){
  const r=nr(); rows.push(r); render();
  setTimeout(()=>{const el=document.getElementById('i'+r.id);if(el)el.focus();},0);
}
function enterEdit(row){
  row.prev={symbol:row.symbol,name:row.name,name_ja:row.name_ja,exchange:row.exchange,country:row.country};
  row.confirmed=false; row.inp=row.symbol; row.sug=[];
  render();
  setTimeout(()=>{const el=document.getElementById('i'+row.id);
    if(el){el.focus();el.select();}},0);
}
function cancelEdit(row){
  if(row.prev){Object.assign(row,row.prev,{confirmed:true,searching:false,
    notFound:false,sug:[],hi:-1,prev:null});}
  else{row.confirmed=false;}
  render(); notifyRows();
}

/* ── Escape / HTML ───────────────────────────────────── */
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                           .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const ea =s=>String(s||'').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

/* ── Render ──────────────────────────────────────────── */
function render(){
  applyTheme();

  /* save focus before innerHTML wipe */
  const ae  = document.activeElement;
  const fid = (ae && ae.id) ? ae.id : null;
  const fv  = fid ? (ae.value || '') : '';
  const fss = fid ? (ae.selectionStart || fv.length) : 0;
  const fse = fid ? (ae.selectionEnd   || fv.length) : 0;

  const hasSug=rows.some(r=>r.sug&&r.sug.length>0);
  let h=`<div class="tbl" style="--cols:${COLS}">
  <div class="thead">
    ${['col_symbol','col_name','col_exchange','col_country','col_status','']
      .map(k=>`<div class="th">${esc(k?T(k):'')}</div>`).join('')}
  </div>`;

  rows.forEach((row,i)=>{
    h+=`<div class="trow">`;
    if(row.confirmed){
      /* ── confirmed row ── */
      const chip=`<span class="chip" onclick="enterEdit(rows[${i}])"
        title="${ea(T('hint_dblclick'))}">${esc(row.symbol)}</span>`;
      h+=`
      <div class="td">${chip}</div>
      <div class="td"><span class="td-text">${esc(dispName(row))}</span></div>
      <div class="td"><span class="td-meta">${esc(row.exchange)}</span></div>
      <div class="td"><span class="td-meta">${esc(row.country)}</span></div>
      <div class="td"><span class="b-ok">✓ ${esc(T('status_confirmed_short'))}</span></div>
      <div class="td" style="gap:4px">
        <button class="btn-del" onclick="delRow(${row.id})">✕</button>
      </div>`;
    } else {
      /* ── edit row ── */
      const sg=row.sug||[], hi=row.hi;
      let sugHtml='';
      /* sugHtml is no longer built here — handled by _renderSuggestionsFor() */

      const zi=300-i;

      let badge='';
      if(row.notFound)  badge=`<div class="b-err">${esc(T('status_not_found'))}</div>`;
      if(row.duplicate) badge=`<div class="b-dup">⚠ ${esc(T('status_duplicate')||'重複')}</div>`;
      if(row.pick)      badge=`<div class="b-dup">${esc(T('status_pick'))}</div>`;

      h+=`
      <div class="td" style="position:relative;overflow:visible;z-index:${zi}">
        <div style="width:100%">
          <div class="inp-wrap">
            <input id="i${row.id}" class="sym-inp"
              type="text" value="${ea(row.inp)}"
              placeholder="${ea(T('placeholder_symbol'))}"
              oninput="onInp(rows.find(r=>r.id===${row.id}),this.value)"
              onkeydown="onKd(event,rows.find(r=>r.id===${row.id}))"
              onfocus="onFoc(rows.find(r=>r.id===${row.id}))"
              onblur="(()=>{const r=rows.find(x=>x.id===${row.id});if(r){setTimeout(()=>{const a=document.activeElement;if(a&&a.id==='i'+r.id)return;r.sug=[];_sugHovered=false;_sugVisible=false;_deferredRender=false;_clearSugFor(r);},150);}})()"
              onpaste="onPaste(rows.find(r=>r.id===${row.id}),event)"
              autocomplete="off" spellcheck="false">
            <div id="sugwrap_${row.id}"></div>
          </div>
          <div id="ind_${row.id}" class="srch-ind" style="display:${row.searching?'flex':'none'}"><span class="spin">⟳</span>${esc(T('status_searching')||'検索中…')}</div>
          ${badge}
        </div>
      </div>
      <div class="td"></div>
      <div class="td"></div>
      <div class="td"></div>
      <div class="td" style="gap:4px">
        ${row.prev?`<button class="btn-cancel" onclick="cancelEdit(rows.find(r=>r.id===${row.id}))" title="${ea(T('hint_cancel_edit'))}">↩</button>`:''}
        <button class="btn-del" onclick="delRow(${row.id})">✕</button>
      </div>`;
    }
    h+=`</div>`;
  });

  h+=`</div>
  <button class="add-btn" onclick="addRow()" title="${ea(T('btn_add_symbol'))}">＋</button>`;
  document.getElementById('root').innerHTML=h;
  /* keep the open dropdown of the focused input (a rebuild must not hide it) */
  const fr=fid&&rows.find(r=>'i'+r.id===fid&&!r.confirmed&&(r.sug||[]).length);
  if(fr){ const w=document.getElementById('sugwrap_'+fr.id); if(w) w.innerHTML=_buildSugHtml(fr); }
  fitHeight();
  /* track whether suggestions are now visible in DOM */
  _sugVisible=hasSug;

  /* restore focus + cursor position */
  if(fid){
    const el=document.getElementById(fid);
    if(el){
      el.focus();
      el.value=fv;
      try{ el.setSelectionRange(fss,fse); }catch(_){}
    }
  }
}

/* ── Receive props ────────────────────────────────── */
function onRender(a, theme){
  labels=a.labels||labels;

  /* theme comes from ev.data.theme (not ev.data.args) */
  if(theme) _theme = theme;

  if(!initialized){
    initialized=true;
    const pr=a.rows||[];
    rows=pr.length
      ? pr.map(r=>Object.assign(nr(r.symbol||''),{
          id:r.id!==undefined?r.id:_rid-1,
          confirmed:!!r.confirmed, symbol:r.symbol||'',
          name:r.name||'',exchange:r.exchange||'',country:r.country||'',
          name_ja:r.name_ja||'',src:r.src||'',
        }))
      : [nr()];
    _rid=Math.max(_rid,...rows.map(r=>r.id+1));
  }

  /* Apply search results from Python */
  const sr=a.search_results;
  let _needsRender=true; /* set false if we handle render ourselves */
  if(sr && sr.seq!==undefined && sr.seq!==lastSrSeq){
    lastSrSeq=sr.seq;

    if(sr.single){
      const row=rows.find(r=>r.id===sr.row_id);
      if(row){
        row.searching=false;
        row.sug=sr.results||[];
        row.hi=row.sug.length?0:-1;
        /* pasted name with no candidates any more → plain "not found" row
           (also stops onFoc from re-searching on every focus restore) */
        if(row.pick&&!row.sug.length){row.pick=false;row.notFound=true;}
        if(sr.auto_confirm && row.sug.length>0){
          _needsRender=false;
          confirmRow(row, row.sug[0]); return;
        }
        /* Surgical update: only update suggestion dropdown, no full re-render */
        _needsRender=false;
        _renderSuggestionsFor(row);
      }
    } else if(sr.bulk){
      let changed=false;
      for(const item of(sr.results||[])){
        const row=rows.find(r=>r.id===item.row_id);
        if(!row)continue;
        row.searching=false;
        if(item.duplicate){
          row.duplicate=true;row.notFound=false;
        } else if(item.pick){
          /* company name: never auto-confirmed — user picks from candidates */
          row.pick=true;row.notFound=false;
          changed=true;
        } else if(item.symbol){
          Object.assign(row,{confirmed:true,symbol:item.symbol,
            name:item.name||'',name_ja:item.name_ja||'',exchange:item.exchange||'',
            country:item.country||'',inp:item.symbol,
            notFound:false,duplicate:false,sug:[],hi:-1});
          changed=true;
        } else {
          row.notFound=true;row.inp=row.inp||'';
        }
      }
      if(changed) notifyRows();
      /* open the first pasted name's candidates */
      const firstPick=rows.find(r=>r.pick&&!r.confirmed);
      if(firstPick){
        _needsRender=false; render();
        setTimeout(()=>{const el=document.getElementById('i'+firstPick.id);if(el)el.focus();},30);
      }
    }
  }
  if(_needsRender) safeRender();
}

window.addEventListener('load',()=>ST.ready());
</script>
</body>
</html>"""