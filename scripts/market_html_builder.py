"""
market_html_builder.py
네이버 증권 스타일 HTML 빌더
- 밝고 깔끔한 화이트 베이스
- 파란 계열 포인트 컬러
- 상승 #e83c3c / 하락 #1261c4 (네이버 증권 컨벤션)
"""

import re
from datetime import datetime

# ── 공통 컬러 시스템 (네이버 증권 기반) ──────────────────────────────────────
UP_COLOR   = "#e83c3c"   # 상승 빨강
DOWN_COLOR = "#1261c4"   # 하락 파랑
UP_BG      = "#fff0f0"
DOWN_BG    = "#f0f4ff"
BORDER     = "#e4e9f0"
TEXT_MAIN  = "#1a1a1a"
TEXT_SUB   = "#666e7a"
TEXT_MUTED = "#9ea7b4"
BG_CARD    = "#ffffff"
BG_PAGE    = "#f4f6f9"
BG_HEADER  = "#ebf0f8"
BLUE_MAIN  = "#1261c4"
BLUE_LIGHT = "#e8f0fc"

SECTION_LABELS = {
    "1": ("OPEN",    "#1261c4"),
    "2": ("DRIVER",  "#0b7a4e"),
    "3": ("SECTOR",  "#b45309"),
    "4": ("KR",      "#6d28d9"),
    "5": ("WATCH",   "#b91c1c"),
    "6": ("RISK",    "#0e7490"),
    "7": ("SUMMARY", "#1a1a1a"),
}

CSS = ""  # 인라인 스타일만 사용


# ── 시세 대시보드 ─────────────────────────────────────────────────────────────

def build_ticker_dashboard(quotes: dict, now_kst: datetime) -> str:
    time_str = now_kst.strftime("%Y.%m.%d %H:%M KST 기준")

    def idx_card(q: dict) -> str:
        up    = q["chg_pct"] >= 0
        color = UP_COLOR if up else DOWN_COLOR
        bg    = UP_BG if up else DOWN_BG
        sign  = "+" if up else ""
        arrow = "▲" if up else "▼"
        chg_abs = abs(q["chg_pct"])
        return (
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;'
            f'padding:14px 16px;flex:1;min-width:110px;text-align:center;">'
            f'<div style="font-size:0.75em;color:{TEXT_SUB};margin-bottom:6px;font-weight:500;">'
            f'{q["name"]}</div>'
            f'<div style="font-size:1.22em;font-weight:700;color:{TEXT_MAIN};'
            f'font-variant-numeric:tabular-nums;">{q["price"]:,.2f}</div>'
            f'<div style="display:inline-flex;align-items:center;gap:4px;margin-top:5px;'
            f'padding:3px 8px;background:{bg};border-radius:4px;">'
            f'<span style="font-size:0.78em;font-weight:700;color:{color};">'
            f'{arrow} {sign}{chg_abs:.2f}%</span></div>'
            f'</div>'
        )

    def macro_card(q: dict) -> str:
        up    = q["chg_pct"] >= 0
        color = UP_COLOR if up else DOWN_COLOR
        sign  = "+" if up else ""
        arrow = "▲" if up else "▼"
        return (
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;'
            f'padding:12px 14px;flex:1;min-width:90px;text-align:center;">'
            f'<div style="font-size:0.72em;color:{TEXT_MUTED};margin-bottom:4px;">{q["name"]}</div>'
            f'<div style="font-size:1.0em;font-weight:600;color:{TEXT_MAIN};">{q["price"]:,.2f}</div>'
            f'<div style="font-size:0.75em;font-weight:600;color:{color};margin-top:3px;">'
            f'{arrow} {sign}{q["chg_pct"]:.2f}%</div>'
            f'</div>'
        )

    idx_cards   = [idx_card(quotes[s])   for s in ["^IXIC","^GSPC","^DJI","^VIX"]  if s in quotes]
    macro_cards = [macro_card(quotes[s]) for s in ["DX-Y.NYB","CL=F","GC=F"]        if s in quotes]

    # 종목 테이블
    rows = []
    KR_MAP = {
        "NVDA":  ["삼성전자", "SK하이닉스", "한미반도체"],
        "AMD":   ["삼성전자", "SK하이닉스"],
        "INTC":  ["삼성전자"],
        "TSM":   ["삼성전자", "DB하이텍"],
        "TSLA":  ["LG에너지솔루션", "삼성SDI", "포스코퓨처엠"],
        "AAPL":  ["LG이노텍", "삼성전기"],
        "MSFT":  ["카카오", "NAVER"],
        "META":  ["카카오"],
        "AMZN":  ["쿠팡"],
        "GOOGL": ["카카오", "NAVER"],
    }
    for i, sym in enumerate(["NVDA","AMD","INTC","TSM","AAPL","MSFT","TSLA","AMZN","GOOGL","META"]):
        q = quotes.get(sym)
        if not q:
            continue
        up    = q["chg_pct"] >= 0
        color = UP_COLOR if up else DOWN_COLOR
        bg    = UP_BG if up else DOWN_BG
        sign  = "+" if up else ""
        arrow = "▲" if up else "▼"
        kr    = ", ".join(KR_MAP.get(sym, ["-"]))
        row_bg = BG_CARD if i % 2 == 0 else "#f9fafc"
        rows.append(
            f'<tr style="background:{row_bg};">'
            f'<td style="padding:10px 14px;border-bottom:1px solid {BORDER};white-space:nowrap;">'
            f'<span style="font-weight:600;color:{TEXT_MAIN};font-size:0.9em;">{q["name"]}</span>'
            f'<span style="color:{TEXT_MUTED};font-size:0.75em;margin-left:6px;">{sym}</span></td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid {BORDER};text-align:right;'
            f'font-variant-numeric:tabular-nums;font-weight:600;color:{TEXT_MAIN};font-size:0.9em;">'
            f'{q["price"]:,.2f}</td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid {BORDER};text-align:right;">'
            f'<span style="display:inline-block;padding:2px 7px;background:{bg};'
            f'border-radius:4px;font-size:0.8em;font-weight:700;color:{color};">'
            f'{arrow} {sign}{q["chg_pct"]:.2f}%</span></td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid {BORDER};'
            f'color:{TEXT_SUB};font-size:0.8em;">{kr}</td>'
            f'</tr>'
        )

    idx_html   = "".join(idx_cards)
    macro_html = "".join(macro_cards)
    rows_html  = "".join(rows)

    return (
        f'<div style="background:{BG_PAGE};border-radius:12px;padding:20px;margin-bottom:1.8em;'
        f'border:1px solid {BORDER};">'

        # 헤더
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="display:inline-block;width:4px;height:18px;background:{BLUE_MAIN};border-radius:2px;"></span>'
        f'<span style="font-size:0.95em;font-weight:700;color:{TEXT_MAIN};">미국 증시 시세</span>'
        f'</div>'
        f'<span style="font-size:0.72em;color:{TEXT_MUTED};">{time_str}</span>'
        f'</div>'

        # 주요 지수
        f'<div style="font-size:0.72em;font-weight:600;color:{TEXT_SUB};'
        f'margin-bottom:8px;letter-spacing:0.5px;">주요 지수</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;">'
        f'{idx_html}</div>'

        # 매크로
        f'<div style="font-size:0.72em;font-weight:600;color:{TEXT_SUB};'
        f'margin-bottom:8px;letter-spacing:0.5px;">매크로</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;">'
        f'{macro_html}</div>'

        # 종목 테이블
        f'<div style="font-size:0.72em;font-weight:600;color:{TEXT_SUB};'
        f'margin-bottom:8px;letter-spacing:0.5px;">핵심 종목 & 한국 연관주</div>'
        f'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER};">'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.88em;background:{BG_CARD};">'
        f'<thead><tr style="background:{BG_HEADER};">'
        f'<th style="padding:9px 14px;text-align:left;color:{TEXT_SUB};font-weight:600;'
        f'font-size:0.82em;border-bottom:2px solid {BORDER};">종목</th>'
        f'<th style="padding:9px 14px;text-align:right;color:{TEXT_SUB};font-weight:600;'
        f'font-size:0.82em;border-bottom:2px solid {BORDER};">현재가</th>'
        f'<th style="padding:9px 14px;text-align:right;color:{TEXT_SUB};font-weight:600;'
        f'font-size:0.82em;border-bottom:2px solid {BORDER};">등락</th>'
        f'<th style="padding:9px 14px;text-align:left;color:{TEXT_SUB};font-weight:600;'
        f'font-size:0.82em;border-bottom:2px solid {BORDER};">한국 연관</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
        f'</div>'
    )


# ── 섹션 헤딩 ─────────────────────────────────────────────────────────────────

def render_heading(text: str) -> str:
    m = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
    if not m:
        return (
            f'<h2 style="font-size:1.1em;font-weight:700;color:{TEXT_MAIN};'
            f'margin:2.2em 0 0.8em;padding:10px 14px;'
            f'background:{BG_HEADER};border-left:4px solid {BORDER};border-radius:0 6px 6px 0;">'
            f'{text}</h2>'
        )
    num, title_text = m.group(1), m.group(2)
    label_info = SECTION_LABELS.get(num)
    badge = ""
    bar_color = BLUE_MAIN
    if label_info:
        label, color = label_info
        bar_color = color
        badge = (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'font-size:0.65em;font-weight:700;padding:2px 7px;border-radius:3px;'
            f'margin-right:9px;vertical-align:middle;letter-spacing:0.8px;'
            f'font-family:monospace;">{label}</span>'
        )
    return (
        f'<h2 style="font-size:1.08em;font-weight:700;color:{TEXT_MAIN};'
        f'margin:2.2em 0 0.8em;padding:10px 14px;display:flex;align-items:center;'
        f'background:{BG_HEADER};border-left:4px solid {bar_color};border-radius:0 6px 6px 0;">'
        f'{badge}{title_text}</h2>'
    )


# ── 섹터 카드 ─────────────────────────────────────────────────────────────────

def render_sector_cards(bullet_lines: list) -> str:
    accent_colors = [BLUE_MAIN, "#0b7a4e", "#b45309", "#6d28d9", "#b91c1c"]
    cards = []
    for i, line in enumerate(bullet_lines):
        text   = re.sub(r"^[-*]\s*", "", line.strip())
        m      = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
        accent = accent_colors[i % len(accent_colors)]
        bg     = BLUE_LIGHT if accent == BLUE_MAIN else "#f8f9fa"
        if m:
            term, desc = m.group(1), m.group(2)
            cards.append(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
                f'border-top:3px solid {accent};border-radius:8px;padding:14px 16px;">'
                f'<div style="font-size:0.85em;font-weight:700;color:{accent};'
                f'margin-bottom:6px;">{term}</div>'
                f'<div style="font-size:0.87em;color:{TEXT_SUB};line-height:1.65;">{desc}</div>'
                f'</div>'
            )
        else:
            cards.append(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
                f'border-top:3px solid {accent};border-radius:8px;padding:14px 16px;">'
                f'<div style="font-size:0.87em;color:{TEXT_SUB};line-height:1.65;">{text}</div>'
                f'</div>'
            )
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));'
        'gap:10px;margin:0.8em 0;">'
        + "".join(f'<div>{c}</div>' for c in cards)
        + '</div>'
    )


# ── 3줄 요약 박스 ─────────────────────────────────────────────────────────────

def _strip_bullet(line: str) -> str:
    return re.sub(r"^[-*]\s*", "", line.strip())


def render_summary_box(bullet_lines: list) -> str:
    items = []
    icons = ["①", "②", "③"]
    for i, l in enumerate(bullet_lines):
        icon = icons[i] if i < len(icons) else "•"
        items.append(
            f'<li style="display:flex;gap:10px;margin-bottom:10px;list-style:none;">'
            f'<span style="flex-shrink:0;font-size:0.9em;font-weight:700;color:{BLUE_MAIN};">'
            f'{icon}</span>'
            f'<span style="font-size:0.92em;color:{TEXT_MAIN};line-height:1.7;">'
            f'{_strip_bullet(l)}</span>'
            f'</li>'
        )
    items_html = "".join(items)
    return (
        f'<div style="background:{BLUE_LIGHT};border:1px solid #c5d8f5;'
        f'border-radius:10px;padding:18px 20px;margin:1.8em 0;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
        f'<span style="display:inline-block;width:4px;height:16px;background:{BLUE_MAIN};'
        f'border-radius:2px;"></span>'
        f'<span style="font-size:0.82em;font-weight:700;color:{BLUE_MAIN};'
        f'letter-spacing:0.5px;">핵심 요약</span>'
        f'</div>'
        f'<ul style="margin:0;padding:0;">{items_html}</ul>'
        f'</div>'
    )


# ── 마크다운 → HTML 변환 ──────────────────────────────────────────────────────

SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def md_to_html(md: str, quotes: dict) -> str:
    # 출처 태그 제거 (노이즈 제거)
    md = SOURCE_TAG_PATTERN.sub("", md)

    lines    = md.split("\n")
    html_out = ["{DASHBOARD}"]   # 대시보드 플레이스홀더
    in_ul    = False
    ul_buf   = []
    cur_sec  = None
    is_lead  = True

    def flush_ul():
        nonlocal in_ul, ul_buf
        if not ul_buf:
            in_ul = False
            return
        if cur_sec in ("3", "5"):
            html_out.append(render_sector_cards(ul_buf))
        elif cur_sec == "7":
            html_out.append(render_summary_box(ul_buf))
        else:
            html_out.append(
                f'<ul style="padding-left:1.4em;margin:0.6em 0;line-height:1.9;">'
            )
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                html_out.append(
                    f'<li style="margin-bottom:6px;color:{TEXT_SUB};font-size:0.93em;">{t}</li>'
                )
            html_out.append("</ul>")
        ul_buf.clear()
        in_ul = False

    for line in lines:
        stripped = line.strip()

        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            continue

        if line.startswith("## "):
            if in_ul:
                flush_ul()
            heading_text = line[3:].strip()
            html_out.append(render_heading(heading_text))
            m = re.match(r"^(\d+)\.", heading_text)
            cur_sec = m.group(1) if m else None
            is_lead = False

        elif re.match(r"^[-*] ", line):
            is_lead = False
            in_ul   = True
            ul_buf.append(line.strip())

        else:
            if in_ul and stripped:
                flush_ul()
            if stripped:
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                if is_lead and cur_sec is None:
                    # 리드 문단
                    html_out.append(
                        f'<div style="background:{BG_HEADER};border-left:4px solid {BLUE_MAIN};'
                        f'border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:1.6em;">'
                        f'<p style="margin:0;line-height:1.85;color:{TEXT_MAIN};'
                        f'font-size:1.02em;font-weight:500;">{t}</p>'
                        f'</div>'
                    )
                    is_lead = False
                else:
                    html_out.append(
                        f'<p style="line-height:1.9;margin:0.8em 0;'
                        f'color:{TEXT_SUB};font-size:0.95em;">{t}</p>'
                    )
            else:
                if in_ul:
                    flush_ul()

    if in_ul:
        flush_ul()

    body = "\n".join(html_out)

    return (
        f'<div style="font-family:\'Noto Sans KR\',\'Malgun Gothic\',Apple SD Gothic Neo,'
        f'sans-serif;max-width:720px;margin:0 auto;color:{TEXT_MAIN};'
        f'word-break:keep-all;background:#ffffff;padding:4px;">'
        f'{body}'
        f'<div style="margin-top:2em;padding:12px 16px;background:#f9fafc;'
        f'border:1px solid {BORDER};border-radius:6px;'
        f'font-size:0.78em;color:{TEXT_MUTED};line-height:1.7;">'
        f'본 콘텐츠는 공개 데이터 기반 자동 생성 정보로, 투자 권유가 아닙니다. '
        f'실제 투자 결정은 본인 판단 하에 전문가와 상담 후 진행하시기 바랍니다.'
        f'</div>'
        f'</div>'
    )
