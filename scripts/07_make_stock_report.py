"""
07_market_report.py
미국 증시 수집·분석 → Blogger 자동 발행

개선 사항:
  - 제목에 KST 발행일 날짜 반영
  - 데이터 기준: 미국 정규장 마감 종가 (previousClose 기반으로 정확도 개선)
  - 기준 시각 명시: 미국 현지 날짜 + "NYSE/NASDAQ 정규장 마감 기준"
  - 원/달러 환율 추가 (USDKRW=X)
  - 거래량 추가 (regularMarketVolume)
  - QQQ, SOX 대용 SOXX, XLF 섹터 ETF 추가
  - max_tokens 5000으로 확대 (분석 길이 확보)
  - LLM 프롬프트에 환율·거래량·섹터ETF 반영
"""

from __future__ import annotations
from market_html_builder import build_ticker_dashboard, md_to_html, CSS

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
OPENROUTER_API_KEY      = os.environ.get("OPENROUTER_API_KEY")
BLOGGER_BLOG_ID         = os.environ.get("BLOGGER_BLOG_ID")
BLOGGER_CLIENT_ID       = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET   = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN_2 = os.environ.get("BLOGGER_REFRESH_TOKEN_2")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# ── 시간대 ───────────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
EST = timezone(timedelta(hours=-5))   # 미국 동부 (겨울: EST, 여름: EDT=-4)
DATA_DIR = "data"

# ── 모델 목록 ─────────────────────────────────────────────────────────────────
MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-26b-a4b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-405b-instruct:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

# ── 티커 정의 ─────────────────────────────────────────────────────────────────
TICKERS = {
    # 지수
    "^IXIC":    ("나스닥",        "index"),
    "^GSPC":    ("S&P500",       "index"),
    "^DJI":     ("다우존스",      "index"),
    "^VIX":     ("VIX",          "index"),
    # 매크로
    "DX-Y.NYB": ("달러인덱스",    "macro"),
    "CL=F":     ("WTI유가",       "macro"),
    "GC=F":     ("금선물",        "macro"),
    "USDKRW=X": ("원달러환율",    "macro"),   # ✅ 추가
    # 섹터 ETF
    "QQQ":      ("나스닥100 ETF", "etf"),     # ✅ 추가
    "SOXX":     ("반도체 ETF",    "etf"),     # ✅ 추가
    "XLF":      ("금융 ETF",      "etf"),     # ✅ 추가
    # 핵심 종목
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
    "SOXX":  ["삼성전자", "SK하이닉스", "한미반도체"],
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


# ── 1. 시세 수집 (종가 정확도 개선) ──────────────────────────────────────────

def get_quote(symbol: str) -> Optional[dict]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?interval=1d&range=5d"  # 5일치로 안정적 종가 확보
    )
    raw = fetch(url, timeout=10)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        result = data["chart"]["result"][0]
        meta   = result["meta"]

        # ✅ 종가 정확도 개선: regularMarketPrice(현재가) vs previousClose(전일종가)
        curr_price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")

        if not curr_price or not prev_close:
            return None

        chg_pct = (curr_price - prev_close) / prev_close * 100

        # ✅ 거래량 추가
        volume = meta.get("regularMarketVolume", 0)

        # ✅ 미국 현지 마감 날짜 추출
        ts = meta.get("regularMarketTime", 0)
        if ts:
            market_dt = datetime.fromtimestamp(ts, tz=EST)
            market_date_us = market_dt.strftime("%m/%d")
        else:
            market_date_us = ""

        name, kind = TICKERS.get(symbol, (symbol, "stock"))
        return {
            "symbol":         symbol,
            "name":           name,
            "kind":           kind,
            "price":          round(curr_price, 2),
            "prev":           round(prev_close, 2),
            "chg_pct":        round(chg_pct, 2),
            "volume":         volume,
            "market_date_us": market_date_us,
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
            print(f"  {q['name']:14s} {arrow}{abs(q['chg_pct']):.2f}%  "
                  f"(US {q['market_date_us']})")
        time.sleep(0.3)
    return quotes


def get_us_market_date(quotes: dict) -> str:
    """나스닥 기준 미국 현지 마감 날짜 반환"""
    q = quotes.get("^IXIC") or quotes.get("^GSPC")
    if q and q.get("market_date_us"):
        return q["market_date_us"]
    # 폴백: KST 기준 전날
    now_est = datetime.now(EST)
    return now_est.strftime("%m/%d")


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

def call_ai(prompt: str, max_tokens: int = 5000) -> str:  # ✅ 5000으로 확대
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
            min_len = 5 if max_tokens <= 200 else 100
            if content and len(content.strip()) >= min_len:
                print(f"  [OK] 모델: {model} / {len(content.strip())}자")
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

def fmt_vol(v: int) -> str:
    """거래량 포맷: 1.2억, 34.5M 등"""
    if v >= 100_000_000:
        return f"{v/100_000_000:.1f}억주"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    return str(v)


def build_prompt(quotes: dict, news: list, now_kst: datetime, us_date: str) -> str:
    # 지수
    idx_lines = [f"=== 주요 지수 (미국 현지 {us_date} 정규장 마감 기준) ==="]
    for sym in ["^IXIC", "^GSPC", "^DJI", "^VIX"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            vol  = f" / 거래량:{fmt_vol(q['volume'])}" if q["volume"] else ""
            idx_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%){vol}")

    # 섹터 ETF
    etf_lines = ["\n=== 섹터 ETF ==="]
    for sym in ["QQQ", "SOXX", "XLF"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            etf_lines.append(f"{q['name']}({sym}): {q['price']} ({sign}{q['chg_pct']}%)")

    # 매크로
    macro_lines = ["\n=== 매크로 ==="]
    for sym in ["DX-Y.NYB", "CL=F", "GC=F", "USDKRW=X"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            macro_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%)")

    # 핵심 종목 (거래량 포함)
    stock_lines = ["\n=== 핵심 종목 (거래량 포함) ==="]
    for sym in ["NVDA","AMD","INTC","TSM","AAPL","MSFT","TSLA","AMZN","GOOGL","META"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            kr   = ", ".join(KR_MAP.get(sym, []))
            vol  = fmt_vol(q["volume"]) if q["volume"] else "-"
            line = f"{q['name']}({sym}): {q['price']} ({sign}{q['chg_pct']}%) / 거래량:{vol}"
            if kr:
                line += f"  → KR연관: {kr}"
            stock_lines.append(line)

    # 뉴스
    news_lines = ["\n=== 주요 헤드라인 ==="]
    for i, n in enumerate(news[:18], 1):
        news_lines.append(f"{i}. {n['title']}")
        if n.get("summary"):
            news_lines.append(f"   {n['summary'][:180]}")

    market_text = "\n".join(idx_lines + etf_lines + macro_lines + stock_lines + news_lines)

    # 날짜: KST 발행일 기준, 미국 마감일도 병기
    kst_date = now_kst.strftime("%Y년 %m월 %d일")

    return f"""당신은 20년 경력의 매크로 애널리스트이자 현업 펀드매니저다.
독자는 AI가 작성한 뻔한 글을 극도로 싫어한다.
아래 실제 시장 데이터를 바탕으로 오늘 아침 한국 증시 대응 리포트를 작성하라.

【KST 발행일】{kst_date} (한국 투자자 기준 오늘 아침)
【데이터 기준】미국 현지 {us_date} NYSE/NASDAQ 정규장 마감 (오후 4시 ET)
【데이터】
{market_text}

【작성 원칙 — AI 느낌 완전 제거】
- "알아보겠습니다", "살펴보겠습니다", "정리해보겠습니다" 절대 금지
- "다양한", "혁신적인", "중요한", "주목할 만한" 절대 금지
- "또한", "한편", "따라서", "즉" 문장 연결 금지
- 수치는 위 데이터에 있는 것만 사용. 없으면 정성적으로만 서술
- 문장은 짧고 밀도 있게. 한 문장 하나의 정보
- 현장에서 직접 보고 판단한 것처럼 구체적으로 서술
- 투자 권유 절대 금지. 시황 분석 관점 유지
- 거래량이 평소보다 급증/급감한 종목은 반드시 언급할 것
- 원/달러 환율 변화가 한국 수출주·반도체에 미치는 영향 반드시 언급
- 섹터 ETF(QQQ, SOXX, XLF) 흐름을 섹터 분석에 활용할 것
- 각 섹션 최소 3~4문장 이상 충분히 서술할 것 (총 3000자 이상 목표)

【섹션 구조 — 반드시 준수】

(리드 문단: 헤딩 없이 2~3문장. 오늘 시장의 핵심을 한 방에 요약. 미국 현지 날짜와 KST 발행일 병기)

## 1. 간밤 미국 증시 요약
(나스닥/S&P/다우 방향·수치·핵심 원인. VIX 변화 해석. 정규장 마감 기준임을 명시)

## 2. 핵심 드라이버
(시장을 실제로 움직인 1~2가지 요인 심층 분석. 거래량 급변 종목 언급. 뉴스 헤드라인 기반)

## 3. 섹터별 흐름
- **섹터명**: QQQ/SOXX/XLF ETF 흐름 + 주요 종목 등락과 원인 (bullet 형식, 4~5개)

## 4. 오늘 코스피·코스닥 영향 예측
(코스피·코스닥 각각 분석. 원/달러 환율 영향 반드시 포함. 방향 판단 + 근거 + 주목 섹터)

## 5. 한국 연관 종목 체크
- **종목명**: 미국 모종목 등락 + 거래량 → 한국 영향 (bullet 형식, 6개 이상)

## 6. 오늘의 리스크 & 체크리스트
- 리스크: 예상을 뒤집을 변수 2개
- 체크리스트: 장 시작 전 반드시 확인할 것 4개 (VIX, 환율, 선물, 주요 발표 포함)

## 7. 3줄 요약
- bullet 정확히 3개. 각 bullet 2문장 이상으로 충분히 서술
"""


# ── 5. 사용하지 않는 렌더 함수 (market_html_builder로 이관됨) ──────────────
# render_heading, render_sector_cards, render_summary_box 는
# market_html_builder.py 에서 처리


# ── 6. 제목 생성 ──────────────────────────────────────────────────────────────

def generate_title(quotes: dict, now_kst: datetime, us_date: str):
    # ✅ KST 발행일 기준 날짜
    kst_date_str = now_kst.strftime("%m월 %d일")

    nasdaq = quotes.get("^IXIC")
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

    # 원달러 환율 정보 추가
    krw = quotes.get("USDKRW=X")
    krw_line = f"원달러 {krw['price']:.0f}원" if krw else ""

    prompt = f"""아래 조건으로 블로그 제목 3개를 추천하라.

오늘 날짜(KST): {kst_date_str}
미국 마감일(현지): {us_date}
시장 상황: {nasdaq_line}
{krw_line}

조건:
- 30자 이내
- 제목에 반드시 날짜({kst_date_str}) 포함
- 숫자로 개수 암시 금지 ("3가지", "5포인트" 등)
- 클릭을 유도하되 낚시성 금지
- 한국 투자자 관점

좋은 예시:
- "{kst_date_str} 나스닥 {direction}, 코스피 전망은"
- "미국 증시 {us_date} 마감 — {kst_date_str} 한국 시장 대응"

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

    fallback = f"{kst_date_str} 미국 증시({us_date}) 마감 & 코스피 전망"
    return fallback, [fallback]


# ── 7. Blogger 발행 ───────────────────────────────────────────────────────────

def get_access_token() -> str:
    payload = {
        "client_id":     BLOGGER_CLIENT_ID,
        "client_secret": BLOGGER_CLIENT_SECRET,
        "refresh_token": BLOGGER_REFRESH_TOKEN_2,
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

    if DRY_RUN:
        print("[DRY_RUN] Blogger 발행 없이 HTML 파일만 생성합니다.")

    if not DRY_RUN:
        missing = [
            name for name, val in [
                ("BLOGGER_BLOG_ID",         BLOGGER_BLOG_ID),
                ("BLOGGER_CLIENT_ID",        BLOGGER_CLIENT_ID),
                ("BLOGGER_CLIENT_SECRET",    BLOGGER_CLIENT_SECRET),
                ("BLOGGER_REFRESH_TOKEN_2",  BLOGGER_REFRESH_TOKEN_2),
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

    # ✅ 미국 현지 마감 날짜 추출
    us_date = get_us_market_date(quotes)
    print(f"  미국 마감일(현지): {us_date}")

    # 2) 뉴스 수집
    news = collect_news()

    # 3) 원본 데이터 저장
    with open(f"{DATA_DIR}/market_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(
            {"quotes": quotes, "news": news,
             "us_date": us_date, "generated_at": now_kst.isoformat()},
            f, ensure_ascii=False, indent=2,
        )

    # 4) AI 분석
    print("[3] AI 분석 중...")
    prompt   = build_prompt(quotes, news, now_kst, us_date)
    analysis = call_ai(prompt)  # max_tokens=5000 기본값
    print(f"  분석 완료: {len(analysis)}자")

    # 5) HTML 변환
    dashboard    = build_ticker_dashboard(quotes, now_kst)
    content_html = md_to_html(analysis, quotes)
    content_html = content_html.replace("{DASHBOARD}", dashboard)

    # 6) 제목 생성 (KST 날짜 + 미국 마감일 반영)
    print("[4] 제목 생성 중...")
    final_title, title_candidates = generate_title(quotes, now_kst, us_date)
    print(f"  제목: {final_title}")

    tags = ["미국증시", "코스피전망", "주식시황", "나스닥", "한국증시"]

    # 7) 파일 저장
    market_post = {
        "title":            final_title,
        "title_candidates": title_candidates,
        "category":         "미국증시-한국전망",
        "content_html":     content_html,
        "tags":             ",".join(tags),
        "us_date":          us_date,
        "created_at":       now_kst.isoformat(),
    }
    with open(f"{DATA_DIR}/market_post_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(market_post, f, ensure_ascii=False, indent=2)

    html_path = f"{DATA_DIR}/market_post_{date_str}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content_html)
    print(f"  HTML 저장 → {html_path}")

    if DRY_RUN:
        print(f"[DRY_RUN] 발행 스킵. 생성 파일: {html_path}")
        return

    # 8) Blogger 발행
    print("[5] Blogger 발행 중...")
    result   = post_to_blogger(final_title, content_html, tags)
    post_url = result.get("url", "")
    post_id  = result.get("id", "")
    print(f"[OK] 발행 성공!")
    print(f"     URL: {post_url}")

    with open(f"{DATA_DIR}/market_result_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(
            {"title": final_title, "url": post_url,
             "post_id": post_id, "us_date": us_date,
             "created_at": now_kst.isoformat()},
            f, ensure_ascii=False, indent=2,
        )


if __name__ == "__main__":
    main()
