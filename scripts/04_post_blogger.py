"""
04_post_blogger.py
Refresh Token으로 Blogger API를 직접 호출해 포스팅한다.
GAS 불필요 — 완전 자동화 가능.
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

POST_FILE   = "data/blog_post.json"
RESULT_FILE = "data/post_result.json"

BLOGGER_BLOG_ID       = os.environ.get("BLOGGER_BLOG_ID")
BLOGGER_CLIENT_ID     = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN_2")


def get_access_token() -> str:
    """Refresh Token으로 Access Token 발급"""
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


def post_to_blogger(title: str, content: str, labels: list[str]) -> dict:
    """Blogger API로 포스트 발행"""
    access_token = get_access_token()

    payload = {
        "title":   title,
        "content": content,
        "labels":  labels,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(
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
        print(f"[ERROR] Blogger API 실패 HTTP {e.code}: {body[:400]}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Blogger API 실패: {e}")
        sys.exit(1)


def main():
    for name, val in [
        ("BLOGGER_BLOG_ID",       BLOGGER_BLOG_ID),
        ("BLOGGER_CLIENT_ID",     BLOGGER_CLIENT_ID),
        ("BLOGGER_CLIENT_SECRET", BLOGGER_CLIENT_SECRET),
        ("BLOGGER_REFRESH_TOKEN", BLOGGER_REFRESH_TOKEN),
    ]:
        if not val:
            print(f"[ERROR] {name} 없음")
            sys.exit(1)

    with open(POST_FILE, encoding="utf-8") as f:
        post = json.load(f)

    title   = post["title"]
    content = post["content_html"]
    tags    = [t.strip() for t in post.get("tags", "").split(",") if t.strip()]

    print(f"[Blogger 업로드]")
    print(f"  제목   : {title}")
    print(f"  태그   : {tags}")
    print(f"  글자수 : {len(content)}자")

    result = post_to_blogger(title, content, tags)

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
