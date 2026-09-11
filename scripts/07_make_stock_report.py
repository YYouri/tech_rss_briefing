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
    "^SOX":     ("필라델피아반도체지수", "index"),
    "DX-Y.NYB": ("달러인덱스",    "macro"),
    "CL=F":     ("WTI유가",       "macro"),
    "GC=F":     ("금선물",        "macro"),
    "USDKRW=X": ("원달러환율",    "macro"),
    "QQQ":      ("나스닥100 ETF", "etf"),
    "SOXX":     ("반도체 ETF",    "etf"),
    "XLF":      ("금융 ETF",      "etf"),
    "EWY":      ("한국 ETF(EWY)", "kr_proxy"),
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
    # ⚠ 한국거래소 종목의 "실제" 전일 종가 — 모델이 임의로 원화 가격을
    # 지어내지 못하도록 실측치를 기준점으로 제공한다 (2026-09-10 사고:
    # 삼성전자를 26만 원대인데 8만 원대로 서술한 사례 참고).
    "005930.KS": ("삼성전자(KRX)",   "kr_actual"),
    "000660.KS": ("SK하이닉스(KRX)", "kr_actual"),
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
    "^SOX":  ["삼성전자", "SK하이닉스", "한미반도체", "DB하이텍"],
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
    "^SOX": "^sox",
    "CL=F": "cl.f", "GC=F": "gc.f", "USDKRW=X": "usdkrw",
    "QQQ": "qqq.us", "SOXX": "soxx.us", "XLF": "xlf.us", "EWY": "ewy.us",
    "NVDA": "nvda.us", "AMD": "amd.us", "INTC": "intc.us", "TSM": "tsm.us",
    "AAPL": "aapl.us", "MSFT": "msft.us", "TSLA": "tsla.us", "AMZN": "amzn.us",
    "GOOGL": "googl.us", "META": "meta.us",
    # ⚠ Stooq의 한국거래소 커버리지는 보장이 안 돼 실패할 수 있음 —
    # 실패 시 collect_quotes()가 조용히 건너뛰므로 리포트 자체는 안 죽는다.
    "005930.KS": "005930.kr", "000660.KS": "000660.kr",
}


def compute_chg_pct(curr_price: float, prev_close: float) -> float:
    """등락률 계산은 반드시 이 함수 하나만 거친다.
    Yahoo 경로와 Stooq 폴백 경로가 각자 다른 공식(전일 종가 대비 vs 당일 시가 대비)을
    쓰면서 같은 가격에 다른 등락률이 나오는 사고가 있었다(2026-09-11 실제 발행본에서
    확인 — 두 날짜의 종목 현재가는 완전히 동일한데 등락률·부호가 전부 달랐음).
    앞으로 소스가 하나 더 늘어도 이 함수만 거치면 같은 사고는 재발하지 않는다."""
    if not prev_close:
        return 0.0
    return (curr_price - prev_close) / prev_close * 100


def get_stooq_prev_close(stooq_sym: str) -> Optional[float]:
    """Stooq 일별 히스토리에서 '직전 거래일' 종가를 가져온다.
    q/l/ 실시간 엔드포인트에는 당일 시가·현재가만 있고 전일 종가가 없어서,
    day/i=d 히스토리를 별도로 조회해 마지막에서 두 번째 행(직전 거래일)을 쓴다."""
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(stooq_sym)}&i=d"
    raw = fetch(url, timeout=10)
    if not raw:
        return None
    try:
        lines = [l for l in raw.decode("utf-8", errors="ignore").strip().splitlines() if l]
        if len(lines) < 3:
            return None
        # 마지막 행(lines[-1])은 당일 진행 중인 바(bar)일 수 있으므로,
        # 그 직전 행(lines[-2])을 "직전 거래일 종가"로 사용한다.
        header = [h.strip().lower() for h in lines[0].split(",")]
        row    = lines[-2].split(",")
        rec    = dict(zip(header, row))
        prev_close = float(rec.get("close", "N/D"))
        if prev_close != prev_close:  # NaN
            return None
        return prev_close
    except Exception as e:
        print(f"  [WARN] Stooq 전일종가 조회 실패: {e}")
        return None


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
        if close != close:  # NaN 방지
            return None

        # ⚠ 예전에는 여기서 당일 시가(open) 대비로 등락률을 계산해서 Yahoo 경로와
        # 기준이 달라지는 사고가 있었다. 반드시 "전일 거래일 종가" 대비로 계산한다.
        prev_close = get_stooq_prev_close(stooq_sym)
        if not prev_close:
            print(f"  [WARN] {symbol}: Stooq 전일종가 조회 실패 — 등락률 신뢰 불가, 스킵")
            return None
        chg_pct = compute_chg_pct(close, prev_close)

        volume = int(float(rec["volume"])) if rec.get("volume", "N/D") not in ("N/D", "") else 0
        name, kind = TICKERS.get(symbol, (symbol, "stock"))
        return {
            "symbol": symbol, "name": name, "kind": kind,
            "price": round(close, 2), "prev": round(prev_close, 2),
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
 
        chg_pct = compute_chg_pct(curr_price, prev_close)
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


# ── 발행 직전 자동 정합성 검사 ─────────────────────────────────────────────────
# 사람이 매일 발행물을 확인할 수 없다는 전제 하에 만든 안전망이다.
# 원칙: "애매하면 발행하지 않는다" — 토픽 미선정으로 하루 안 올라오는 것과
# 마찬가지로, 데이터가 앞뒤가 안 맞으면 그날은 조용히 건너뛰는 쪽이 잘못된
# 수치를 그대로 내보내는 것보다 낫다.

# 지수/ETF/매크로처럼 하루에 이 이상 튀는 게 거의 불가능한 종류는 임계값을
# 보수적으로 좁게, 개별 종목처럼 실제로도 급등락이 흔한 것은 넓게 둔다.
SANITY_MAX_ABS_PCT = {
    "index": 12.0, "etf": 12.0, "macro": 15.0,
    "kr_proxy": 15.0, "kr_actual": 20.0, "stock": 30.0,
}


def sanity_check(quotes: dict, prev_day_quotes: Optional[dict] = None) -> list[str]:
    """
    수집된 quotes가 내부적으로 앞뒤가 맞는지 자동 점검한다.
    반환값: 발견된 문제 설명 리스트 (비어 있으면 이상 없음)
    """
    problems = []

    for sym, q in quotes.items():
        # (1) 내부 모순 검사: 저장된 chg_pct가 price/prev로 재계산한 값과
        #     실제로 일치하는지 확인한다. 2026-09-11 사고(Yahoo/Stooq 공식
        #     불일치)처럼 "가격은 맞는데 등락률만 틀린" 경우를 정확히 잡아낸다.
        recomputed = compute_chg_pct(q["price"], q["prev"])
        if abs(recomputed - q["chg_pct"]) > 0.1:
            problems.append(
                f"{q['name']}({sym}): 저장된 등락률 {q['chg_pct']}%가 "
                f"price/prev로 재계산한 {recomputed:.2f}%와 불일치"
            )
            continue

        # (2) 전날 리포트와 대조: 가격이 사실상 동일한데 등락률이 크게 다르면
        #     '전일 대비' 기준점 자체가 실행마다 흔들리고 있다는 신호다.
        prev_q = (prev_day_quotes or {}).get(sym)
        if prev_q and abs(q["price"] - prev_q["price"]) < max(0.01, q["price"] * 0.0005):
            if abs(q["chg_pct"] - prev_q["chg_pct"]) > 1.0:
                problems.append(
                    f"{q['name']}({sym}): 어제와 가격이 사실상 동일({q['price']})한데 "
                    f"등락률은 어제 {prev_q['chg_pct']}% → 오늘 {q['chg_pct']}%로 다름"
                )

        # (3) 극단적 이상치: 종류별 상식적 범위를 벗어나면 데이터 소스 오류일
        #     가능성이 높다 (실제 폭락/폭등이어도 일단 사람 확인 전엔 보류).
        cap = SANITY_MAX_ABS_PCT.get(q.get("kind", "stock"), 30.0)
        if abs(q["chg_pct"]) > cap:
            problems.append(
                f"{q['name']}({sym}): 등락률 {q['chg_pct']}%가 "
                f"'{q.get('kind')}' 유형 상식 범위(±{cap}%) 초과"
            )

    return problems


def load_prev_day_quotes(date_str: str) -> Optional[dict]:
    """직전 실행분의 data/market_{date}.json에서 quotes만 로드한다.
    파일이 없거나 형식이 안 맞아도 조용히 None을 반환 — 이 검사는 '있으면
    좋은' 보조 수단이지 필수 전제조건이 아니다."""
    try:
        prev_date = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        path = f"{DATA_DIR}/market_{prev_date}.json"
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("quotes")
    except Exception:
        return None


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
 
    # ── 한국 시장 선행지표 ──────────────────────────────────────────────────
    # EWY(미국에 상장된 한국 지수 ETF, 미 증시 시간에 실시간 거래)와
    # 필라델피아 반도체지수(^SOX)는 "다음 날 코스피가 어느 방향으로 열릴지"를
    # 미국 개별 종목 하나하나보다 직접적으로 반영하는 선행지표다.
    # 삼성전자/SK하이닉스는 임의 가격 서술을 막기 위한 실측 기준점으로 제공한다.
    kr_lines = ["\n=== 한국 시장 선행지표 (실측 데이터) ==="]
    ewy = quotes.get("EWY")
    if ewy:
        sign = "+" if ewy["chg_pct"] >= 0 else ""
        kr_lines.append(
            f"한국 ETF(EWY, 미국 상장·삼성전자·SK하이닉스 비중 높음): "
            f"{ewy['price']} ({sign}{ewy['chg_pct']}%) → 코스피 익일 방향의 1차 근거로 사용"
        )
    sox = quotes.get("^SOX")
    if sox:
        sign = "+" if sox["chg_pct"] >= 0 else ""
        kr_lines.append(f"필라델피아반도체지수(SOX): {sox['price']} ({sign}{sox['chg_pct']}%)")
    for sym in ["005930.KS", "000660.KS"]:
        q = quotes.get(sym)
        if q:
            sign = "+" if q["chg_pct"] >= 0 else ""
            kr_lines.append(
                f"{q['name']} 전일 KRX 종가(실제값, 참고용): "
                f"{q['price']:,.0f}원 ({sign}{q['chg_pct']}%)"
            )
    if len(kr_lines) == 1:
        kr_lines.append("(EWY/SOX/KRX 실측 데이터 수집 실패 — 미국 개별 종목 상관관계로만 추정할 것)")
 
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
 
    market_text = "\n".join(idx_lines + etf_lines + macro_lines + kr_lines + stock_lines + news_lines)
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
- ⚠ 한국 종목(삼성전자, SK하이닉스, 한미반도체, LG에너지솔루션 등)의 원화 가격·등락률·
  지지선/저항선은 위 "한국 시장 선행지표" 블록에 실측치로 제공된 삼성전자·SK하이닉스
  전일 KRX 종가 외에는 절대 언급하지 말 것. 그 두 종목도 제공된 숫자 그대로만 인용하고
  다른 가격을 지어내지 않는다. 나머지 한국 종목(한미반도체, DB하이텍, LG에너지솔루션 등)은
  실측 가격이 없으므로 원화 가격 자체를 언급하지 말고 "미국 모종목이 이만큼 움직였으니
  이런 방향·강도의 압력을 받을 것"이라는 인과관계·방향성으로만 서술한다
  (예: "TSM -1.68%는 DB하이텍 파운드리 업황에 부담" O, 근거 없는 "10만 원 이탈 우려" X)
- 코스피·코스닥 익일 방향을 판단할 때는 개별 미국 종목보다 EWY(한국 ETF)와
  필라델피아반도체지수(SOX)의 등락을 1차 근거로 삼고, 개별 종목 등락은 업종별 부연 설명에만 쓴다
- 애널리캐피탈, 아메리칸타워 등 위 데이터에 없는 미국 종목도 동일한 이유로 구체적
  수치 언급 금지 — 섹터 흐름은 해당 섹터 ETF(QQQ/SOXX/XLF) 수치로만 설명
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
- **섹터명**: 설명 (bullet 4~5개, 위 데이터에 있는 종목/ETF 수치만 사용)
## 4. 오늘 코스피·코스닥 영향 예측
- EWY·SOX 등락을 1차 근거로 코스피 갭 방향을 먼저 제시하고, 원달러 환율·개별 종목
  상관관계를 보조 근거로 덧붙인다
## 5. 한국 연관 종목 체크
- **종목명**: 미국 모종목의 등락(%) → 한국 종목이 받을 방향성·강도 예측. 삼성전자·
  SK하이닉스는 제공된 전일 KRX 종가를 기준점으로 언급 가능하나 그 외 가격 추정 금지,
  나머지 종목은 원화 가격·지지선 언급 없이 방향성만 서술 (bullet 6개 이상)
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
                # "...", "…", "-", "N/A" 등 실제 글자가 없는 플레이스홀더 배제
                and re.search(r"[가-힣A-Za-z0-9]", t)
            ]
            if real_titles:
                return real_titles[0], real_titles
            print(f"[WARN] 제목 후보가 전부 플레이스홀더로 보여 기본 제목으로 대체: {titles}")
        except Exception:
            pass
    return fallback, [fallback]
 
 
# ── AI 생성 본문 사후 검증 (자동 자가치유) ───────────────────────────────────
# 프롬프트에 "삼성전자·SK하이닉스 실측치 외 원화 가격 언급 금지"를 명시해도,
# 모델이 규칙을 어기는 사례가 실제로 반복됐다(애널리캐피탈 -2.7%, 삼성전자
# 8만 원 등). 사람이 매번 못 보니, 발행 전에 코드가 직접 본문을 스캔해서
# 허용 목록에 없는 원화 가격 언급이 있으면 해당 문장만 잘라낸다.

WON_PRICE_PATTERN = re.compile(r"[가-힣]{0,6}[0-9][0-9,]*\s*만?\s*원")


def _split_sentences(text: str) -> list[str]:
    # 한국어 문장 종결(. 다음 공백/줄바꿈) 기준 — 완벽하진 않지만
    # "숫자원" 오탐 제거용으로는 충분한 근사치다.
    return re.split(r"(?<=[.!?])\s+", text)


def _price_ok(text: str, allowed_prices: set) -> bool:
    """문장/구절 안의 모든 '숫자(만)원' 표기가 허용 목록과 맞는지 확인."""
    for m in WON_PRICE_PATTERN.findall(text):
        digits = re.sub(r"[^0-9]", "", m)
        if not digits:
            continue
        num = int(digits)
        is_man = "만" in m
        candidates = {num, num * 10000 if is_man else num}
        if not (candidates & allowed_prices):
            return False
    return True


BULLET_PREFIX_PATTERN = re.compile(r"^(\s*[-*]\s*(?:\*\*.+?\*\*\s*[:：]\s*)?)(.*)$")


def audit_kr_price_mentions(analysis: str, quotes: dict) -> tuple[str, list[str]]:
    """
    본문에서 '숫자(만) 원' 패턴을 찾아, 위 quotes에 있는 실측 원화 가격
    (005930.KS, 000660.KS)과 어림 일치하지 않으면 그 문장만 제거한다.
    불릿("- **종목명**: ...") 형식은 접두어를 보존한 채 뒷부분만 문장 단위로
    걸러내므로, 정상 수치(예: 259,500원)와 지어낸 수치(예: 25만 원 지지선)가
    한 줄에 섞여 있어도 정상 수치는 살아남는다.
    반환값: (정제된 본문, 제거된 문장 목록 — 감사 로그용)
    """
    allowed_prices = set()
    for sym in ("005930.KS", "000660.KS"):
        q = quotes.get(sym)
        if q:
            allowed_prices.add(round(q["price"]))
            allowed_prices.add(round(q["price"] / 10000))  # "26만 원" 같은 축약 표기 허용

    removed = []
    cleaned_lines = []
    for line in analysis.split("\n"):
        if not WON_PRICE_PATTERN.search(line):
            cleaned_lines.append(line)
            continue

        bm = BULLET_PREFIX_PATTERN.match(line)
        prefix, body = (bm.group(1), bm.group(2)) if bm else ("", line)

        kept_sentences = []
        for s in _split_sentences(body):
            if s.strip() and not _price_ok(s, allowed_prices):
                removed.append(s.strip())
            elif s.strip():
                kept_sentences.append(s)

        if kept_sentences:
            cleaned_lines.append(prefix + " ".join(kept_sentences))
        elif prefix.strip():
            # 접두어(종목명)만 남고 내용이 통째로 걸러진 경우 — 빈 불릿은 버린다.
            continue
        # prefix도 body도 다 없으면 그냥 그 줄 자체를 스킵(= 추가 안 함)

    return "\n".join(cleaned_lines), removed


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

    # 1-1) 자동 정합성 검사 — 사람이 매일 못 보는 걸 전제로, 애매하면
    #      발행 자체를 하지 않는다 (토픽 미선정과 같은 원칙).
    prev_day_quotes = load_prev_day_quotes(date_str)
    problems = sanity_check(quotes, prev_day_quotes)
    if problems:
        print("[ERROR] 정합성 검사 실패 — 오늘 발행을 건너뜁니다:")
        for p in problems:
            print(f"  - {p}")
        with open(f"{DATA_DIR}/market_skipped_{date_str}.json", "w", encoding="utf-8") as f:
            json.dump({"reason": "sanity_check_failed", "problems": problems,
                       "quotes": quotes, "created_at": now_kst.isoformat()},
                      f, ensure_ascii=False, indent=2)
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
    prompt   = build_prompt(quotes, news, now_kst, us_date)
    used_model: list[str] = []
    analysis = call_ai(prompt, used_model_out=used_model)
    print(f"  분석 완료: {len(analysis)}자")

    # 4-1) 본문 사후 검증 — 허용 안 된 원화 가격 언급을 자동으로 제거한다.
    analysis, removed_lines = audit_kr_price_mentions(analysis, quotes)
    if removed_lines:
        print(f"[WARN] 사후 검증에서 근거 없는 원화 가격 언급 {len(removed_lines)}건 제거:")
        for l in removed_lines:
            print(f"  - {l[:80]}")
 
    # 5) HTML 변환 (it_html_builder 사용)
    dashboard    = build_ticker_dashboard(quotes, now_kst)
    content_html = md_to_html_market(analysis, quotes)
    content_html = content_html.replace("{DASHBOARD}", dashboard)
 
    # 6) 제목 생성
    print("[4] 제목 생성 중...")
    final_title, title_candidates = generate_title(quotes, now_kst, us_date)
    print(f"  제목: {final_title}")
 
    tags = ["미국증시", "코스피전망", "주식시황", "나스닥", "한국증시"]
 
    # 7) 파일 저장 (+ 감사 추적용 프롬프트/모델명 함께 보관)
    with open(f"{DATA_DIR}/market_post_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump({"title": final_title, "title_candidates": title_candidates,
                   "content_html": content_html, "tags": ",".join(tags),
                   "us_date": us_date, "created_at": now_kst.isoformat(),
                   "audit": {
                       "prompt": prompt,
                       "model_used": used_model[0] if used_model else None,
                       "removed_kr_price_mentions": removed_lines,
                   }},
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
 
