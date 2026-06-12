"""
01_collect_news.py
뉴스 수집: Google News RSS / Yahoo Finance RSS / Hacker News API / Reddit API
유료 API 없음 - 완전 무료 소스만 사용
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
from datetime import datetime, timezone, timedelta

import feedparser  # pip install feedparser

OUTPUT_FILE = "data/raw_articles.json"
MAX_ARTICLES = 80   # 총 수집 한도

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

# ── 1. Google News RSS ────────────────────────────────────────────────────────

GOOGLE_NEWS_QUERIES = [
    "AI semiconductor technology",
    "HBM memory chip market",
    "Agentic AI enterprise",
    "AI data center infrastructure",
    "tech industry trend",
]

def collect_google_news() -> list[dict]:
    articles = []
    base = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    for q in GOOGLE_NEWS_QUERIES:
        url = base.format(q=urllib.parse.quote(q))
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            title = clean(entry.get("title", ""))
            link = entry.get("link", "")
            summary = clean(entry.get("summary", ""))[:200]
            if title and link:
                articles.append({
                    "source": "google_news",
                    "query": q,
                    "title": title,
                    "link": link,
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
]

def collect_yahoo_finance() -> list[dict]:
    articles = []
    for url in YAHOO_RSS_URLS:
        feed = feedparser.parse(url)
        ticker = url.split("s=")[1].split("&")[0]
        for entry in feed.entries[:4]:
            title = clean(entry.get("title", ""))
            link = entry.get("link", "")
            summary = clean(entry.get("summary", ""))[:200]
            if title and link:
                articles.append({
                    "source": "yahoo_finance",
                    "query": ticker,
                    "title": title,
                    "link": link,
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
]

def collect_hacker_news() -> list[dict]:
    articles = []
    data = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not data:
        return articles
    ids = json.loads(data)[:60]

    for story_id in ids:
        raw = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if not raw:
            continue
        item = json.loads(raw)
        title = item.get("title", "").lower()
        if not any(kw in title for kw in HN_KEYWORDS):
            continue
        score = item.get("score", 0)
        if score < 50:
            continue
        articles.append({
            "source": "hacker_news",
            "query": "top_story",
            "title": item.get("title", ""),
            "link": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
            "summary": f"HN Score: {score}, Comments: {item.get('descendants', 0)}",
        })
        if len(articles) >= 15:
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
    seen = set()
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
