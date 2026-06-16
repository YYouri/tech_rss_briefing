"""
07_market_report.py
무료 데이터로 미국 증시를 수집·분석하고
기존 블로그 포스팅과 동일한 HTML 스타일로 Blogger에 발행한다.

데이터 소스 (전부 무료·무인증):
  - Yahoo Finance JSON API  → 나스닥/S&P500/다우/VIX/유가/금/달러
  - Yahoo Finance RSS       → 핵심 종목 뉴스
  - Google News RSS         → 미국 시장 뉴스

수정 사항:
  - DRY_RUN 환경변수 지원 (Blogger 발행 없이 HTML만 생성)
  - bytes | None → Optional[bytes] (Python 3.9 호환)
  - dict | None  → Optional[dict]  (Python 3.9 호환)
  - render_summary_box 정규식 버그 수정 (f-string 내 백슬래시 제거)
  - Blogger 발행 전 필수 환경변수 사전 검증으로 이동
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import html as html_lib
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser

# ── 환경변수 ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY    = os.environ.get("OPENROUTER_API_KEY")
BLOGGER_BLOG_ID       = os.environ.get("BLOGGER_BLOG_ID")
BLOGGER_CLIENT_ID     = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN_2")

# ✅ DRY_RUN: "true" 이면 Blogger 발행 없이 HTML 파일만 저장
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# ── 상수 ─────────────────────────────────────────────────────────────────────
KST      = timezone(timedelta(hours=9))
DATA_DIR = "data"

# 2026-06-16 기준 OpenRouter 무료 모델 (PDF 확인)
MODELS = [
    "openai/gpt-oss-120b:free",           # gpt-oss 계열, 안정적
    "google/gemma-4-26b-a4b:free",        # 262K context, MoE 고품질
    "qwen/qwen3-next-80b-a3b-instruct:free",  # 262K context, 멀티링궐 강점
    "meta-llama/llama-3.3-70b-instruct:free", # 131K, 검증된 70B
    "nousresearch/hermes-3-405b-instruct:free", # 131K, 고품질 파인튠
    "openai/gpt-oss-20b:free",            # 소형 폴백
    "meta-llama/llama-3.2-3b-instruct:free",  # 최후 폴백
]

TICKERS = {
    "^IXIC":    ("나스닥",        "index"),
    "^GSPC":    ("S&P500",       "index"),
    "^DJI":     ("다우존스",      "index"),
    "^VIX":     ("VIX",          "index"),
    "DX-Y.NYB": ("달러인덱스",    "macro"),
    "CL=F":     ("WTI유가",       "macro"),
    "GC=F":     ("금선물",        "macro"),
    "NVDA":     ("엔비디아",      "stock"),
    "AMD":      ("AMD",          "stock"),
    "INTC":     ("인텔",         "stock"),
    "TSM":      ("TSMC",         "stock"),
    "AAPL":     ("애플",         "stock"),
    "MSFT":     ("마이크로소프트", "stock"),
    "TSLA":     ("테슬라",        "stock"),
    "AMZN":     ("아마존",        "stock"),
    "GOOGL":    ("알파벳",        "stock"),
    "META":     ("메타",          "stock"),
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

SECTION_LABELS = {
    "1": ("OPEN",    "#0052cc"),
    "2": ("DRIVER",  "#057a55"),
    "3": ("SECTOR",  "#b45309"),
    "4": ("KR",      "#6d28d9"),
    "5": ("WATCH",   "#b91c1c"),
    "6": ("RISK",    "#0e7490"),
    "7": ("SUMMARY", "#1e293b"),
}


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    text = html_lib.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ✅ bytes | None → Optional[bytes] (Python 3.9 호환)
def fetch(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MarketBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  [WARN] fetch 실패: {url[:60]} → {e}")
        return None


# ── 1. 시세 수집 ──────────────────────────────────────────────────────────────

# ✅ dict | None → Optional[dict] (Python 3.9 호환)
def get_quote(symbol: str) -> Optional[dict]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?interval=1d&range=2d"
    )
    raw = fetch(url, timeout=10)
    if not raw:
        return None
    try:
        data       = json.loads(raw)
        meta       = data["chart"]["result"][0]["meta"]
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        curr_price = meta.get("regularMarketPrice")
        if not curr_price or not prev_close:
            return None
        chg_pct = (curr_price - prev_close) / prev_close * 100
        name, kind = TICKERS.get(symbol, (symbol, "stock"))
        return {
            "symbol":  symbol,
            "name":    name,
            "kind":    kind,
            "price":   round(curr_price, 2),
            "prev":    round(prev_close, 2),
            "chg_pct": round(chg_pct, 2),
        }
    except Exception as e:
        print(f"  [WARN] 파싱 실패 {symbol}: {e}")
        return None


def collect_quotes() -> dict:
    print("[1] 시세 수집...")
    quotes = {}
    for sym in TICKERS:
        q = get_quote(sym)
        if q:
            quotes[sym] = q
            arrow = "▲" if q["chg_pct"] >= 0 else "▼"
            print(f"  {q['name']:14s} {arrow}{abs(q['chg_pct']):.2f}%")
        time.sleep(0.3)
    return quotes


# ── 2. 뉴스 수집 ─────────────────────────────────────────────────────────────

NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMD&region=US&lang=en-US",
    "https://news.google.com/rss/search?q=US+stock+market+today&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=nasdaq+SP500+wall+street&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Federal+Reserve+economy+2026&hl=en-US&gl=US&ceid=US:en",
]


def collect_news() -> list:
    print("[2] 뉴스 수집...")
    seen, articles = set(), []
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title   = clean(entry.get("title", ""))
                summary = clean(entry.get("summary", ""))[:400]
                link    = entry.get("link", "")
                if title and title not in seen:
                    seen.add(title)
                    articles.append({"title": title, "summary": summary, "link": link})
        except Exception as e:
            print(f"  [WARN] RSS 실패: {e}")
        time.sleep(0.4)
    print(f"  뉴스 {len(articles)}건")
    return articles[:25]


# ── 3. LLM 호출 ──────────────────────────────────────────────────────────────

def call_ai(prompt: str, max_tokens: int = 3500) -> str:
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY 없음")
        sys.exit(1)

    for model in MODELS:
        payload = {
            "model":       model,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": 0.3,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req  = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json; charset=utf-8",
                "HTTP-Referer":  "https://github.com",
                "X-Title":       "Tech Blog",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                result = json.loads(r.read().decode("utf-8"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            # max_tokens 200 이하(제목 등 단답)는 최소 5자, 그 외 100자 기준
            min_len = 5 if max_tokens <= 200 else 100
            if content and len(content.strip()) >= min_len:
                print(f"  [OK] 모델: {model}")
                return content.strip()
            print(f"  [WARN] {model} 응답 부실 ({len((content or '').strip())}자)")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(f"  [WARN] {model} HTTP {e.code}: {body[:120]}")
        except Exception as e:
            print(f"  [WARN] {model}: {e}")
        time.sleep(2)

    print("[ERROR] 모든 모델 실패")
    sys.exit(1)


# ── 4. 프롬프트 생성 ──────────────────────────────────────────────────────────

def build_prompt(quotes: dict, news: list, now_kst: datetime) -> str:
    idx_lines = ["=== 주요 지수 ==="]
    for sym in ["^IXIC", "^GSPC", "^DJI", "^VIX"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            idx_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%)")

    macro_lines = ["\n=== 매크로 ==="]
    for sym in ["DX-Y.NYB", "CL=F", "GC=F"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            macro_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%)")

    stock_lines = ["\n=== 핵심 종목 ==="]
    for sym in ["NVDA", "AMD", "INTC", "TSM", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            kr   = ", ".join(KR_MAP.get(sym, []))
            line = f"{q['name']}({sym}): {q['price']} ({sign}{q['chg_pct']}%)"
            if kr:
                line += f"  → KR연관: {kr}"
            stock_lines.append(line)

    news_lines = ["\n=== 주요 헤드라인 ==="]
    for i, n in enumerate(news[:18], 1):
        news_lines.append(f"{i}. {n['title']}")
        if n.get("summary"):
            news_lines.append(f"   {n['summary'][:180]}")

    market_text = "\n".join(idx_lines + macro_lines + stock_lines + news_lines)
    date_str    = now_kst.strftime("%Y년 %m월 %d일")

    return f"""당신은 20년 경력의 매크로 애널리스트이자 현업 펀드매니저다.
독자는 AI가 작성한 뻔한 글을 극도로 싫어한다.
아래 실제 시장 데이터를 바탕으로 오늘 아침 한국 증시 대응 리포트를 작성하라.

【분석일】{date_str}
【데이터】
{market_text}

【작성 원칙 — AI 느낌 완전 제거】
- "알아보겠습니다", "살펴보겠습니다", "정리해보겠습니다" 절대 금지
- "다양한", "혁신적인", "중요한", "주목할 만한" 절대 금지
- "또한", "한편", "따라서", "즉" 문장 연결 금지
- 수치는 위 데이터에 있는 것만 사용. 없으면 정성적으로만 서술
- 수치 사용 시 반드시 문장 끝에 [출처: 데이터] 태깅
- 문장은 짧고 밀도 있게. 한 문장 하나의 정보
- 현장에서 직접 보고 판단한 것처럼 구체적으로 서술
- 투자 권유 절대 금지. 시황 분석 관점 유지
- 한국 시장 연결: 미국 시장의 움직임이 한국의 어떤 종목(반도체, 2차전지 등)과 어떤 논리로 연결되는지 반드시 짚어주십시오. 

【섹션 구조 — 반드시 준수】

(리드 문단: 헤딩 없이 2~3문장. 오늘 시장의 핵심을 한 방에 요약)

## 1. 간밤 미국 증시 요약
(나스닥/S&P/다우 방향과 핵심 원인. 구체적 수치와 종목 언급)

## 2. 핵심 드라이버
(오늘 시장을 실제로 움직인 1~2가지 요인 심층 분석. 뉴스 헤드라인 기반)

## 3. 섹터별 흐름
- **섹터명**: 주요 종목 등락과 원인 (bullet 형식, 3~5개)

## 4. 오늘 코스피·코스닥 영향 예측
(코스피와 코스닥를 각각 분석. 방향 판단 + 근거 + 주목 섹터)

## 5. 한국 연관 종목 체크
- **종목명**: 미국 모종목 등락 → 한국 영향 (bullet 형식)

## 6. 오늘의 리스크 & 체크리스트
(예상을 뒤집을 변수 2개 + 장 시작 전 확인할 것 3개. bullet 형식)

## 7. 3줄 요약
- bullet 정확히 3개
"""


# ── 5. HTML 변환 ──────────────────────────────────────────────────────────────

SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def render_heading(text: str) -> str:
    m = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
    if not m:
        return (
            f'<h2 style="font-size:1.15em;font-weight:700;color:#0f172a;'
            f'margin:2.4em 0 0.9em;padding-left:14px;'
            f'border-left:4px solid #cbd5e1;">'
            f'{text}</h2>'
        )
    num, title_text = m.group(1), m.group(2)
    label_info = SECTION_LABELS.get(num)
    badge = ""
    bar_color = "#cbd5e1"
    if label_info:
        label, color = label_info
        bar_color = color
        badge = (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'font-size:0.68em;font-weight:800;padding:2px 8px;border-radius:3px;'
            f'margin-right:10px;vertical-align:middle;letter-spacing:1px;'
            f'font-family:monospace;">'
            f'{label}</span>'
        )
    return (
        f'<h2 style="font-size:1.15em;font-weight:700;color:#0f172a;'
        f'margin:2.4em 0 0.9em;padding-left:14px;'
        f'border-left:4px solid {bar_color};">'
        f'{badge}{title_text}</h2>'
    )


def render_sector_cards(bullet_lines: list) -> str:
    cards = []
    accent_colors = ["#0052cc", "#057a55", "#b45309", "#6d28d9", "#b91c1c"]
    for i, line in enumerate(bullet_lines):
        text = re.sub(r"^[-*]\s*", "", line.strip())
        m = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
        accent = accent_colors[i % len(accent_colors)]
        if m:
            term, desc = m.group(1), m.group(2)
            cards.append(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                f'padding:14px 16px;border-left:3px solid {accent};">'
                f'<strong style="color:{accent};font-size:0.9em;letter-spacing:0.3px;">{term}</strong>'
                f'<p style="margin:6px 0 0;font-size:0.88em;color:#475569;line-height:1.65;">{desc}</p>'
                '</div>'
            )
        else:
            cards.append(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                f'padding:14px 16px;border-left:3px solid {accent};">'
                f'<p style="margin:0;font-size:0.88em;color:#475569;line-height:1.65;">{text}</p>'
                '</div>'
            )
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:1em 0;">'
        + "".join(f'<div>{c}</div>' for c in cards)
        + "</div>"
    )


def _strip_bullet(line: str) -> str:
    """bullet 기호(- *) 제거 — f-string 안에서 백슬래시 사용 불가 문제 회피"""
    return re.sub(r"^[-*]\s*", "", line.strip())


def render_summary_box(bullet_lines: list) -> str:
    items = "".join(
        f'<li style="margin-bottom:10px;line-height:1.75;color:#e2e8f0;font-size:0.95em;">'
        f'{_strip_bullet(l)}</li>'
        for l in bullet_lines
    )
    return (
        '<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);'
        'border-radius:12px;padding:20px 24px;margin:1.8em 0;">'
        '<p style="font-weight:700;color:#94a3b8;margin:0 0 12px;font-size:0.75em;'
        'letter-spacing:2px;text-transform:uppercase;font-family:monospace;">SUMMARY</p>'
        f'<ul style="padding-left:1.3em;margin:0;">{items}</ul>'
        '</div>'
    )


def build_ticker_dashboard(quotes: dict) -> str:
    def idx_card(q: dict) -> str:
        up    = q["chg_pct"] >= 0
        color = "#22c55e" if up else "#f87171"
        sign  = "+" if up else ""
        arrow = "\u25b2" if up else "\u25bc"
        bg    = "rgba(34,197,94,0.10)" if up else "rgba(248,113,113,0.10)"
        return (
            f'<div style="background:#1e293b;border-radius:10px;padding:16px 14px;'
            f'flex:1;min-width:110px;text-align:center;border:1px solid #334155;">'
            f'<div style="font-size:0.72em;color:#94a3b8;margin-bottom:6px;letter-spacing:0.5px;">{q["name"]}</div>'
            f'<div style="font-size:1.2em;font-weight:800;color:#f1f5f9;font-variant-numeric:tabular-nums;">'
            f'{q["price"]:,.2f}</div>'
            f'<div style="display:inline-block;margin-top:6px;padding:2px 8px;background:{bg};border-radius:20px;">'
            f'<span style="font-size:0.8em;font-weight:700;color:{color};">{arrow} {sign}{q["chg_pct"]}%</span></div>'
            f'</div>'
        )

    def macro_card(q: dict) -> str:
        up    = q["chg_pct"] >= 0
        color = "#22c55e" if up else "#f87171"
        sign  = "+" if up else ""
        arrow = "\u25b2" if up else "\u25bc"
        return (
            f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;'
            f'padding:14px 16px;flex:1;min-width:100px;text-align:center;">'
            f'<div style="font-size:0.72em;color:#64748b;margin-bottom:4px;">{q["name"]}</div>'
            f'<div style="font-size:1.05em;font-weight:700;color:#cbd5e1;">{q["price"]:,.2f}</div>'
            f'<div style="font-size:0.8em;font-weight:600;color:{color};margin-top:3px;">{arrow} {sign}{q["chg_pct"]}%</div>'
            f'</div>'
        )

    idx_cards   = [idx_card(quotes[s])   for s in ["^IXIC","^GSPC","^DJI","^VIX"]    if s in quotes]
    macro_cards = [macro_card(quotes[s]) for s in ["DX-Y.NYB","CL=F","GC=F"]          if s in quotes]

    rows = []
    for sym in ["NVDA","AMD","INTC","TSM","AAPL","MSFT","TSLA","AMZN","GOOGL","META"]:
        q = quotes.get(sym)
        if not q:
            continue
        up    = q["chg_pct"] >= 0
        color = "#22c55e" if up else "#f87171"
        sign  = "+" if up else ""
        bg    = "rgba(34,197,94,0.07)" if up else "rgba(248,113,113,0.07)"
        kr    = ", ".join(KR_MAP.get(sym, ["-"]))
        rows.append(
            f'<tr style="border-bottom:1px solid #1e293b;">'
            f'<td style="padding:10px 14px;white-space:nowrap;">'
            f'<span style="font-weight:700;color:#e2e8f0;font-size:0.9em;">{q["name"]}</span>'
            f'<span style="color:#475569;font-size:0.75em;margin-left:6px;">{sym}</span></td>'
            f'<td style="padding:10px 14px;text-align:right;font-variant-numeric:tabular-nums;'
            f'color:#cbd5e1;font-size:0.88em;font-weight:600;">{q["price"]:,.2f}</td>'
            f'<td style="padding:10px 14px;text-align:right;">'
            f'<span style="display:inline-block;padding:2px 8px;background:{bg};'
            f'border-radius:20px;font-size:0.8em;font-weight:700;color:{color};">{sign}{q["chg_pct"]}%</span></td>'
            f'<td style="padding:10px 14px;color:#64748b;font-size:0.8em;">{kr}</td>'
            f'</tr>'
        )

    idx_html   = "".join(idx_cards)
    macro_html = "".join(macro_cards)
    rows_html  = "".join(rows)

    return (
        '<div style="background:#0f172a;border-radius:14px;padding:22px;margin-bottom:2em;border:1px solid #1e293b;">'
        '<p style="font-size:0.7em;font-weight:700;color:#475569;letter-spacing:2.5px;'
        'text-transform:uppercase;margin:0 0 14px;font-family:monospace;">MAJOR INDEX</p>'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px;">{idx_html}</div>'
        '<p style="font-size:0.7em;font-weight:700;color:#475569;letter-spacing:2.5px;'
        'text-transform:uppercase;margin:0 0 12px;font-family:monospace;">MACRO</p>'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px;">{macro_html}</div>'
        '<p style="font-size:0.7em;font-weight:700;color:#475569;letter-spacing:2.5px;'
        'text-transform:uppercase;margin:0 0 10px;font-family:monospace;">US STOCKS &amp; KR IMPACT</p>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.88em;background:#0f172a;">'
        '<thead><tr style="border-bottom:2px solid #334155;">'
        '<th style="padding:8px 14px;text-align:left;color:#475569;font-weight:600;font-size:0.8em;">종목</th>'
        '<th style="padding:8px 14px;text-align:right;color:#475569;font-weight:600;font-size:0.8em;">현재가</th>'
        '<th style="padding:8px 14px;text-align:right;color:#475569;font-weight:600;font-size:0.8em;">등락</th>'
        '<th style="padding:8px 14px;text-align:left;color:#475569;font-weight:600;font-size:0.8em;">한국 연관</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div></div>'
    )



def md_to_html(md: str, quotes: dict) -> str:
    md = SOURCE_TAG_PATTERN.sub(
        lambda m: f'<sup style="font-size:0.75em;color:#888;">{m.group()}</sup>', md
    )

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
        if cur_sec in ("3", "5"):
            html_out.append(render_sector_cards(ul_buf))
        elif cur_sec == "7":
            html_out.append(render_summary_box(ul_buf))
        else:
            html_out.append('<ul style="padding-left:1.5em;line-height:2.0;margin:0.5em 0;">')
            for l in ul_buf:
                t = re.sub(r"^[-*]\s*", "", l.strip())
                t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
                html_out.append(f'  <li style="margin-bottom:6px;">{t}</li>')
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
                    r'<code style="background:#f1f1f1;padding:2px 6px;'
                    r'border-radius:3px;font-size:0.9em;">\1</code>',
                    t,
                )
                if is_lead and cur_sec is None:
                    html_out.append(
                        f'<p style="line-height:1.85;margin:0 0 1.8em;color:#334155;'
                        f'font-size:1.05em;padding:16px 20px;'
                        f'background:#f1f5f9;border-radius:8px;'
                        f'border-left:4px solid #0052cc;">{t}</p>'
                    )
                    is_lead = False
                else:
                    html_out.append(
                        f'<p style="line-height:1.95;margin:0.9em 0;'
                        f'color:#333;font-size:1em;">{t}</p>'
                    )
            else:
                if in_ul:
                    flush_ul()

    if in_ul:
        flush_ul()

    body = "\n".join(html_out)

    return f"""<div style="font-family:'Noto Sans KR','Malgun Gothic',sans-serif;max-width:720px;margin:0 auto;color:#1e293b;word-break:keep-all;background:#f8fafc;padding:0;border-radius:16px;">

{build_ticker_dashboard(quotes)}

<div style="padding:0 4px;">
{body}
</div>

<div style="margin-top:2em;padding:14px 18px;background:#f1f5f9;border-radius:8px;
font-size:0.8em;color:#94a3b8;line-height:1.8;border-left:3px solid #cbd5e1;">
본 콘텐츠는 공개 데이터 기반 자동 생성 정보로, 투자 권유가 아닙니다. 실제 투자 결정은 본인 판단 하에 전문가와 상담 후 진행하시기 바랍니다.
</div>

</div>"""


# ── 6. 제목 생성 ──────────────────────────────────────────────────────────────

def generate_title(quotes: dict, now_kst: datetime):
    date_str = now_kst.strftime("%m월 %d일")
    nasdaq   = quotes.get("^IXIC")
    if nasdaq:
        direction = (
            "급등" if nasdaq["chg_pct"] >= 2 else
            "상승" if nasdaq["chg_pct"] >= 0 else
            "급락" if nasdaq["chg_pct"] <= -2 else
            "하락"
        )
        nasdaq_line = f"나스닥 {direction}({nasdaq['chg_pct']:+.2f}%)"
    else:
        nasdaq_line = "미국 증시 마감"

    prompt = f"""아래 조건으로 블로그 제목 3개를 추천하라.

오늘 날짜: {date_str}
시장 상황: {nasdaq_line}

조건:
- 30자 이내
- 숫자로 개수 암시 금지 ("3가지", "5포인트" 등)
- 클릭을 유도하되 낚시성 금지
- 한국 투자자 관점

JSON만 출력:
{{"titles": ["제목1", "제목2", "제목3"]}}
"""
    raw   = call_ai(prompt, max_tokens=200)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            titles = result.get("titles", [])
            if titles:
                return titles[0], titles
        except Exception:
            pass

    fallback = f"{date_str} 미국 증시 마감 & 오늘 코스피 전망"
    return fallback, [fallback]


# ── 7. Blogger 발행 ───────────────────────────────────────────────────────────

def get_access_token() -> str:
    payload = {
        "client_id":     BLOGGER_CLIENT_ID,
        "client_secret": BLOGGER_CLIENT_SECRET,
        "refresh_token": BLOGGER_REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode("utf-8"))
        token = result.get("access_token")
        if not token:
            print(f"[ERROR] Access Token 발급 실패: {result}")
            sys.exit(1)
        return token
    except Exception as e:
        print(f"[ERROR] Access Token 발급 실패: {e}")
        sys.exit(1)


def post_to_blogger(title: str, content: str, labels: list) -> dict:
    access_token = get_access_token()
    payload = {"title": title, "content": content, "labels": labels}
    data    = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req     = urllib.request.Request(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/",
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[ERROR] Blogger API HTTP {e.code}: {body[:400]}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Blogger API 실패: {e}")
        sys.exit(1)


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    now_kst  = datetime.now(KST)
    date_str = now_kst.strftime("%Y-%m-%d")

    os.makedirs(DATA_DIR, exist_ok=True)

    # ✅ DRY_RUN 모드 안내
    if DRY_RUN:
        print("[DRY_RUN] Blogger 발행 없이 HTML 파일만 생성합니다.")

    # ✅ Blogger 환경변수 사전 검증 (DRY_RUN 아닐 때만)
    if not DRY_RUN:
        missing = [
            name for name, val in [
                ("BLOGGER_BLOG_ID",         BLOGGER_BLOG_ID),
                ("BLOGGER_CLIENT_ID",        BLOGGER_CLIENT_ID),
                ("BLOGGER_CLIENT_SECRET",    BLOGGER_CLIENT_SECRET),
                ("BLOGGER_REFRESH_TOKEN_2",  BLOGGER_REFRESH_TOKEN),
            ]
            if not val
        ]
        if missing:
            print(f"[ERROR] 필수 환경변수 누락: {', '.join(missing)}")
            sys.exit(1)

    # 1) 시세 수집
    quotes = collect_quotes()
    if not quotes:
        print("[ERROR] 시세 수집 실패")
        sys.exit(1)

    # 2) 뉴스 수집
    news = collect_news()

    # 3) 원본 데이터 저장
    with open(f"{DATA_DIR}/market_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(
            {"quotes": quotes, "news": news, "generated_at": now_kst.isoformat()},
            f, ensure_ascii=False, indent=2,
        )

    # 4) AI 분석
    print("[3] AI 분석 중...")
    prompt   = build_prompt(quotes, news, now_kst)
    analysis = call_ai(prompt)
    print(f"  분석 완료: {len(analysis)}자")

    # 5) HTML 변환
    content_html = md_to_html(analysis, quotes)

    # 6) 제목 생성
    print("[4] 제목 생성 중...")
    final_title, title_candidates = generate_title(quotes, now_kst)
    print(f"  제목: {final_title}")

    tags = ["미국증시", "코스피전망", "주식시황", "나스닥", "한국증시"]

    # 7) HTML 파일 저장 (DRY_RUN 포함 항상 저장)
    market_post = {
        "title":            final_title,
        "title_candidates": title_candidates,
        "category":         "미국증시-한국전망",
        "content_html":     content_html,
        "tags":             ",".join(tags),
        "created_at":       now_kst.isoformat(),
    }
    post_json_path = f"{DATA_DIR}/market_post_{date_str}.json"
    with open(post_json_path, "w", encoding="utf-8") as f:
        json.dump(market_post, f, ensure_ascii=False, indent=2)

    html_path = f"{DATA_DIR}/market_post_{date_str}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content_html)

    print(f"  HTML 저장 → {html_path}")

    # 8) Blogger 발행 (DRY_RUN 이면 스킵)
    if DRY_RUN:
        print(f"[DRY_RUN] 발행 스킵. 생성 파일: {html_path}")
        return

    print("[5] Blogger 발행 중...")
    result   = post_to_blogger(final_title, content_html, tags)
    post_url = result.get("url", "")
    post_id  = result.get("id", "")

    print(f"[OK] 발행 성공!")
    print(f"     URL: {post_url}")

    with open(f"{DATA_DIR}/market_result_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "title":      final_title,
                "url":        post_url,
                "post_id":    post_id,
                "created_at": now_kst.isoformat(),
            },
            f, ensure_ascii=False, indent=2,
        )


if __name__ == "__main__":
    main()
