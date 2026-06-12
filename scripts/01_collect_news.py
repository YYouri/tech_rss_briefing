"""
01_collect_news.py
뉴스 수집: Google News RSS / Yahoo Finance RSS / Hacker News API
유료 API 없음 - 완전 무료 소스만 사용

개선 사항:
- 기사 요약 200자 → 500자로 확장
- Google News 쿼리 다양화 (토픽당 기사 5개 → 8개)
- 기사 본문 일부 fetch 추가 (요약이 부실한 경우 보완)
- MAX_ARTICLES 80 → 120으로 확장
"""

import json
import os
import re
import sys
import time
import html
import urllib.request
import urllib.parse
import urllib.error
from googlenewsdecoder import gnewsdecoder

from datetime import datetime, timezone, timedelta

import feedparser  # pip install feedparser

OUTPUT_FILE  = "data/raw_articles.json"
MAX_ARTICLES = 120  # 80 → 120으로 확장

# ── 유틸 ──────────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch_url(url: str, headers: dict = None, timeout: int = 15) -> bytes | None:
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "Mozilla/5.0 (compatible; BlogBot/1.0)"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  [WARN] fetch 실패 {url[:60]}... → {e}")
        return None


def fetch_article_body(url: str) -> str:
    """
    기사 URL에서 본문 일부를 가져온다.
    실패하면 빈 문자열 반환 (비필수).
    <p> 태그 내용만 추출해 500자 이내로 반환.
    """
    try:
        data = fetch_url(url, timeout=8)
        if not data:
            return ""
        text = data.decode("utf-8", errors="ignore")
        # <p> 태그 내용만 추출
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", text, re.DOTALL | re.IGNORECASE)
        body = " ".join(clean(p) for p in paragraphs[:6])
        return body[:500]
    except Exception:
        return ""


# ── 1. Google News RSS ────────────────────────────────────────────────────────

GOOGLE_NEWS_QUERIES = [
    # 기존
    "AI semiconductor technology",
    "HBM memory chip market",
    "Agentic AI enterprise",
    "AI data center infrastructure",
    "tech industry trend",
    # 추가 — 토픽 다양성 확보
    "Physical AI industrial automation",
    "edge AI inference chip",
    "LLM inference optimization",
    "AI governance enterprise",
    "on-device AI mobile",
    "digital twin manufacturing",
    "zero trust security AI",
    "quantum computing enterprise",
]


def resolve_google_news_url(url: str) -> str:
    """Google News 리다이렉트 URL → 실제 기사 URL"""
    try:
        result = gnewsdecoder(url, interval=1)
        if result.get("status"):
            return result["decoded_url"]
        return url
    except Exception:
        return url

def collect_google_news() -> list[dict]:
    articles = []
    base = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    for q in GOOGLE_NEWS_QUERIES:
        url = base.format(q=urllib.parse.quote(q))
        feed = feedparser.parse(url)
        for entry in feed.entries[:8]:  # 5 → 8로 확장
            title   = clean(entry.get("title", ""))
            link    = entry.get("link", "")
            link    = resolve_google_news_url(link)
            # summary 500자로 확장
            summary = clean(entry.get("summary", ""))[:500]

            # summary가 너무 짧으면 본문 fetch 시도
            if len(summary) < 100:
                body = fetch_article_body(link)
                if body:
                    summary = body

            if title and link:
                articles.append({
                    "source":  "google_news",
                    "query":   q,
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                })
        time.sleep(1)
    print(f"[Google News] {len(articles)}개 수집")
    return articles


# ── 2. Yahoo Finance RSS ──────────────────────────────────────────────────────

YAHOO_RSS_URLS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMD&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=INTC&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSM&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GOOGL&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMZN&region=US&lang=en-US",
    # 추가 티커
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=QCOM&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AVGO&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=IBM&region=US&lang=en-US",
]

def collect_yahoo_finance() -> list[dict]:
    articles = []
    for url in YAHOO_RSS_URLS:
        feed   = feedparser.parse(url)
        ticker = url.split("s=")[1].split("&")[0]
        for entry in feed.entries[:5]:  # 4 → 5로 확장
            title   = clean(entry.get("title", ""))
            link    = entry.get("link", "")
            summary = clean(entry.get("summary", ""))[:500]  # 200 → 500

            # summary가 짧으면 본문 fetch 시도
            if len(summary) < 100:
                body = fetch_article_body(link)
                if body:
                    summary = body

            if title and link:
                articles.append({
                    "source":  "yahoo_finance",
                    "query":   ticker,
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                })
        time.sleep(0.5)
    print(f"[Yahoo Finance] {len(articles)}개 수집")
    return articles


# ── 3. Hacker News (공식 Firebase API) ───────────────────────────────────────

HN_KEYWORDS = [
    "ai", "llm", "gpu", "semiconductor", "hbm", "memory", "data center",
    "machine learning", "inference", "agent", "chip", "nvidia", "amd",
    "quantum", "zero trust", "cloud", "kubernetes", "transformer",
    "physical ai", "edge", "digital twin", "on-device", "rag",
]

def collect_hacker_news() -> list[dict]:
    articles = []
    data = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not data:
        return articles
    ids = json.loads(data)[:80]  # 60 → 80으로 확장

    for story_id in ids:
        raw = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if not raw:
            continue
        item  = json.loads(raw)
        title = item.get("title", "").lower()
        if not any(kw in title for kw in HN_KEYWORDS):
            continue
        score = item.get("score", 0)
        if score < 50:
            continue

        link    = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        summary = f"HN Score: {score}, Comments: {item.get('descendants', 0)}"

        # 본문 fetch로 요약 보완
        body = fetch_article_body(link)
        if body:
            summary = body

        articles.append({
            "source":  "hacker_news",
            "query":   "top_story",
            "title":   item.get("title", ""),
            "link":    link,
            "summary": summary,
        })
        if len(articles) >= 20:  # 15 → 20으로 확장
            break
        time.sleep(0.2)
    print(f"[Hacker News] {len(articles)}개 수집")
    return articles


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data", exist_ok=True)
    all_articles = []

    all_articles += collect_google_news()
    all_articles += collect_yahoo_finance()
    all_articles += collect_hacker_news()

    # 중복 URL 제거
    seen   = set()
    unique = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    unique = unique[:MAX_ARTICLES]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(unique)}개 기사 저장 → {OUTPUT_FILE}")
    if not unique:
        sys.exit(1)


if __name__ == "__main__":
    main()
