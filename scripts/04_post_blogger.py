"""
04_post_blogger.py
Google Apps Script 웹 앱을 통해 Blogger에 포스팅한다.
OAuth 로컬 인증 불필요 — GAS가 구글 계정 인증을 대신 처리.
"""

import json
import os
import sys
import urllib.request
import urllib.error

POST_FILE   = "data/blog_post.json"
RESULT_FILE = "data/post_result.json"

GAS_WEBHOOK_URL  = os.environ.get("GAS_WEBHOOK_URL")
GAS_SECRET_TOKEN = os.environ.get("GAS_SECRET_TOKEN")
BLOGGER_BLOG_ID  = os.environ.get("BLOGGER_BLOG_ID")


def post_via_gas(title: str, content: str, labels: list[str]) -> dict:
    if not GAS_WEBHOOK_URL:
        print("[ERROR] GAS_WEBHOOK_URL 없음")
        sys.exit(1)
    if not GAS_SECRET_TOKEN:
        print("[ERROR] GAS_SECRET_TOKEN 없음")
        sys.exit(1)
    if not BLOGGER_BLOG_ID:
        print("[ERROR] BLOGGER_BLOG_ID 없음")
        sys.exit(1)

    payload = {
        "secret":  GAS_SECRET_TOKEN,
        "blogId":  BLOGGER_BLOG_ID,
        "title":   title,
        "content": content,
        "labels":  labels,
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(
        GAS_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode("utf-8"))
        return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[ERROR] GAS 호출 실패 HTTP {e.code}: {body[:400]}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] GAS 호출 실패: {e}")
        sys.exit(1)


def main():
    with open(POST_FILE, encoding="utf-8") as f:
        post = json.load(f)

    title   = post["title"]
    content = post["content_html"]
    tags    = [t.strip() for t in post.get("tags", "").split(",") if t.strip()]

    print(f"[Blogger 업로드 via GAS]")
    print(f"  제목   : {title}")
    print(f"  태그   : {tags}")
    print(f"  글자수 : {len(content)}자")

    result = post_via_gas(title, content, tags)

    if result.get("status") != "ok":
        print(f"[ERROR] 발행 실패: {result.get('message', '')}")
        sys.exit(1)

    post_url = result.get("url", "")
    post_id  = result.get("id", "")

    print(f"[OK] 발행 성공!")
    print(f"     Post ID : {post_id}")
    print(f"     URL     : {post_url}")

    out = {
        "title":      title,
        "topic":      post["topic"],
        "url":        post_url,
        "post_id":    post_id,
        "tags":       post.get("tags", ""),
        "created_at": post["created_at"],
        "status":     "published",
    }

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 → {RESULT_FILE}")


if __name__ == "__main__":
    main()
