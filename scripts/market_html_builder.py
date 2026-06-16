"""
market_html_builder.py
07_market_report.py 의 build_ticker_dashboard + md_to_html 교체용
Seeking Alpha / 미래에셋 리서치 스타일
"""
 
import re
 
SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')
 
SECTION_LABELS = {
    "1": ("OPEN",    "badge-open"),
    "2": ("DRIVER",  "badge-driver"),
    "3": ("SECTOR",  "badge-sector"),
    "4": ("KR",      "badge-kr"),
    "5": ("WATCH",   "badge-watch"),
    "6": ("RISK",    "badge-risk"),
    "7": ("SUMMARY", "badge-sum"),
}
 
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
 
CSS = """
<style>
.mr-report * { box-sizing: border-box; margin: 0; padding: 0; }
.mr-report { font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; max-width: 720px; margin: 0 auto; color: #1e293b; word-break: keep-all; }
.mr-date { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; color: #94a3b8; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 10px; }
.mr-date::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }
.mr-headline { font-size: 22px; font-weight: 700; color: #0f172a; line-height: 1.35; margin-bottom: 6px; }
.mr-subline { font-size: 13px; color: #64748b; line-height: 1.6; margin-bottom: 20px; }
.mr-lead { background: #f8fafc; border-left: 3px solid #3b82f6; border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 24px; font-size: 13px; color: #475569; line-height: 1.75; }
.mr-idx-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
.mr-idx-card { background: #f8fafc; border-radius: 8px; padding: 12px 14px; border: 1px solid #e2e8f0; }
.mr-idx-label { font-size: 10px; color: #94a3b8; letter-spacing: 0.6px; text-transform: uppercase; margin-bottom: 4px; }
.mr-idx-val { font-size: 18px; font-weight: 700; color: #0f172a; font-variant-numeric: tabular-nums; }
.mr-idx-chg { font-size: 12px; font-weight: 600; margin-top: 3px; }
.mr-macro-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 24px; }
.mr-mac-card { background: #f8fafc; border-radius: 8px; padding: 10px; border: 1px solid #e2e8f0; text-align: center; }
.mr-mac-label { font-size: 9px; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 3px; }
.mr-mac-val { font-size: 13px; font-weight: 700; color: #0f172a; }
.mr-mac-chg { font-size: 11px; font-weight: 600; margin-top: 2px; }
.mr-up { color: #16a34a; }
.mr-dn { color: #dc2626; }
.mr-section { margin-bottom: 22px; }
.mr-sec-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9; }
.mr-sec-badge { font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; padding: 3px 7px; border-radius: 3px; font-family: monospace; }
.badge-open   { background: #dbeafe; color: #1e40af; }
.badge-driver { background: #dcfce7; color: #166534; }
.badge-sector { background: #fef3c7; color: #92400e; }
.badge-kr     { background: #ede9fe; color: #5b21b6; }
.badge-watch  { background: #f0fdf4; color: #14532d; }
.badge-risk   { background: #fee2e2; color: #991b1b; }
.badge-sum    { background: #f1f5f9; color: #475569; }
.mr-sec-title { font-size: 13px; font-weight: 700; color: #0f172a; }
.mr-body { font-size: 13px; color: #475569; line-height: 1.75; margin-bottom: 8px; }
.mr-bullet-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.mr-bullet-item { display: flex; gap: 8px; font-size: 13px; color: #475569; line-height: 1.65; }
.mr-bullet-dot { width: 4px; height: 4px; border-radius: 50%; background: #cbd5e1; margin-top: 9px; flex-shrink: 0; }
.mr-sector-card { background: #f8fafc; border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; border: 1px solid #e2e8f0; }
.mr-sector-name { font-size: 12px; font-weight: 700; color: #0f172a; margin-bottom: 3px; }
.mr-sector-desc { font-size: 12px; color: #64748b; line-height: 1.5; }
.mr-stock-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.mr-stock-table th { font-size: 10px; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase; padding: 6px 0; text-align: left; border-bottom: 1px solid #e2e8f0; }
.mr-stock-table td { padding: 8px 0; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.mr-sname { font-weight: 700; color: #0f172a; font-size: 12px; }
.mr-ssym { color: #94a3b8; font-size: 10px; margin-left: 4px; }
.mr-sprice { color: #0f172a; font-variant-numeric: tabular-nums; text-align: right; padding-right: 8px; font-size: 12px; }
.mr-chg-pill { display: inline-block; padding: 2px 7px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.mr-chg-up { background: #dcfce7; color: #166534; }
.mr-chg-dn  { background: #fee2e2; color: #991b1b; }
.mr-kr-text { color: #94a3b8; font-size: 10px; }
.mr-summary-box { background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; }
.mr-sum-item { display: flex; gap: 12px; padding: 10px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; color: #475569; line-height: 1.6; }
.mr-sum-item:last-child { border-bottom: none; }
.mr-sum-num { font-size: 10px; font-weight: 700; color: #94a3b8; min-width: 18px; margin-top: 2px; font-family: monospace; }
.mr-disclaimer { font-size: 11px; color: #cbd5e1; line-height: 1.6; padding: 12px 0; border-top: 1px solid #f1f5f9; margin-top: 8px; }
</style>
"""
 
 
def build_ticker_dashboard(quotes: dict, now_kst) -> str:
    date_str = now_kst.strftime("%m월 %d일 %A · 미국 시장 마감")
 
    # 나스닥 방향으로 헤드라인 생성
    nasdaq = quotes.get("^IXIC")
    sp500  = quotes.get("^GSPC")
 
    if nasdaq:
        direction = (
            "급등" if nasdaq["chg_pct"] >= 2 else
            "상승" if nasdaq["chg_pct"] >= 0 else
            "급락" if nasdaq["chg_pct"] <= -2 else
            "하락"
        )
        headline = f"나스닥 {direction} {nasdaq['chg_pct']:+.2f}%"
        if sp500:
            headline += f", S&P500 {sp500['chg_pct']:+.2f}%"
    else:
        headline = "미국 증시 마감 리포트"
 
    # 주요 상승 종목
    stocks = [(s, quotes[s]) for s in ["NVDA","AMD","INTC","TSM","TSLA","AAPL","MSFT","AMZN","GOOGL","META"] if s in quotes]
    top_movers = sorted(stocks, key=lambda x: abs(x[1]["chg_pct"]), reverse=True)[:3]
    subline = " · ".join([f"{q['name']} {q['chg_pct']:+.1f}%" for _, q in top_movers])
 
    def idx_card(sym, label):
        q = quotes.get(sym)
        if not q:
            return ""
        up = q["chg_pct"] >= 0
        cls = "mr-up" if up else "mr-dn"
        arrow = "▲" if up else "▼"
        sign = "+" if up else ""
        return (
            f'<div class="mr-idx-card">'
            f'<div class="mr-idx-label">{label}</div>'
            f'<div class="mr-idx-val">{q["price"]:,.2f}</div>'
            f'<div class="mr-idx-chg {cls}">{arrow} {sign}{q["chg_pct"]}%</div>'
            f'</div>'
        )
 
    def mac_card(sym, label):
        q = quotes.get(sym)
        if not q:
            return ""
        up = q["chg_pct"] >= 0
        cls = "mr-up" if up else "mr-dn"
        arrow = "▲" if up else "▼"
        sign = "+" if up else ""
        return (
            f'<div class="mr-mac-card">'
            f'<div class="mr-mac-label">{label}</div>'
            f'<div class="mr-mac-val">{q["price"]:,.2f}</div>'
            f'<div class="mr-mac-chg {cls}">{arrow} {sign}{q["chg_pct"]}%</div>'
            f'</div>'
        )
 
    idx_html   = idx_card("^IXIC","나스닥") + idx_card("^GSPC","S&P 500") + idx_card("^DJI","다우존스") + idx_card("^VIX","VIX 공포지수")
    macro_html = mac_card("DX-Y.NYB","달러인덱스") + mac_card("CL=F","WTI유가") + mac_card("GC=F","금선물")
 
    stock_rows = ""
    for sym, q in stocks:
        up   = q["chg_pct"] >= 0
        pill = "mr-chg-up" if up else "mr-chg-dn"
        sign = "+" if up else ""
        kr   = ", ".join(KR_MAP.get(sym, []))
        stock_rows += (
            f'<tr>'
            f'<td><span class="mr-sname">{q["name"]}</span><span class="mr-ssym">{sym}</span></td>'
            f'<td class="mr-sprice">{q["price"]:,.2f}</td>'
            f'<td><span class="mr-chg-pill {pill}">{sign}{q["chg_pct"]}%</span></td>'
            f'<td><span class="mr-kr-text">{kr}</span></td>'
            f'</tr>'
        )
 
    return f"""
<div class="mr-date">{date_str}</div>
<div class="mr-headline">{headline}</div>
<div class="mr-subline">{subline}</div>
<div class="mr-idx-grid">{idx_html}</div>
<div class="mr-macro-row">{macro_html}</div>
<table class="mr-stock-table" style="margin-bottom:24px;">
<thead><tr>
  <th>종목</th><th style="text-align:right;padding-right:8px">현재가</th><th>등락</th><th>한국 연관</th>
</tr></thead>
<tbody>{stock_rows}</tbody>
</table>
"""
 
 
def md_to_html(md: str, quotes: dict) -> str:
    # [출처: 데이터] 완전 제거 (노출 방지)
    md = SOURCE_TAG_PATTERN.sub("", md)
 
    lines    = md.split("\n")
    html_out = []
    in_ul    = False
    ul_buf   = []
    cur_sec  = None
    is_lead  = True
 
    def flush_ul():
        nonlocal in_ul, ul_buf
        if not ul_buf:
            in_ul = False
            return
 
        if cur_sec == "7":
            # 3줄 요약 박스
            items = ""
            for i, l in enumerate(ul_buf, 1):
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                items += f'<div class="mr-sum-item"><span class="mr-sum-num">0{i}</span><span>{t}</span></div>'
            html_out.append(f'<div class="mr-summary-box">{items}</div>')
        elif cur_sec in ("3", "5"):
            # 섹터 카드
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                m = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", t)
                if m:
                    name, desc = m.group(1), m.group(2)
                    desc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", desc)
                    desc = SOURCE_TAG_PATTERN.sub("", desc)
                    html_out.append(
                        f'<div class="mr-sector-card">'
                        f'<div class="mr-sector-name">{name}</div>'
                        f'<div class="mr-sector-desc">{desc}</div>'
                        f'</div>'
                    )
                else:
                    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                    t = SOURCE_TAG_PATTERN.sub("", t)
                    html_out.append(
                        f'<div class="mr-sector-card">'
                        f'<div class="mr-sector-desc">{t}</div>'
                        f'</div>'
                    )
        else:
            # 일반 bullet
            items = ""
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                t = SOURCE_TAG_PATTERN.sub("", t)
                items += f'<li class="mr-bullet-item"><span class="mr-bullet-dot"></span><span>{t}</span></li>'
            html_out.append(f'<ul class="mr-bullet-list">{items}</ul>')
 
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
            m = re.match(r"^(\d+)\.\s*(.+)$", heading_text)
            if m:
                num, title = m.group(1), m.group(2)
                label_info = SECTION_LABELS.get(num, ("", "badge-sum"))
                label, badge_cls = label_info
                html_out.append(
                    f'<div class="mr-section">'
                    f'<div class="mr-sec-header">'
                    f'<span class="mr-sec-badge {badge_cls}">{label}</span>'
                    f'<span class="mr-sec-title">{title}</span>'
                    f'</div>'
                )
            else:
                html_out.append(
                    f'<div class="mr-section">'
                    f'<div class="mr-sec-header">'
                    f'<span class="mr-sec-title">{heading_text}</span>'
                    f'</div>'
                )
            cur_sec = m.group(1) if m else None
            is_lead = False
 
        elif re.match(r"^[-*] ", line):
            is_lead = False
            in_ul   = True
            ul_buf.append(line.strip())
 
        else:
            if in_ul and stripped:
                flush_ul()
                html_out.append("</div>")  # close mr-section
 
            if stripped:
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                t = SOURCE_TAG_PATTERN.sub("", t)
 
                if is_lead and cur_sec is None:
                    html_out.append(f'<div class="mr-lead">{t}</div>')
                    is_lead = False
                else:
                    html_out.append(f'<p class="mr-body">{t}</p>')
            else:
                if in_ul:
                    flush_ul()
                    html_out.append("</div>")
 
    if in_ul:
        flush_ul()
        html_out.append("</div>")
 
    body = "\n".join(html_out)
 
    return f"""{CSS}
<div class="mr-report">
 
{{DASHBOARD}}
 
{body}
 
<div class="mr-disclaimer">
  본 콘텐츠는 공개 데이터 기반 자동 생성 정보로, 투자 권유가 아닙니다.
  실제 투자 결정은 본인 판단 하에 전문가와 상담 후 진행하시기 바랍니다.
</div>
 
</div>"""