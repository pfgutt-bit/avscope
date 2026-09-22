from __future__ import annotations

from html import escape

import streamlit as st

from src.formatters import format_compact, format_full_number, format_integer, format_percent


CSS = """
<style>
:root { color-scheme: dark; }
html, body, [data-testid="stAppViewContainer"] { background: #0B0D10; color: #F4F6F8; }
[data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stHeader"] { background: rgba(11,13,16,.92); }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
.stAppViewBlockContainer { max-width: 1280px; padding-top: 1.25rem; padding-bottom: 4rem; }
html, body, [class*="st-"] { font-family: Inter, "Segoe UI", system-ui, sans-serif; letter-spacing: 0; }
h1, h2, h3, p { letter-spacing: 0 !important; }
h2 { font-size: 1.28rem !important; font-weight: 600 !important; margin: 2.35rem 0 .25rem !important; }
h3 { font-size: .98rem !important; font-weight: 600 !important; color: #F4F6F8 !important; }
.av-topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; padding: 5px 0 20px; border-bottom:1px solid rgba(255,255,255,.08); }
.av-brand { display:flex; align-items:baseline; gap:14px; min-width:0; }
.av-wordmark { color:#F4F6F8; font-size:1.28rem; font-weight:650; white-space:nowrap; }
.av-subtitle { color:#929AA5; font-size:.86rem; white-space:nowrap; }
.av-meta { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.av-badge { color:#B8C0CA; border:1px solid rgba(255,255,255,.1); background:#111419; border-radius:999px; padding:5px 9px; font-size:.72rem; white-space:nowrap; }
.av-kicker { color:#929AA5; font-size:.72rem; font-weight:600; text-transform:uppercase; margin-top:26px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:rgba(255,255,255,.08) !important; border-radius:10px !important; background:#111419; box-shadow:none !important; }
[data-testid="stSelectbox"] label, [data-testid="stDateInput"] label { color:#929AA5 !important; font-size:.76rem !important; font-weight:600 !important; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div { background:#171B21 !important; border-color:rgba(255,255,255,.1) !important; transition:border-color 150ms ease, background 150ms ease; }
[data-baseweb="select"] > div:hover, [data-baseweb="input"] > div:hover { border-color:rgba(110,168,254,.48) !important; }
.stButton > button { border-color:rgba(255,255,255,.1); background:#171B21; color:#F4F6F8; transition:background 150ms ease,border-color 150ms ease,transform 150ms ease; }
.stButton > button:hover { border-color:rgba(110,168,254,.55); background:#1C222A; color:#F4F6F8; }
.stButton > button:focus-visible { outline:2px solid #6EA8FE; outline-offset:2px; }
.av-route-hero { display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); align-items:center; gap:28px; padding:29px 4px 24px; }
.av-airport:last-child { text-align:right; }
.av-code { color:#F4F6F8; font-size:clamp(2.15rem,5vw,4.4rem); line-height:1; font-weight:620; font-variant-numeric:tabular-nums; }
.av-place { color:#929AA5; font-size:.92rem; margin-top:9px; overflow-wrap:anywhere; }
.av-route-line { min-width:150px; display:flex; align-items:center; gap:10px; color:#6EA8FE; }
.av-route-line:before { content:""; height:1px; background:rgba(110,168,254,.55); flex:1; }
.av-arrow { font-size:1.25rem; }
.av-period { color:#B8C0CA; font-size:.82rem; text-align:center; margin-top:-8px; margin-bottom:20px; }
.av-partial { color:#E7B65A; }
.av-kpi-rail { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); border:1px solid rgba(255,255,255,.08); border-radius:10px; background:#111419; overflow:hidden; }
.av-kpi { min-width:0; padding:18px 20px 16px; border-right:1px solid rgba(255,255,255,.08); }
.av-kpi:last-child { border-right:0; }
.av-kpi-label { color:#929AA5; font-size:.69rem; font-weight:650; text-transform:uppercase; }
.av-kpi-value { color:#F4F6F8; font-size:1.48rem; font-weight:620; margin-top:7px; font-variant-numeric:tabular-nums; white-space:nowrap; }
.av-kpi-full { color:#6F7884; font-size:.68rem; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.av-delta { font-size:.72rem; margin-top:7px; line-height:1.35; }
.av-delta-up { color:#45C486; } .av-delta-down { color:#E36D76; }
.av-delta-context { color:#929AA5; display:block; }
.av-section-head { display:flex; justify-content:space-between; align-items:flex-end; gap:14px; margin-top:38px; margin-bottom:2px; }
.av-section-title { color:#F4F6F8; font-size:1.22rem; font-weight:600; }
.av-section-copy { color:#929AA5; font-size:.78rem; margin-top:4px; }
.av-hhi { border-left:1px solid rgba(255,255,255,.08); padding:22px 4px 22px 28px; min-height:230px; display:flex; flex-direction:column; justify-content:center; }
.av-hhi-label { color:#929AA5; font-size:.72rem; text-transform:uppercase; font-weight:600; }
.av-hhi-value { color:#F4F6F8; font-size:2.5rem; font-weight:620; margin:8px 0; font-variant-numeric:tabular-nums; }
.av-hhi-copy { color:#929AA5; font-size:.78rem; line-height:1.55; max-width:250px; }
.av-empty { border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:34px 22px; text-align:center; background:#111419; }
.av-empty strong { display:block; color:#F4F6F8; margin-bottom:6px; }.av-empty span { color:#929AA5; font-size:.86rem; }
.av-quality-ok { color:#45C486; }.av-quality-warn { color:#E7B65A; }
[data-testid="stExpander"] { border-color:rgba(255,255,255,.08) !important; background:#111419; border-radius:10px !important; }
[data-testid="stExpander"] [data-testid="stIconMaterial"] { font-size:0 !important; width:14px; min-width:14px; }
[data-testid="stExpander"] [data-testid="stIconMaterial"]::before { content:"›"; font-family:system-ui,sans-serif; font-size:1rem; line-height:1; }
[data-testid="stExpander"] details[open] [data-testid="stIconMaterial"]::before { content:"⌄"; }
[data-testid="stDataFrame"] { border:1px solid rgba(255,255,255,.08); border-radius:8px; overflow:hidden; }
a { color:#8CB9FE !important; text-decoration:none; } a:hover { text-decoration:underline; }
@media (max-width: 850px) {
  .av-kpi-rail { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .av-kpi { border-bottom:1px solid rgba(255,255,255,.08); }
  .av-kpi:nth-child(2n) { border-right:0; }
  .av-kpi:last-child { grid-column:1/-1; border-bottom:0; }
  .av-hhi { border-left:0; border-top:1px solid rgba(255,255,255,.08); padding:22px 4px; min-height:0; }
}
@media (max-width: 600px) {
  .stAppViewBlockContainer { padding-left:1rem; padding-right:1rem; }
  .av-topbar { align-items:flex-start; }.av-subtitle { display:none; }.av-meta { gap:5px; }
  .av-route-hero { gap:11px; }.av-route-line { min-width:64px; }.av-place { font-size:.78rem; }
  .av-kpi { padding:15px 14px; }.av-kpi-value { font-size:1.22rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition:none !important; scroll-behavior:auto !important; } }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def render_topbar(updated_label: str) -> None:
    st.markdown(
        f"""<div class="av-topbar"><div class="av-brand"><span class="av-wordmark">◈ AVScope</span><span class="av-subtitle">Explore o mercado aéreo brasileiro.</span></div><div class="av-meta"><span class="av-badge">Dados ANAC</span><span class="av-badge">Dados até {escape(updated_label)}</span></div></div>""",
        unsafe_allow_html=True,
    )


def render_route_hero(
    origin_code: str,
    origin_place: str,
    destination_code: str,
    destination_place: str,
    period_label: str,
    partial_label: str | None,
) -> None:
    partial = f' <span class="av-partial">· {escape(partial_label)}</span>' if partial_label else ""
    st.markdown(
        f"""<div class="av-route-hero"><div class="av-airport"><div class="av-code">{escape(origin_code)}</div><div class="av-place">{escape(origin_place)}</div></div><div class="av-route-line"><span class="av-arrow">→</span></div><div class="av-airport"><div class="av-code">{escape(destination_code)}</div><div class="av-place">{escape(destination_place)}</div></div></div><div class="av-period">{escape(period_label)}{partial}</div>""",
        unsafe_allow_html=True,
    )


def _delta_html(comparison: dict[str, object]) -> str:
    growth = comparison.get("CRESCIMENTO_PCT")
    if growth is None:
        return ""
    direction_class = "av-delta-up" if float(growth) >= 0 else "av-delta-down"
    arrow = "↑" if float(growth) >= 0 else "↓"
    month = int(comparison["MES_FINAL"])
    current = int(comparison["ANO_ATUAL"]) % 100
    previous = int(comparison["ANO_ANTERIOR"]) % 100
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    label = "YTD" if comparison.get("TIPO_COMPARACAO") == "YTD" else "ano"
    return f'<div class="av-delta {direction_class}">{arrow} {format_percent(abs(float(growth)))} {label}<span class="av-delta-context">jan–{months[month-1]}/{current:02d} vs jan–{months[month-1]}/{previous:02d}</span></div>'


def render_kpi_rail(summary: dict[str, object], comparison: dict[str, object]) -> None:
    items = [
        ("Passageiros", summary.get("PASSAGEIROS_PAGOS"), "compact", _delta_html(comparison)),
        ("Assentos", summary.get("ASSENTOS"), "compact", ""),
        ("Decolagens", summary.get("DECOLAGENS"), "compact", ""),
        ("Load Factor", summary.get("LOAD_FACTOR_PCT"), "percent", ""),
        ("Companhias", summary.get("NUMERO_COMPANHIAS"), "integer", ""),
    ]
    cells = []
    for label, value, kind, extra in items:
        display = format_percent(value) if kind == "percent" else format_integer(value) if kind == "integer" else format_compact(value)
        full = format_percent(value, 2) if kind == "percent" else format_full_number(value)
        cells.append(f'<div class="av-kpi"><div class="av-kpi-label">{label}</div><div class="av-kpi-value">{display}</div><div class="av-kpi-full" title="{full}">{full}</div>{extra}</div>')
    st.markdown(f'<div class="av-kpi-rail">{"".join(cells)}</div>', unsafe_allow_html=True)


def render_section_header(title: str, copy: str | None = None) -> None:
    subtitle = f'<div class="av-section-copy">{escape(copy)}</div>' if copy else ""
    st.markdown(f'<div class="av-section-head"><div><div class="av-section-title">{escape(title)}</div>{subtitle}</div></div>', unsafe_allow_html=True)


def render_hhi(value: float | None) -> None:
    st.markdown(
        f"""<div class="av-hhi"><div class="av-hhi-label">Índice de concentração</div><div class="av-hhi-value">{format_integer(value)}</div><div class="av-hhi-copy">O HHI resume a distribuição de participação entre as companhias. Quanto maior o valor, mais concentrado é o mercado.</div></div>""",
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown('<div class="av-empty"><strong>Nenhuma operação encontrada para este recorte.</strong><span>Tente ampliar o período ou selecionar todas as companhias.</span></div>', unsafe_allow_html=True)

