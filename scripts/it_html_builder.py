"""
it_html_builder.py
market_html_builder.py 와 동일한 디자인 토큰(여백/헤딩/리드박스/요약박스 구조)을 사용하는
IT 리포팅 전용 HTML 빌더.

공유하는 것: 폰트, 카드 패딩/라운드, 헤딩 바+배지 구조, 리드 문단 박스, 요약 박스 구조
다르게 가는 것: 포인트 컬러(시안 계열), 배지 라벨(TECH/TREND/CORE...), 대시보드 없음(대신 메타바)
"""

import re
from datetime import datetime

# ── 공통 디자인 토큰 (market_html_builder.py 와 통일) ────────────────────────
BORDER     = "#e4e9f0"
TEXT_MAIN  = "#1a1a1a"
TEXT_SUB   = "#666e7a"
TEXT_MUTED = "#9ea7b4"
BG_CARD    = "#ffffff"
BG_PAGE    = "#f4f6f9"

# ── IT 전용 포인트 컬러 (시안 계열 — Stock의 블루와 구분되는 형제색) ──────────
ACCENT_MAIN  = "#0e7490"   # 시안 — IT 리포팅의 메인 포인트
ACCENT_LIGHT = "#e6f4f6"   # 시안 옅은 배경
BG_HEADER    = "#eef5f6"   # 헤딩 배경 (Stock의 BG_HEADER #ebf0f8 와 같은 톤 위치)

SECTION_LABELS = {
    "1": ("TECH",    "#0e7490"),
    "2": ("TREND",   "#0b7a4e"),
    "3": ("CORE",    "#b45309"),
    "4": ("IMPACT",  "#6d28d9"),
    "5": ("CASE",    "#b91c1c"),
    "6": ("INSIGHT", "#0369a1"),
    "7": ("SUMMARY", "#1a1a1a"),
}


# ── 상단 메타 바 (Stock의 시세 대시보드 자리를 대신하는 IT 전용 헤더) ─────────

def build_meta_bar(topic: str, tags: list, now_kst: datetime, read_min: int = 4) -> str:
    """
    Stock 리포팅의 build_ticker_dashboard()와 같은 위치에 들어가는
    IT 리포팅 전용 상단 정보 바. 같은 카드 골격(BG_PAGE 배경, BORDER, radius)을 사용.
    """
    time_str = now_kst.strftime("%Y.%m.%d %H:%M KST")

    tag_chips = "".join(
        f'<span style="display:inline-block;background:{BG_CARD};border:1px solid {BORDER};'
        f'color:{TEXT_SUB};font-size:0.78em;padding:4px 11px;border-radius:14px;'
        f'margin-right:6px;margin-bottom:6px;">#{t}</span>'
        for t in tags[:5]
    )

    return (
        f'<div style="background:{BG_PAGE};border-radius:12px;padding:20px;margin-bottom:1.8em;'
        f'border:1px solid {BORDER};">'

        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="display:inline-block;width:4px;height:18px;background:{ACCENT_MAIN};'
        f'border-radius:2px;"></span>'
        f'<span style="font-size:0.95em;font-weight:700;color:{TEXT_MAIN};">기술 분석 리포트</span>'
        f'</div>'
        f'<span style="font-size:0.72em;color:{TEXT_MUTED};">{time_str} · 약 {read_min}분 분량</span>'
        f'</div>'

        f'<div style="font-size:0.72em;font-weight:600;color:{TEXT_SUB};'
        f'margin-bottom:8px;letter-spacing:0.5px;">다루는 주제</div>'
        f'<div style="margin-bottom:2px;">'
        f'<span style="display:inline-block;background:{ACCENT_LIGHT};color:{ACCENT_MAIN};'
        f'font-size:0.92em;font-weight:700;padding:6px 14px;border-radius:6px;margin-bottom:10px;">'
        f'{topic}</span>'
        f'</div>'

        f'<div style="margin-top:10px;">{tag_chips}</div>'

        f'</div>'
    )


# ── 섹션 헤딩 (Stock render_heading 과 동일 구조, 컬러만 분기) ───────────────

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
    bar_color = ACCENT_MAIN
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


# ── 핵심 기술 요소 카드 (Stock render_sector_cards 와 동일 구조) ─────────────

def render_core_cards(bullet_lines: list) -> str:
    accent_colors = [ACCENT_MAIN, "#0b7a4e", "#b45309", "#6d28d9", "#b91c1c"]
    cards = []
    for i, line in enumerate(bullet_lines):
        text   = re.sub(r"^[-*]\s*", "", line.strip())
        m      = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
        accent = accent_colors[i % len(accent_colors)]
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


# ── 3줄 요약 박스 (Stock render_summary_box 와 동일 구조) ────────────────────

def _strip_bullet(line: str) -> str:
    return re.sub(r"^[-*]\s*", "", line.strip())


def render_summary_box(bullet_lines: list) -> str:
    items = []
    icons = ["①", "②", "③"]
    for i, l in enumerate(bullet_lines):
        icon = icons[i] if i < len(icons) else "•"
        items.append(
            f'<li style="display:flex;gap:10px;margin-bottom:10px;list-style:none;">'
            f'<span style="flex-shrink:0;font-size:0.9em;font-weight:700;color:{ACCENT_MAIN};">'
            f'{icon}</span>'
            f'<span style="font-size:0.92em;color:{TEXT_MAIN};line-height:1.7;">'
            f'{_strip_bullet(l)}</span>'
            f'</li>'
        )
    items_html = "".join(items)
    return (
        f'<div style="background:{ACCENT_LIGHT};border:1px solid #bfe1e5;'
        f'border-radius:10px;padding:18px 20px;margin:1.8em 0;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
        f'<span style="display:inline-block;width:4px;height:16px;background:{ACCENT_MAIN};'
        f'border-radius:2px;"></span>'
        f'<span style="font-size:0.82em;font-weight:700;color:{ACCENT_MAIN};'
        f'letter-spacing:0.5px;">핵심 요약</span>'
        f'</div>'
        f'<ul style="margin:0;padding:0;">{items_html}</ul>'
        f'</div>'
    )


# ── 참고 기사 박스 ────────────────────────────────────────────────────────────

def render_references(articles: list) -> str:
    if not articles:
        return ""
    src_label_map = {
        "google_news":   "Google News",
        "yahoo_finance": "Yahoo Finance",
        "hacker_news":   "Hacker News",
    }
    items = []
    for a in articles[:8]:
        src_label = src_label_map.get(a.get("source", ""), a.get("source", ""))
        items.append(
            f'<li style="margin-bottom:7px;line-height:1.6;font-size:0.88em;">'
            f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
            f'style="color:{ACCENT_MAIN};text-decoration:none;">{a["title"]}</a>'
            f'<span style="color:{TEXT_MUTED};font-size:0.85em;"> — {src_label}</span></li>'
        )
    return (
        f'<div style="margin-top:2em;padding:16px 18px;background:{BG_PAGE};'
        f'border:1px solid {BORDER};border-radius:8px;">'
        f'<div style="font-size:0.72em;font-weight:700;color:{TEXT_MUTED};'
        f'letter-spacing:1px;margin-bottom:10px;">참고 기사</div>'
        f'<ul style="padding-left:1.3em;margin:0;">{"".join(items)}</ul>'
        f'</div>'
    )


# ── 대표 이미지 (기존 build_hero_image_html 을 토큰 통일해서 재구성) ─────────

def render_hero_image(image: dict) -> str:
    if not image:
        return ""
    return (
        f'<div style="margin:0 0 1.8em;border-radius:10px;overflow:hidden;'
        f'border:1px solid {BORDER};">'
        f'<img src="{image["url"]}" alt="{image.get("alt","")}" '
        f'style="width:100%;max-height:380px;object-fit:cover;display:block;" loading="lazy" />'
        f'<p style="font-size:0.74em;color:{TEXT_MUTED};margin:6px 10px;text-align:right;">'
        f'Photo by <a href="{image["author_url"]}?utm_source=mystacklog&utm_medium=referral" '
        f'target="_blank" rel="noopener noreferrer" style="color:{TEXT_MUTED};">{image["author"]}</a>'
        f' on <a href="https://unsplash.com?utm_source=mystacklog&utm_medium=referral" '
        f'target="_blank" rel="noopener noreferrer" style="color:{TEXT_MUTED};">Unsplash</a>'
        f'</p></div>'
    )


# ── 구성도 (mermaid) 래퍼 ─────────────────────────────────────────────────────

def render_diagram(diagram_url: str, topic: str) -> str:
    if not diagram_url:
        return ""
    return (
        f'<div style="text-align:center;margin:1.6em 0;padding:16px;'
        f'background:{BG_PAGE};border:1px solid {BORDER};border-radius:10px;">'
        f'<img src="{diagram_url}" alt="{topic} 구조도" '
        f'style="max-width:100%;border-radius:6px;" loading="lazy" />'
        f'<p style="font-size:0.78em;color:{TEXT_MUTED};margin-top:10px;">{topic} 핵심 구조도</p>'
        f'</div>'
    )


# ── 출처 태그 → 각주 링크 ──────────────────────────────────────────────────

SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def convert_source_tags(text: str, articles: list) -> str:
    title_to_url = {a["title"].strip(): a.get("link", "") for a in articles}

    def replace_tag(match):
        inner = re.sub(r'^\[출처\s*:\s*', '', match.group()).rstrip(']').strip()
        url = title_to_url.get(inner, "")
        if not url:
            for title, u in title_to_url.items():
                if inner[:20] in title or title[:20] in inner:
                    url = u
                    break
        if url:
            return (
                f'<sup style="font-size:0.74em;color:{ACCENT_MAIN};">'
                f'[<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="color:{ACCENT_MAIN};text-decoration:none;">{inner[:30]}</a>]</sup>'
            )
        return f'<sup style="font-size:0.74em;color:{TEXT_MUTED};">[{inner[:30]}]</sup>'

    return SOURCE_TAG_PATTERN.sub(replace_tag, text)


# ── 마크다운 → HTML 변환 (Stock md_to_html 과 동일 파이프라인 구조) ──────────

def md_to_html(md: str, articles: list = None) -> str:
    articles = articles or []
    md = convert_source_tags(md, articles)

    lines    = md.split("\n")
    html_out = ["{META_BAR}"]   # 메타바 플레이스홀더 — Stock의 {DASHBOARD}와 같은 위치
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
            html_out.append('<ul style="padding-left:1.4em;margin:0.6em 0;line-height:1.9;">')
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
                t = re.sub(
                    r"`(.+?)`",
                    f'<code style="background:{BG_PAGE};padding:2px 6px;'
                    f'border-radius:3px;font-size:0.9em;">\\1</code>',
                    t,
                )
                if is_lead and cur_sec is None:
                    html_out.append(
                        f'<div style="background:{BG_HEADER};border-left:4px solid {ACCENT_MAIN};'
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
        f'<div style="margin-top:2em;padding:12px 16px;background:{BG_PAGE};'
        f'border:1px solid {BORDER};border-radius:6px;'
        f'font-size:0.78em;color:{TEXT_MUTED};line-height:1.7;">'
        f'본 콘텐츠는 IT 기술 정보 제공 목적으로 작성되었습니다. 투자 판단의 근거로 사용하지 마시기 바랍니다.'
        f'</div>'
        f'</div>'
    )
