"""
07_market_report.py
미국 증시 수집·분석 → Blogger 자동 발행
it_html_builder.py 의 build_ticker_dashboard + md_to_html_market 사용
"""
 
from __future__ import annotations
from it_html_builder import build_ticker_dashboard, md_to_html_market
 
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
from openrouter_free_models import build_model_list, strip_reasoning_blocks, extract_balanced
 
# ── 환경변수 ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY      = os.environ.get("OPENROUTER_API_KEY")
BLOGGER_BLOG_ID         = os.environ.get("BLOGGER_BLOG_ID")
BLOGGER_CLIENT_ID       = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET   = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN_2 = os.environ.get("BLOGGER_REFRESH_TOKEN_2")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
 
KST = timezone(timedelta(hours=9))
EST = timezone(timedelta(hours=-5))
DATA_DIR = "data"
 
# ⚠ 하드코딩 슬러그는 OpenRouter가 무료 라인업을 몇 주 단위로 갈아치우며 계속
# 404로 깨졌다. 매 실행마다 실제로 살아있는 무료 모델 목록을 조회해서 쓴다.
MODELS = build_model_list(limit=15)
 
TICKERS = {
    "^IXIC":    ("나스닥",        "index"),
    "^GSPC":    ("S&P500",       "index"),
    "^DJI":     ("다우존스",      "index"),
    "^VIX":     ("VIX",          "index"),
    "DX-Y.NYB": ("달러인덱스",    "macro"),
    "CL=F":     ("WTI유가",       "macro"),
    "GC=F":     ("금선물",        "macro"),
    "USDKRW=X": ("원달러환율",    "macro"),
    "QQQ":      ("나스닥100 ETF", "etf"),
    "SOXX":     ("반도체 ETF",    "etf"),
    "XLF":      ("금융 ETF",      "etf"),
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
 
 
# ── 유틸 ─────────────────────────────────────────────────────────────────────
 
def clean(text: str) -> str:
    text = html_lib.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()
 
 
import http.cookiejar

# Yahoo의 v8/finance/chart 엔드포인트는 2024년 이후 봇 차단이 강화되어
# User-Agent만으로는 401/429가 반환되는 경우가 많다.
# 브라우저처럼 쿠키를 먼저 받고(crumb 발급 없이도 쿠키만으로 대부분 통과됨) 재사용한다.
_YAHOO_COOKIE_JAR = http.cookiejar.CookieJar()
_YAHOO_OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(_YAHOO_COOKIE_JAR)
)
_YAHOO_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_YAHOO_CRUMB: Optional[str] = None
_YAHOO_WARMED_UP = False


def _yahoo_warmup() -> None:
    """finance.yahoo.com 홈페이지를 한 번 방문해 세션 쿠키를 획득하고,
    getcrumb 엔드포인트로 crumb을 발급받는다. 실패해도 조용히 넘어간다."""
    global _YAHOO_CRUMB, _YAHOO_WARMED_UP
    if _YAHOO_WARMED_UP:
        return
    _YAHOO_WARMED_UP = True
    try:
        req = urllib.request.Request(
            "https://fc.yahoo.com", headers={"User-Agent": _YAHOO_UA}
        )
        _YAHOO_OPENER.open(req, timeout=10)
    except Exception as e:
        print(f"  [WARN] Yahoo 쿠키 워밍업 실패: {e}")
    try:
        req = urllib.request.Request(
            "https://query1.finance.yahoo.com/v1/test/getcrumb",
            headers={"User-Agent": _YAHOO_UA},
        )
        with _YAHOO_OPENER.open(req, timeout=10) as r:
            crumb = r.read().decode("utf-8").strip()
            if crumb and "<html" not in crumb.lower():
                _YAHOO_CRUMB = crumb
    except Exception as e:
        print(f"  [WARN] Yahoo crumb 발급 실패: {e}")


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


def fetch_yahoo(url: str, timeout: int = 15) -> Optional[bytes]:
    """쿠키(+crumb)를 실어 Yahoo 엔드포인트를 호출. 401/429 시 한 번 재시도."""
    _yahoo_warmup()
    full_url = url
    if _YAHOO_CRUMB:
        sep = "&" if "?" in url else "?"
        full_url = f"{url}{sep}crumb={urllib.parse.quote(_YAHOO_CRUMB)}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(full_url, headers={
                "User-Agent": _YAHOO_UA,
                "Accept": "application/json,text/plain,*/*",
            })
            with _YAHOO_OPENER.open(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            print(f"  [WARN] Yahoo fetch 실패(시도 {attempt+1}): {url[:60]} → HTTP {e.code}")
            if e.code in (401, 429) and attempt == 0:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            print(f"  [WARN] Yahoo fetch 실패: {url[:60]} → {e}")
            return None
    return None
 
 
# ── 1. 시세 수집 ──────────────────────────────────────────────────────────────

# Yahoo가 완전히 막혔을 때를 대비한 2차 소스(Stooq, 무인증·무API키).
# 정확도가 조금 떨어질 수 있으나 최소한 "발행 실패"보다는 낫다.
STOOQ_SYMBOLS = {
    "^IXIC": "^ndq", "^GSPC": "^spx", "^DJI": "^dji", "^VIX": "^vix",
    "CL=F": "cl.f", "GC=F": "gc.f", "USDKRW=X": "usdkrw",
    "QQQ": "qqq.us", "SOXX": "soxx.us", "XLF": "xlf.us",
    "NVDA": "nvda.us", "AMD": "amd.us", "INTC": "intc.us", "TSM": "tsm.us",
    "AAPL": "aapl.us", "MSFT": "msft.us", "TSLA": "tsla.us", "AMZN": "amzn.us",
    "GOOGL": "googl.us", "META": "meta.us",
}


def get_quote_stooq(symbol: str) -> Optional[dict]:
    stooq_sym = STOOQ_SYMBOLS.get(symbol)
    if not stooq_sym:
        return None
    url = f"https://stooq.com/q/l/?s={urllib.parse.quote(stooq_sym)}&f=sd2t2ohlcvn&h&e=csv"
    raw = fetch(url, timeout=10)
    if not raw:
        return None
    try:
        lines = raw.decode("utf-8", errors="ignore").strip().splitlines()
        if len(lines) < 2:
            return None
        header = [h.strip().lower() for h in lines[0].split(",")]
        row = lines[1].split(",")
        rec = dict(zip(header, row))
        close = float(rec.get("close", "N/D"))
        open_ = float(rec.get("open", "N/D"))
        if close != close or open_ != open_:  # NaN 방지
            return None
        chg_pct = (close - open_) / open_ * 100 if open_ else 0.0
        volume = int(float(rec["volume"])) if rec.get("volume", "N/D") not in ("N/D", "") else 0
        name, kind = TICKERS.get(symbol, (symbol, "stock"))
        return {
            "symbol": symbol, "name": name, "kind": kind,
            "price": round(close, 2), "prev": round(open_, 2),
            "chg_pct": round(chg_pct, 2), "volume": volume,
            "market_date_us": rec.get("date", ""),
        }
    except Exception as e:
        print(f"  [WARN] Stooq 파싱 실패 {symbol}: {e}")
        return None


def get_quote(symbol: str) -> Optional[dict]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?interval=1d&range=5d"
    )
    raw = fetch_yahoo(url, timeout=10)
    if not raw:
        # Yahoo가 차단되었으면 Stooq로 폴백
        fallback = get_quote_stooq(symbol)
        if fallback:
            print(f"  [INFO] {symbol}: Yahoo 실패 → Stooq로 대체")
        return fallback
    try:
        data   = json.loads(raw)
        result = data["chart"]["result"][0]
        meta   = result["meta"]
 
        curr_price = meta.get("regularMarketPrice")
 
        # ✅ 핵심 수정: closes 배열에서 직전 거래일 종가 직접 추출
        # meta의 previousClose는 종종 전전일 기준이라 등락률이 틀림
        closes = (
            result
            .get("indicators", {})
            .get("quote", [{}])[0]
            .get("close", [])
        )
        closes = [c for c in closes if c is not None]
 
        if len(closes) >= 2:
            prev_close = closes[-2]   # 직전 거래일 종가
        elif len(closes) == 1:
            prev_close = closes[0]
        else:
            # 폴백: meta 값 사용
            prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
 
        if not curr_price or not prev_close:
            return None
 
        chg_pct = (curr_price - prev_close) / prev_close * 100
        volume  = meta.get("regularMarketVolume", 0)
 
        ts = meta.get("regularMarketTime", 0)
        market_date_us = (
            datetime.fromtimestamp(ts, tz=EST).strftime("%m/%d") if ts else ""
        )
 
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
        print(f"  [WARN] 파싱 실패 {symbol}: {e} (Yahoo가 HTML/캡차를 반환했을 가능성)")
        fallback = get_quote_stooq(symbol)
        if fallback:
            print(f"  [INFO] {symbol}: Yahoo 파싱 실패 → Stooq로 대체")
        return fallback
 
 
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
 
 
def get_us_market_date(quotes: dict) -> str:
    q = quotes.get("^IXIC") or quotes.get("^GSPC")
    if q and q.get("market_date_us"):
        return q["market_date_us"]
    return datetime.now(EST).strftime("%m/%d")
 
 
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
 
def call_ai(prompt: str, max_tokens: int = 7000, exclude_models: set | None = None,
            used_model_out: list | None = None) -> str:
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY 없음")
        sys.exit(1)
    if not MODELS:
        print("[ERROR] 사용 가능한 무료 모델을 하나도 찾지 못함")
        sys.exit(1)

    exclude_models = exclude_models or set()
    models_to_try = [m for m in MODELS if m not in exclude_models] or MODELS

    for model in models_to_try:
        payload = {
            "model":       model,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": 0.3,
            # 리즈닝 모델이 <think> 태그 없이 사고과정을 본문에 그대로 흘려보내는
            # 경우가 있어(2026-08-24 nemotron-3.5-lightning, nemotron-3-ultra
            # 실제 관측), 지원되는 모델에 한해 reasoning을 응답 content에서
            # 제외하도록 요청한다.
            "reasoning": {"exclude": True},
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
            min_len = 5 if max_tokens <= 300 else 100
            if content and len(content.strip()) >= min_len:
                print(f"  [OK] 모델: {model} / {len(content.strip())}자")
                if used_model_out is not None:
                    used_model_out.append(model)
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
    if v >= 100_000_000:
        return f"{v/100_000_000:.1f}억주"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    return str(v)
 
 
def build_prompt(quotes: dict, news: list, now_kst: datetime, us_date: str) -> str:
    idx_lines = [f"=== 주요 지수 (미국 현지 {us_date} 정규장 마감 기준) ==="]
    for sym in ["^IXIC", "^GSPC", "^DJI", "^VIX"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            vol  = f" / 거래량:{fmt_vol(q['volume'])}" if q["volume"] else ""
            idx_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%){vol}")
 
    etf_lines = ["\n=== 섹터 ETF ==="]
    for sym in ["QQQ", "SOXX", "XLF"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            etf_lines.append(f"{q['name']}({sym}): {q['price']} ({sign}{q['chg_pct']}%)")
 
    macro_lines = ["\n=== 매크로 ==="]
    for sym in ["DX-Y.NYB", "CL=F", "GC=F", "USDKRW=X"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            macro_lines.append(f"{q['name']}: {q['price']} ({sign}{q['chg_pct']}%)")
 
    stock_lines = ["\n=== 핵심 종목 ==="]
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
 
    news_lines = ["\n=== 주요 헤드라인 ==="]
    for i, n in enumerate(news[:18], 1):
        news_lines.append(f"{i}. {n['title']}")
        if n.get("summary"):
            news_lines.append(f"   {n['summary'][:180]}")
 
    market_text = "\n".join(idx_lines + etf_lines + macro_lines + stock_lines + news_lines)
    kst_date    = now_kst.strftime("%Y년 %m월 %d일")
 
    return f"""당신은 정보관리기술사를 준비하는 현업 개발자이자, 본인 투자 기록을 블로그에 공개하는 개인 투자자다.
독자는 AI가 작성한 뻔한 글을 극도로 싫어한다.
아래 실제 시장 데이터를 바탕으로 오늘 아침 한국 증시 대응 리포트를 작성하라.
 
【KST 발행일】{kst_date}
【데이터 기준】미국 현지 {us_date} NYSE/NASDAQ 정규장 마감 (오후 4시 ET)
【데이터】
{market_text}
 
【톤 — 애널리스트 리포트와 개인 투자 기록의 중간】
- 3인칭 애널리스트 톤이 아니라, 직접 이 데이터를 보고 본인 포지션을 고민하는 1인칭 관점을 섞는다
- 리드 문단과 5번 섹션(한국 연관 종목 체크)에는 "내 포트폴리오 기준으로", "실제로 지켜보면" 같은 개인 관점 어투를 1~2번 자연스럽게 넣는다
- 나머지 섹션은 기존처럼 데이터 중심 분석 구조를 유지한다
- 반말이나 인터넷 말투는 쓰지 않는다. 존댓말·평서문 유지
 
【작성 원칙】
- "알아보겠습니다", "살펴보겠습니다" 절대 금지
- "다양한", "혁신적인", "중요한" 절대 금지
- "또한", "한편", "따라서", "즉" 문장 연결 금지
- 수치는 위 데이터에 있는 것만 사용
- 문장은 짧고 밀도 있게
- 투자 권유 절대 금지
- 원/달러 환율 변화가 한국 수출주에 미치는 영향 반드시 언급
- 섹터 ETF(QQQ, SOXX, XLF) 흐름 활용
- 각 섹션 최소 3~4문장 이상 (총 3000자 이상 목표)
 
【섹션 구조】
 
(리드 문단: 헤딩 없이 2~3문장. 오늘 시장 핵심 요약)
 
## 1. 간밤 미국 증시 요약
## 2. 핵심 드라이버
## 3. 섹터별 흐름
- **섹터명**: 설명 (bullet 4~5개)
## 4. 오늘 코스피·코스닥 영향 예측
## 5. 한국 연관 종목 체크
- **종목명**: 미국 모종목 → 한국 영향 (bullet 6개 이상)
## 6. 오늘의 리스크 & 체크리스트
- bullet 형식
## 7. 3줄 요약
- bullet 정확히 3개
"""
 
 
# ── 5. 제목 생성 ──────────────────────────────────────────────────────────────
 
def generate_title(quotes: dict, now_kst: datetime, us_date: str):
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
 
    prompt = f"""아래 조건으로 블로그 제목 3개를 추천하라.
 
날짜(KST): {kst_date_str}
시장: {nasdaq_line}
 
조건:
- 30자 이내, 날짜 포함
- 숫자로 개수 암시 금지
- 한국 투자자 관점
 
아래는 JSON "형식"을 보여주는 예시일 뿐입니다. <> 안의 설명을 그대로 베껴서
출력하지 말고, 실제 제목 문자열로 교체해서 출력하세요.
{{"titles": ["<30자 이내 실제 제목 1>", "<실제 제목 2>", "<실제 제목 3>"]}}
 
JSON만 출력:
"""
    fallback = f"{kst_date_str} 미국 증시 마감 & 코스피 전망"
    raw = call_ai(prompt, max_tokens=800)
    json_str = extract_balanced(strip_reasoning_blocks(raw), "{", "}")
    if json_str:
        try:
            result = json.loads(json_str)
            titles = result.get("titles", [])
            # 모델이 예시의 플레이스홀더(<...>, "제목1" 등)를 그대로 베껴
            # 반환하는 경우가 있다 — 문법은 유효한 JSON이라 파싱은 통과하므로
            # 내용 자체를 검증해야 한다(03_generate_post.py와 동일 이슈).
            real_titles = [
                t for t in titles
                if isinstance(t, str) and t.strip()
                and not re.match(r"^\s*<.*>\s*$", t)
                and not re.match(r"^제목\s*\d*$", t.strip())
            ]
            if real_titles:
                return real_titles[0], real_titles
            print(f"[WARN] 제목 후보가 전부 플레이스홀더로 보여 기본 제목으로 대체: {titles}")
        except Exception:
            pass
    return fallback, [fallback]
 
 
# ── 6. Blogger 발행 ───────────────────────────────────────────────────────────
 
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
            ] if not val
        ]
        if missing:
            print(f"[ERROR] 필수 환경변수 누락: {', '.join(missing)}")
            sys.exit(1)
 
    # 1) 시세 수집
    quotes = collect_quotes()
    if not quotes:
        print("[ERROR] 시세 수집 실패")
        sys.exit(1)
 
    us_date = get_us_market_date(quotes)
    print(f"  미국 마감일: {us_date}")
 
    # 2) 뉴스 수집
    news = collect_news()
 
    # 3) 원본 데이터 저장
    with open(f"{DATA_DIR}/market_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump({"quotes": quotes, "news": news,
                   "us_date": us_date, "generated_at": now_kst.isoformat()},
                  f, ensure_ascii=False, indent=2)
 
    # 4) AI 분석
    print("[3] AI 분석 중...")
    analysis = call_ai(build_prompt(quotes, news, now_kst, us_date))
    print(f"  분석 완료: {len(analysis)}자")
 
    # 5) HTML 변환 (it_html_builder 사용)
    dashboard    = build_ticker_dashboard(quotes, now_kst)
    content_html = md_to_html_market(analysis, quotes)
    content_html = content_html.replace("{DASHBOARD}", dashboard)
 
    # 6) 제목 생성
    print("[4] 제목 생성 중...")
    final_title, title_candidates = generate_title(quotes, now_kst, us_date)
    print(f"  제목: {final_title}")
 
    tags = ["미국증시", "코스피전망", "주식시황", "나스닥", "한국증시"]
 
    # 7) 파일 저장
    with open(f"{DATA_DIR}/market_post_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump({"title": final_title, "title_candidates": title_candidates,
                   "content_html": content_html, "tags": ",".join(tags),
                   "us_date": us_date, "created_at": now_kst.isoformat()},
                  f, ensure_ascii=False, indent=2)
 
    html_path = f"{DATA_DIR}/market_post_{date_str}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content_html)
    print(f"  HTML 저장 → {html_path}")
 
    if DRY_RUN:
        print(f"[DRY_RUN] 발행 스킵.")
        return
 
    # 8) Blogger 발행
    print("[5] Blogger 발행 중...")
    result = post_to_blogger(final_title, content_html, tags)
    print(f"[OK] 발행 성공! URL: {result.get('url', '')}")
 
    with open(f"{DATA_DIR}/market_result_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump({"title": final_title, "url": result.get("url", ""),
                   "post_id": result.get("id", ""), "us_date": us_date,
                   "created_at": now_kst.isoformat()},
                  f, ensure_ascii=False, indent=2)
 
 
if __name__ == "__main__":
    main()
 
