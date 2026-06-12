"""
04_post_tistory.py
티스토리 Open API를 사용해 포스팅을 비공개 상태로 업로드한다.

사전 준비:
1. https://www.tistory.com/guide/api/manage/register 에서 앱 등록
2. Access Token 발급 (1회성 수동 발급 후 GitHub Secret에 저장)
3. 블로그명을 GitHub Secret TISTORY_BLOG_NAME에 저장

티스토리 API 문서: https://tistory.github.io/document-tistory-apis/
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error

POST_FILE = "data/blog_post.json"
RESULT_FILE = "data/post_result.json"

TISTORY_ACCESS_TOKEN = os.environ.get("TISTORY_ACCESS_TOKEN")
TISTORY_BLOG_NAME    = os.environ.get("TISTORY_BLOG_NAME")

TISTORY_WRITE_URL = "https://www.tistory.com/apis/post/write"

# ── 포스팅 ────────────────────────────────────────────────────────────────────

def post_to_tistory(title: str, content: str, tags: str) -> dict:
    if not TISTORY_ACCESS_TOKEN:
        print("[ERROR] TISTORY_ACCESS_TOKEN 없음")
        sys.exit(1)
    if not TISTORY_BLOG_NAME:
        print("[ERROR] TISTORY_BLOG_NAME 없음")
        sys.exit(1)

    params = {
        "access_token": TISTORY_ACCESS_TOKEN,
        "output":       "json",
        "blogName":     TISTORY_BLOG_NAME,
        "title":        title,
        "content":      content,
        "visibility":   "0",    # 0: 비공개, 3: 공개 (검토 후 수동으로 3으로 변경 권장)
        "category":     "0",    # 0: 기본 카테고리 (카테고리 ID 지정 가능)
        "tag":          tags,
        "acceptComment": "1",
    }

    encoded = urllib.parse.urlencode(params, encoding="utf-8").encode("utf-8")

    req = urllib.request.Request(
        TISTORY_WRITE_URL,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (compatible; BlogBot/1.0)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode("utf-8"))
        return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[ERROR] Tistory API HTTP {e.code}: {body[:400]}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Tistory API 호출 실패: {e}")
        sys.exit(1)

# ── 결과 확인 ─────────────────────────────────────────────────────────────────

def validate_response(result: dict) -> str:
    """티스토리 API 응답 구조 파싱"""
    try:
        tistory = result.get("tistory", {})
        status  = tistory.get("status", "")
        post_id = tistory.get("postId", "")
        url     = tistory.get("url", "")

        if status == "200":
            print(f"[OK] 포스팅 성공!")
            print(f"     Post ID : {post_id}")
            print(f"     URL     : {url}")
            return url
        else:
            print(f"[ERROR] 티스토리 응답 이상: {result}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 응답 파싱 실패: {e}\n원본: {result}")
        sys.exit(1)

# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    with open(POST_FILE, encoding="utf-8") as f:
        post = json.load(f)

    title   = post["title"]
    content = post["content_html"]
    tags    = post["tags"]

    print(f"[Tistory 업로드]")
    print(f"  제목 : {title}")
    print(f"  태그 : {tags}")
    print(f"  글자수: {len(content)}자")

    result = post_to_tistory(title, content, tags)
    url    = validate_response(result)

    out = {
        "title":      title,
        "topic":      post["topic"],
        "url":        url,
        "tags":       tags,
        "created_at": post["created_at"],
        "status":     "private",   # 비공개로 저장
    }

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 → {RESULT_FILE}")

if __name__ == "__main__":
    main()
