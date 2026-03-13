import urllib.request
import urllib.parse
import json
import sys
import html
import re
import os

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 없습니다.")
    sys.exit(1)

QUERIES = {
    "AI":  "인공지능 LLM",
    "SW":  "소프트웨어 개발 클라우드",
    "DB":  "데이터베이스 빅데이터",
    "SEC": "사이버보안 정보보안",
    "NW":  "네트워크 클라우드 인프라",
}

def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

articles = []

for domain, query in QUERIES.items():
    try:
        params = urllib.parse.urlencode({
            "query": query,
            "display": 3,
            "sort": "date"
        })
        url = f"https://openapi.naver.com/v1/search/news.json?{params}"

        req = urllib.request.Request(url, headers={
            "X-Naver-Client-Id": CLIENT_ID,
            "X-Naver-Client-Secret": CLIENT_SECRET,
            "User-Agent": "Mozilla/5.0"
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        items = result.get("items", [])

        for item in items:
            title = clean(item.get("title", ""))
            link  = item.get("originallink") or item.get("link", "")
            desc  = clean(item.get("description", ""))[:100]

            if title and link:
                articles.append({
                    "domain": domain,
                    "title": title,
                    "link": link,
                    "desc": desc
                })

        print(f"[OK] {domain}: {len(items)}개 수집")

    except Exception as e:
        print(f"[WARN] {domain} 수집 실패: {e}", file=sys.stderr)

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"\n총 {len(articles)}개 기사 수집 완료")

if not articles:
    sys.exit(1)