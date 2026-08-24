"""
it_html_builder.py
IT 리포팅 + 증시 리포팅 공통 HTML 빌더.

디자인 컨셉 "기술 데이터시트 / 브리핑 노트":
카드형 파스텔 배지 대신 모노스페이스 인덱스 + 헤어라인 룰 중심의
엔지니어링 스펙시트/마켓 터미널 톤으로 통일. (2026-08 리디자인)

공통: 폰트 토큰, 헤어라인 헤딩, 리드 문단, 요약 노트
IT 전용: 앰버 시그널 컬러, build_meta_bar(), md_to_html()
증시 전용: 네이버 증권 컨벤션(상승 적/하락 청), build_ticker_dashboard(), md_to_html_market()
"""

import re
from datetime import datetime

# ── 폰트 토큰 ────────────────────────────────────────────────────────────────
# Blogger 포스트 본문에 삽입되는 <link>는 대부분의 커스텀 템플릿에서 유지되지만,
# 메일/RSS 리더 등 일부 구독 경로에서는 무시될 수 있어 폴백을 촘촘히 둔다.
FONT_IMPORT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700'
    '&family=IBM+Plex+Sans+KR:wght@500;600;700&display=swap" rel="stylesheet">'
)
FONT_DISPLAY = "'IBM Plex Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
FONT_BODY    = "'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
FONT_MONO    = "'IBM Plex Mono','D2Coding','SFMono-Regular',Consolas,monospace"

# ── 공통 디자인 토큰 (엔지니어링 데이터시트 톤) ───────────────────────────────
INK        = "#1C2230"   # 헤딩/본문 강조
BORDER     = "#DADFE6"   # 헤어라인
TEXT_MAIN  = "#1C2230"
TEXT_SUB   = "#5B6472"
TEXT_MUTED = "#9099A6"
BG_CARD    = "#ffffff"
BG_PAGE    = "#F7F7F5"   # 미세하게 따뜻한 종이톤 (크림/테라코타 클리셰 회피용으로 채도 최소화)

# ── IT 전용 포인트 컬러: 블루프린트 주석 앰버 ─────────────────────────────────
ACCENT_MAIN  = "#B4550C"
ACCENT_LIGHT = "#FBEFE4"
BG_HEADER    = "#FBEFE4"

# ── 증시 전용 컬러 (네이버 증권 컨벤션: 상승=적, 하락=청 — 국내 독자 관례 유지) ─
UP_COLOR         = "#C23B3B"
DOWN_COLOR       = "#2E5FA3"
UP_BG            = "#FBEEEE"
DOWN_BG          = "#EEF2F8"
STOCK_BLUE       = "#2E5FA3"
STOCK_BLUE_LIGHT = "#EEF2F8"
STOCK_BG_HEADER  = "#EEF2F8"

# ── IT 섹션 라벨 (모노스페이스 러닝 인덱스로 사용) ────────────────────────────
SECTION_LABELS = {
    "1": ("TECH",    "#B4550C"),
    "2": ("TREND",   "#3F7A5C"),
    "3": ("CORE",    "#8A5A17"),
    "4": ("IMPACT",  "#5C4B9E"),
    "5": ("CASE",    "#9E3B3B"),
    "6": ("INSIGHT", "#2E6B7A"),
    "7": ("SUMMARY", "#1C2230"),
}

# ── 증시 섹션 라벨 ───────────────────────────────────────────────────────────
STOCK_SECTION_LABELS = {
    "1": ("OPEN",    "#2E5FA3"),
    "2": ("DRIVER",  "#3F7A5C"),
    "3": ("SECTOR",  "#8A5A17"),
    "4": ("KR",      "#5C4B9E"),
    "5": ("WATCH",   "#9E3B3B"),
    "6": ("RISK",    "#2E6B7A"),
    "7": ("SUMMARY", "#1C2230"),
}

# ── 증시 한국 연관주 매핑 ─────────────────────────────────────────────────────
STOCK_KR_MAP = {
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
    "SOXX":  ["삼성전자", "SK하이닉스", "한미반도체"],
}

SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


# ════════════════════════════════════════════════════════════════════════════════
# CTA 버튼 블록
# ════════════════════════════════════════════════════════════════════════════════

def render_cta_button(
    label: str,
    url: str,
    description: str = "",
    button_text: str = "바로가기 →",
    color: str = None,
) -> str:
    """
    포스트 하단(면책 박스 앞)에 삽입할 CTA 버튼 블록.

    Parameters
    ----------
    label       : 상단 강조 텍스트  (예: "KPC 정보관리기술사 설명회")
    url         : 버튼 링크
    description : 버튼 위 보조 설명 (생략 가능)
    button_text : 버튼 라벨         (기본값: "바로가기 →")
    color       : 포인트 컬러       (기본값: ACCENT_MAIN)
    """
    c = color or ACCENT_MAIN
    desc_html = (
        f'<p style="font-size:0.85em;color:{TEXT_SUB};margin:0 0 14px;line-height:1.7;">'
        f'{description}</p>'
        if description else ""
    )
    return (
        f'<div style="border:1px solid {BORDER};border-top:3px solid {c};'
        f'padding:22px 20px;margin:2em 0;text-align:center;">'
        f'<p style="font-family:{FONT_MONO};font-size:0.72em;font-weight:600;color:{c};'
        f'letter-spacing:0.08em;margin:0 0 10px;">{label}</p>'
        f'{desc_html}'
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;background:{c};color:#fff;'
        f'font-size:0.88em;font-weight:700;padding:10px 26px;'
        f'border-radius:3px;text-decoration:none;letter-spacing:0.3px;">'
        f'{button_text}</a>'
        f'</div>'
    )


# ════════════════════════════════════════════════════════════════════════════════
# IT 리포팅 전용
# ════════════════════════════════════════════════════════════════════════════════

def build_meta_bar(topic: str, tags: list, now_kst: datetime, read_min: int = 4) -> str:
    """헤더를 '기술 데이터시트 표지'처럼 구성: 모노스페이스 문서번호 + 헤어라인."""
    doc_no  = now_kst.strftime("TR-%Y%m%d")
    time_str = now_kst.strftime("%Y.%m.%d %H:%M KST")
    tag_chips = "".join(
        f'<span style="display:inline-block;border:1px solid {BORDER};'
        f'color:{TEXT_SUB};font-family:{FONT_MONO};font-size:0.72em;padding:3px 9px;'
        f'border-radius:3px;margin-right:6px;margin-bottom:6px;">{t}</span>'
        for t in tags[:5]
    )
    return (
        f'{FONT_IMPORT}'
        f'<div style="margin-bottom:2em;">'
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'font-family:{FONT_MONO};font-size:0.72em;letter-spacing:0.06em;color:{TEXT_MUTED};'
        f'border-bottom:1px solid {INK};padding-bottom:8px;margin-bottom:14px;">'
        f'<span>{doc_no} · TECH BRIEF</span>'
        f'<span>{time_str} · {read_min} MIN READ</span>'
        f'</div>'
        f'<div style="font-family:{FONT_DISPLAY};font-size:1.5em;font-weight:700;'
        f'color:{INK};line-height:1.35;margin-bottom:14px;">{topic}</div>'
        f'<div>{tag_chips}</div>'
        f'</div>'
    )


def render_heading(text: str) -> str:
    """섹션 헤딩을 컬러 배지 대신 '러닝 인덱스 + 앰버 룰'로 표시."""
    m = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
    if not m:
        return (
            f'<h2 style="font-family:{FONT_DISPLAY};font-size:1.12em;font-weight:700;'
            f'color:{INK};margin:2.4em 0 0.9em;padding-bottom:8px;'
            f'border-bottom:2px solid {ACCENT_MAIN};">{text}</h2>'
        )
    num, title_text = m.group(1), m.group(2)
    label_info = SECTION_LABELS.get(num)
    label, bar_color = label_info if label_info else ("SEC", ACCENT_MAIN)
    total = f"{len(SECTION_LABELS):02d}"
    return (
        f'<div style="margin:2.4em 0 0.9em;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;font-family:{FONT_MONO};'
        f'font-size:0.72em;font-weight:600;letter-spacing:0.08em;color:{bar_color};margin-bottom:6px;">'
        f'<span>{num.zfill(2)}/{total}</span><span style="color:{TEXT_MUTED};">{label}</span>'
        f'</div>'
        f'<h2 style="font-family:{FONT_DISPLAY};font-size:1.16em;font-weight:700;color:{INK};'
        f'margin:0;padding-bottom:8px;border-bottom:2px solid {bar_color};">{title_text}</h2>'
        f'</div>'
    )


def render_core_cards(bullet_lines: list) -> str:
    """파스텔 카드 그리드 대신 헤어라인으로 구분한 스펙 목록(용어–설명)으로 표시."""
    rows = []
    n = len(bullet_lines)
    for i, line in enumerate(bullet_lines):
        text = re.sub(r"^[-*]\s*", "", line.strip())
        m    = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
        bdr  = f'border-bottom:1px solid {BORDER};' if i < n - 1 else ""
        idx  = f"{i+1:02d}"
        if m:
            term, desc = m.group(1), m.group(2)
            rows.append(
                f'<div style="display:flex;gap:14px;padding:12px 0;{bdr}">'
                f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
                f'font-weight:600;color:{ACCENT_MAIN};padding-top:1px;">{idx}</span>'
                f'<div>'
                f'<div style="font-family:{FONT_DISPLAY};font-size:0.92em;font-weight:700;'
                f'color:{INK};margin-bottom:4px;">{term}</div>'
                f'<div style="font-size:0.88em;color:{TEXT_SUB};line-height:1.7;">{desc}</div>'
                f'</div></div>'
            )
        else:
            rows.append(
                f'<div style="display:flex;gap:14px;padding:12px 0;{bdr}">'
                f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
                f'font-weight:600;color:{ACCENT_MAIN};padding-top:1px;">{idx}</span>'
                f'<div style="font-size:0.88em;color:{TEXT_SUB};line-height:1.7;">{text}</div>'
                f'</div>'
            )
    return f'<div style="margin:0.6em 0 1.2em;">{"".join(rows)}</div>'


def _strip_bullet(line: str) -> str:
    return re.sub(r"^[-*]\s*", "", line.strip())


def render_summary_box(bullet_lines: list) -> str:
    """유일하게 '박스'로 강조하는 시그니처 요소: 잉크 배경 + 앰버 룰의 요약 노트."""
    items = []
    for i, l in enumerate(bullet_lines):
        items.append(
            f'<li style="display:flex;gap:12px;margin-bottom:11px;list-style:none;">'
            f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
            f'font-weight:600;color:{ACCENT_MAIN};padding-top:2px;">{i+1:02d}</span>'
            f'<span style="font-size:0.92em;color:#EDEEF1;line-height:1.7;">{_strip_bullet(l)}</span>'
            f'</li>'
        )
    items_html = "".join(items)
    return (
        f'<div style="background:{INK};border-top:3px solid {ACCENT_MAIN};'
        f'padding:20px 22px;margin:2em 0;">'
        f'<div style="font-family:{FONT_MONO};font-size:0.72em;font-weight:600;'
        f'letter-spacing:0.1em;color:{ACCENT_MAIN};margin-bottom:14px;">SUMMARY</div>'
        f'<ul style="margin:0;padding:0;">{items_html}</ul>'
        f'</div>'
    )


def render_references(articles: list) -> str:
    if not articles:
        return ""
    src_label_map = {
        "google_news":   "Google News",
        "yahoo_finance": "Yahoo Finance",
        "hacker_news":   "Hacker News",
    }
    items = []
    for i, a in enumerate(articles[:8]):
        src_label = src_label_map.get(a.get("source", ""), a.get("source", ""))
        items.append(
            f'<li id="ref-{i+1}" style="margin-bottom:7px;line-height:1.6;font-size:0.88em;">'
            f'<span style="font-family:{FONT_MONO};color:{TEXT_MUTED};">[{i+1}]</span> '
            f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
            f'style="color:{ACCENT_MAIN};text-decoration:none;">{a["title"]}</a>'
            f'<span style="color:{TEXT_MUTED};font-size:0.85em;"> — {src_label}</span></li>'
        )
    return (
        f'<div style="margin-top:2.4em;padding-top:16px;border-top:1px solid {BORDER};">'
        f'<div style="font-family:{FONT_MONO};font-size:0.68em;font-weight:600;'
        f'color:{TEXT_MUTED};letter-spacing:0.1em;margin-bottom:10px;">REFERENCES</div>'
        f'<ul style="padding-left:1.3em;margin:0;">{"".join(items)}</ul>'
        f'</div>'
    )


def render_hero_image(image: dict) -> str:
    if not image:
        return ""
    return (
        f'<div style="margin:0 0 1.8em;border-radius:10px;overflow:hidden;border:1px solid {BORDER};">'
        f'<img src="{image["url"]}" alt="{image.get("alt","")}" '
        f'style="width:100%;max-height:380px;object-fit:cover;display:block;" />'
        f'<p style="font-size:0.74em;color:{TEXT_MUTED};margin:6px 10px;text-align:right;">'
        f'Photo by <a href="{image["author_url"]}?utm_source=mystacklog&utm_medium=referral" '
        f'target="_blank" rel="noopener noreferrer" style="color:{TEXT_MUTED};">{image["author"]}</a>'
        f' on <a href="https://unsplash.com?utm_source=mystacklog&utm_medium=referral" '
        f'target="_blank" rel="noopener noreferrer" style="color:{TEXT_MUTED};">Unsplash</a>'
        f'</p></div>'
    )


def render_diagram(diagram_url: str, topic: str) -> str:
    if not diagram_url:
        return ""
    return (
        f'<div style="text-align:center;margin:1.6em 0;padding:16px;'
        f'background:{BG_PAGE};border:1px solid {BORDER};border-radius:10px;">'
        f'<img src="{diagram_url}" alt="{topic} 구조도" '
        f'style="max-width:100%;border-radius:6px;" '
        f'onerror="this.closest(\'div\').style.display=\'none\';" />'
        f'<p style="font-size:0.78em;color:{TEXT_MUTED};margin-top:10px;">{topic} 핵심 구조도</p>'
        f'</div>'
    )


def convert_source_tags(text: str, articles: list) -> str:
    """[출처: 기사제목] 태그를 본문 안에 원문 그대로 박아넣지 않고,
    REFERENCES 목록과 연결된 번호 각주 [1][2]...로 바꾼다.

    기존 방식은 잘린 영문 기사 제목(inner[:30])을 문장 중간에 그대로 삽입해서
    "...주장했다 [DeepSeek open sources DSpark, ]." 처럼 단어가 잘린 채 노출되는
    문제가 있었다(2026-08-24 실제 발행본에서 확인). 번호 각주 + REFERENCES 목록
    순서를 일치시켜서 어떤 제목이든 안전하게 표시되도록 했다.
    """
    title_to_idx = {a["title"].strip(): i + 1 for i, a in enumerate(articles[:8])}

    def replace_tag(match):
        inner = re.sub(r'^\[출처\s*:\s*', '', match.group()).rstrip(']').strip()
        idx = title_to_idx.get(inner)
        if idx is None:
            for title, i in title_to_idx.items():
                if inner[:20] in title or title[:20] in inner:
                    idx = i
                    break
        if idx is None:
            # 매칭되는 기사를 못 찾으면 굳이 잘린 원문을 노출하지 않고 조용히 제거한다.
            return ""
        return (
            f'<sup><a href="#ref-{idx}" style="color:{ACCENT_MAIN};'
            f'text-decoration:none;font-size:0.78em;">[{idx}]</a></sup>'
        )

    return SOURCE_TAG_PATTERN.sub(replace_tag, text)


def extract_meta_description(md: str, max_len: int = 150) -> str:
    for line in md.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("##") or re.match(r"^[-*]\s", stripped):
            continue
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            continue
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = SOURCE_TAG_PATTERN.sub("", text).strip()
        if not text:
            continue
        if len(text) > max_len:
            text = text[:max_len].rstrip() + "…"
        return text
    return ""


def md_to_html(md: str, articles: list = None, cta: dict = None) -> str:
    """IT 포스팅 전용 md→HTML

    cta 예시 (생략하면 CTA 없이 렌더링):
        cta = {
            "label":       "KPC 정보관리기술사 정기 설명회",
            "url":         "https://www.kpc.or.kr",
            "description": "등록 전에 설명회를 먼저 들어보는 게 맞다.",
            "button_text": "설명회 일정 확인하기 →",   # 생략 가능
        }
    """
    articles = articles or []
    md = convert_source_tags(md, articles)

    lines    = md.split("\n")
    html_out = ["{META_BAR}"]
    in_ul    = False
    ul_buf   = []
    cur_sec  = None
    is_lead  = True

    def flush_ul():
        nonlocal in_ul, ul_buf
        if not ul_buf:
            in_ul = False
            return
        if cur_sec == "3":
            html_out.append(render_core_cards(ul_buf))
        elif cur_sec == "7":
            html_out.append(render_summary_box(ul_buf))
        else:
            html_out.append(f'<ul style="padding-left:1.4em;margin:0.6em 0;line-height:1.9;">')
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                html_out.append(f'<li style="margin-bottom:6px;color:{TEXT_SUB};font-size:0.93em;">{t}</li>')
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
                t = re.sub(
                    r"`(.+?)`",
                    f'<code style="background:{BG_PAGE};padding:2px 6px;border-radius:3px;font-size:0.9em;">\\1</code>',
                    t,
                )
                if is_lead and cur_sec is None:
                    html_out.append(
                        f'<p style="margin:0 0 1.8em;padding-left:16px;border-left:3px solid {ACCENT_MAIN};'
                        f'line-height:1.85;color:{INK};font-size:1.04em;font-weight:500;">{t}</p>'
                    )
                    is_lead = False
                else:
                    html_out.append(f'<p style="line-height:1.9;margin:0.8em 0;color:{TEXT_SUB};font-size:0.95em;">{t}</p>')
            else:
                if in_ul:
                    flush_ul()

    if in_ul:
        flush_ul()

    body     = "\n".join(html_out)
    cta_html = render_cta_button(**cta) if cta else ""
    return (
        f'<div style="font-family:{FONT_BODY};max-width:720px;margin:0 auto;'
        f'color:{TEXT_MAIN};word-break:keep-all;background:#ffffff;padding:4px;">'
        f'{body}'
        f'{cta_html}'
        f'<div style="margin-top:2em;padding-top:14px;border-top:1px solid {BORDER};'
        f'font-family:{FONT_MONO};font-size:0.72em;color:{TEXT_MUTED};line-height:1.7;">'
        f'본 콘텐츠는 IT 기술 정보 제공 목적으로 작성되었습니다. 투자 판단의 근거로 사용하지 마시기 바랍니다.'
        f'</div></div>'
    )


# ════════════════════════════════════════════════════════════════════════════════
# 증시 리포팅 전용
# ════════════════════════════════════════════════════════════════════════════════

def build_ticker_dashboard(quotes: dict, now_kst: datetime) -> str:
    """파스텔 카드 그리드 대신 마켓 터미널의 '호가판'처럼 헤어라인+모노스페이스 숫자로 구성."""
    time_str = now_kst.strftime("%Y.%m.%d %H:%M KST 기준")

    def quote_cell(q: dict, big: bool = False) -> str:
        up    = q["chg_pct"] >= 0
        color = UP_COLOR if up else DOWN_COLOR
        sign  = "+" if up else ""
        arrow = "▲" if up else "▼"
        size  = "1.05em" if big else "0.88em"
        return (
            f'<div style="padding:10px 4px;border-bottom:1px solid {BORDER};">'
            f'<div style="font-size:0.72em;color:{TEXT_SUB};margin-bottom:4px;">{q["name"]}</div>'
            f'<div style="font-family:{FONT_MONO};font-size:{size};font-weight:600;color:{INK};">'
            f'{q["price"]:,.2f}</div>'
            f'<div style="font-family:{FONT_MONO};font-size:0.78em;font-weight:600;color:{color};margin-top:2px;">'
            f'{arrow} {sign}{q["chg_pct"]:.2f}%</div>'
            f'</div>'
        )

    idx_cells   = [quote_cell(quotes[s], big=True) for s in ["^IXIC","^GSPC","^DJI","^VIX"]       if s in quotes]
    macro_cells = [quote_cell(quotes[s])            for s in ["DX-Y.NYB","CL=F","GC=F","USDKRW=X"] if s in quotes]
    etf_cells   = [quote_cell(quotes[s])            for s in ["QQQ","SOXX","XLF"]                   if s in quotes]

    def grid(cells: list) -> str:
        return (
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));'
            f'gap:0 16px;margin-bottom:20px;">{"".join(cells)}</div>'
        )

    rows = []
    for sym in ["NVDA","AMD","INTC","TSM","AAPL","MSFT","TSLA","AMZN","GOOGL","META"]:
        q = quotes.get(sym)
        if not q:
            continue
        up    = q["chg_pct"] >= 0
        color = UP_COLOR if up else DOWN_COLOR
        sign  = "+" if up else ""
        arrow = "▲" if up else "▼"
        kr    = ", ".join(STOCK_KR_MAP.get(sym, ["-"]))
        rows.append(
            f'<tr>'
            f'<td style="padding:9px 10px;border-bottom:1px solid {BORDER};white-space:nowrap;">'
            f'<span style="font-weight:600;color:{INK};font-size:0.88em;">{q["name"]}</span>'
            f'<span style="font-family:{FONT_MONO};color:{TEXT_MUTED};font-size:0.72em;margin-left:6px;">{sym}</span></td>'
            f'<td style="padding:9px 10px;border-bottom:1px solid {BORDER};text-align:right;'
            f'font-family:{FONT_MONO};font-weight:600;color:{INK};font-size:0.86em;">{q["price"]:,.2f}</td>'
            f'<td style="padding:9px 10px;border-bottom:1px solid {BORDER};text-align:right;'
            f'font-family:{FONT_MONO};font-size:0.82em;font-weight:600;color:{color};white-space:nowrap;">{arrow} {sign}{q["chg_pct"]:.2f}%</td>'
            f'<td style="padding:9px 10px;border-bottom:1px solid {BORDER};color:{TEXT_SUB};font-size:0.78em;">{kr}</td>'
            f'</tr>'
        )
    rows_html = "".join(rows)

    return (
        f'{FONT_IMPORT}'
        f'<div style="border-top:2px solid {INK};border-bottom:1px solid {BORDER};'
        f'padding:16px 0 20px;margin-bottom:2em;">'
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'font-family:{FONT_MONO};font-size:0.7em;letter-spacing:0.06em;color:{TEXT_MUTED};margin-bottom:16px;">'
        f'<span>US MARKET CLOSE</span><span>{time_str}</span>'
        f'</div>'
        f'<div style="font-family:{FONT_MONO};font-size:0.68em;font-weight:600;color:{STOCK_BLUE};'
        f'letter-spacing:0.08em;margin-bottom:2px;">INDEX</div>{grid(idx_cells)}'
        f'<div style="font-family:{FONT_MONO};font-size:0.68em;font-weight:600;color:{STOCK_BLUE};'
        f'letter-spacing:0.08em;margin-bottom:2px;">MACRO</div>{grid(macro_cells)}'
        f'<div style="font-family:{FONT_MONO};font-size:0.68em;font-weight:600;color:{STOCK_BLUE};'
        f'letter-spacing:0.08em;margin-bottom:2px;">SECTOR ETF</div>{grid(etf_cells)}'
        f'<div style="font-family:{FONT_MONO};font-size:0.68em;font-weight:600;color:{STOCK_BLUE};'
        f'letter-spacing:0.08em;margin-bottom:8px;">KEY STOCKS &amp; KR PEERS</div>'
        f'<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>'
        f'<th style="padding:8px 10px;text-align:left;color:{TEXT_MUTED};font-weight:600;font-size:0.72em;border-bottom:2px solid {INK};">종목</th>'
        f'<th style="padding:8px 10px;text-align:right;color:{TEXT_MUTED};font-weight:600;font-size:0.72em;border-bottom:2px solid {INK};">현재가</th>'
        f'<th style="padding:8px 10px;text-align:right;color:{TEXT_MUTED};font-weight:600;font-size:0.72em;border-bottom:2px solid {INK};">등락</th>'
        f'<th style="padding:8px 10px;text-align:left;color:{TEXT_MUTED};font-weight:600;font-size:0.72em;border-bottom:2px solid {INK};">한국 연관</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div></div>'
    )


def md_to_html_market(md: str, quotes: dict) -> str:
    """증시 포스팅 전용 md→HTML"""
    md = SOURCE_TAG_PATTERN.sub("", md)

    lines    = md.split("\n")
    html_out = ["{DASHBOARD}"]
    in_ul    = False
    ul_buf   = []
    cur_sec  = None
    is_lead  = True

    def _heading(text: str) -> str:
        m = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
        if not m:
            return (
                f'<h2 style="font-family:{FONT_DISPLAY};font-size:1.12em;font-weight:700;'
                f'color:{INK};margin:2.4em 0 0.9em;padding-bottom:8px;'
                f'border-bottom:2px solid {STOCK_BLUE};">{text}</h2>'
            )
        num, title_text = m.group(1), m.group(2)
        label_info = STOCK_SECTION_LABELS.get(num)
        label, bar_color = label_info if label_info else ("SEC", STOCK_BLUE)
        total = f"{len(STOCK_SECTION_LABELS):02d}"
        return (
            f'<div style="margin:2.4em 0 0.9em;">'
            f'<div style="display:flex;align-items:baseline;gap:10px;font-family:{FONT_MONO};'
            f'font-size:0.72em;font-weight:600;letter-spacing:0.08em;color:{bar_color};margin-bottom:6px;">'
            f'<span>{num.zfill(2)}/{total}</span><span style="color:{TEXT_MUTED};">{label}</span>'
            f'</div>'
            f'<h2 style="font-family:{FONT_DISPLAY};font-size:1.16em;font-weight:700;color:{INK};'
            f'margin:0;padding-bottom:8px;border-bottom:2px solid {bar_color};">{title_text}</h2>'
            f'</div>'
        )

    def _sector_cards(bullet_lines: list) -> str:
        rows = []
        n = len(bullet_lines)
        for i, line in enumerate(bullet_lines):
            text = re.sub(r"^[-*]\s*", "", line.strip())
            m    = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
            bdr  = f'border-bottom:1px solid {BORDER};' if i < n - 1 else ""
            idx  = f"{i+1:02d}"
            if m:
                term, desc = m.group(1), m.group(2)
                rows.append(
                    f'<div style="display:flex;gap:14px;padding:12px 0;{bdr}">'
                    f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
                    f'font-weight:600;color:{STOCK_BLUE};padding-top:1px;">{idx}</span>'
                    f'<div><div style="font-family:{FONT_DISPLAY};font-size:0.92em;font-weight:700;'
                    f'color:{INK};margin-bottom:4px;">{term}</div>'
                    f'<div style="font-size:0.88em;color:{TEXT_SUB};line-height:1.7;">{desc}</div></div></div>'
                )
            else:
                rows.append(
                    f'<div style="display:flex;gap:14px;padding:12px 0;{bdr}">'
                    f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
                    f'font-weight:600;color:{STOCK_BLUE};padding-top:1px;">{idx}</span>'
                    f'<div style="font-size:0.88em;color:{TEXT_SUB};line-height:1.7;">{text}</div></div>'
                )
        return f'<div style="margin:0.6em 0 1.2em;">{"".join(rows)}</div>'

    def _summary(bullet_lines: list) -> str:
        items = []
        for i, l in enumerate(bullet_lines):
            text = re.sub(r"^[-*]\s*", "", l.strip())
            items.append(
                f'<li style="display:flex;gap:12px;margin-bottom:11px;list-style:none;">'
                f'<span style="flex-shrink:0;font-family:{FONT_MONO};font-size:0.78em;'
                f'font-weight:600;color:{STOCK_BLUE};padding-top:2px;">{i+1:02d}</span>'
                f'<span style="font-size:0.92em;color:#EDEEF1;line-height:1.7;">{text}</span>'
                f'</li>'
            )
        return (
            f'<div style="background:{INK};border-top:3px solid {STOCK_BLUE};'
            f'padding:20px 22px;margin:2em 0;">'
            f'<div style="font-family:{FONT_MONO};font-size:0.72em;font-weight:600;'
            f'letter-spacing:0.1em;color:{STOCK_BLUE};margin-bottom:14px;">SUMMARY</div>'
            f'<ul style="margin:0;padding:0;">{"".join(items)}</ul>'
            f'</div>'
        )

    def flush_ul():
        nonlocal in_ul, ul_buf
        if not ul_buf:
            in_ul = False
            return
        if cur_sec in ("3", "5"):
            html_out.append(_sector_cards(ul_buf))
        elif cur_sec == "7":
            html_out.append(_summary(ul_buf))
        else:
            html_out.append(f'<ul style="padding-left:1.4em;margin:0.6em 0;line-height:1.9;">')
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                html_out.append(f'<li style="margin-bottom:6px;color:{TEXT_SUB};font-size:0.93em;">{t}</li>')
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
            html_out.append(_heading(heading_text))
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
                    html_out.append(
                        f'<p style="margin:0 0 1.8em;padding-left:16px;border-left:3px solid {STOCK_BLUE};'
                        f'line-height:1.85;color:{INK};font-size:1.04em;font-weight:500;">{t}</p>'
                    )
                    is_lead = False
                else:
                    html_out.append(f'<p style="line-height:1.9;margin:0.8em 0;color:{TEXT_SUB};font-size:0.95em;">{t}</p>')
            else:
                if in_ul:
                    flush_ul()

    if in_ul:
        flush_ul()

    body = "\n".join(html_out)
    return (
        f'<div style="font-family:{FONT_BODY};max-width:720px;margin:0 auto;'
        f'color:{TEXT_MAIN};word-break:keep-all;background:#ffffff;padding:4px;">'
        f'{body}'
        f'<div style="margin-top:2em;padding-top:14px;border-top:1px solid {BORDER};'
        f'font-family:{FONT_MONO};font-size:0.72em;color:{TEXT_MUTED};line-height:1.7;">'
        f'본 콘텐츠는 공개 데이터 기반 자동 생성 정보로, 투자 권유가 아닙니다. '
        f'실제 투자 결정은 본인 판단 하에 전문가와 상담 후 진행하시기 바랍니다.'
        f'</div></div>'
    )
