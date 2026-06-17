"""
debug-token-identity.py
Access Token이 실제로 어떤 구글 계정에 묶여 있는지 직접 확인한다.
기존 디버그 스크립트는 scope만 보여줬지만, 이건 정확히 '누구의 토큰인지' 이메일을 보여준다.

사용법:
python scripts/debug-token-identity.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

CLIENT_ID     = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN_2")
BLOG_ID       = os.environ.get("BLOGGER_BLOG_ID")


def get_access_token() -> str:
    payload = {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token":  REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode("utf-8"))
    return result["access_token"]


def check_token_identity(access_token: str):
    """이 access_token이 실제로 어떤 구글 계정(이메일)인지 직접 확인"""
    url = f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            info = json.loads(r.read().decode("utf-8"))
        print("=== 토큰 신원 확인 (tokeninfo) ===")
        print(f"email   : {info.get('email', '(이메일 없음 — scope에 email 미포함)')}")
        print(f"scope   : {info.get('scope')}")
        print(f"aud(클라이언트ID): {info.get('aud')}")
        print(f"expires_in      : {info.get('expires_in')}초")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[실패] tokeninfo 조회 실패: {e.code} {body[:300]}")


def check_userinfo(access_token: str):
    """email scope가 있으면 실제 이메일 주소까지 확인"""
    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            info = json.loads(r.read().decode("utf-8"))
        print("\n=== userinfo ===")
        print(f"email   : {info.get('email', '(없음)')}")
        print(f"name    : {info.get('name', '(없음)')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"\n[참고] userinfo 조회 불가 (정상 — blogger scope만 동의했으면 안 나옵니다): {e.code}")


def list_accessible_blogs(access_token: str):
    """이 토큰으로 실제로 글을 쓸 수 있는 블로그 목록 전체 출력"""
    req = urllib.request.Request(
        "https://www.googleapis.com/blogger/v3/users/self/blogs",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    print("\n=== 이 토큰으로 접근 가능한 블로그 목록 ===")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            blogs = json.loads(r.read().decode("utf-8"))
        items = blogs.get("items", [])
        if not items:
            print("⚠️  접근 가능한 블로그가 0개입니다. 이 계정에 연결된 Blogger 블로그가 없습니다.")
            return
        for b in items:
            marker = "  ← 시크릿 BLOGGER_BLOG_ID와 일치" if str(b.get("id")) == str(BLOG_ID) else ""
            print(f"  id={b.get('id')}")
            print(f"  name={b.get('name')}")
            print(f"  url={b.get('url')}{marker}")
            print(f"  status={b.get('status')}")
            print("  ---")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[실패] {e.code} {body[:400]}")


def try_draft_post(access_token: str):
    """진짜 쓰기 권한이 있는지 isDraft=true 로 실제 테스트"""
    print("\n=== 쓰기 권한 실제 테스트 (초안으로 발행 시도) ===")
    payload = {
        "title":   "[권한테스트] 자동 삭제 예정",
        "content": "<p>권한 확인용 테스트 게시물입니다.</p>",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url  = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/?isDraft=true"
    req  = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode("utf-8"))
        print(f"✅ 초안 발행 성공! post_id={result.get('id')}")
        print(f"   → 이건 Blogger 대시보드 '게시물' 메뉴에서 직접 삭제해주세요.")
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"❌ 초안 발행도 403 실패: {e.code}")
        print(f"   본문: {body[:500]}")
        return False
    except Exception as e:
        print(f"❌ 예외: {e}")
        return False


def main():
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BLOG_ID]):
        print("[ERROR] 환경변수 누락 — CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN/BLOG_ID 확인 필요")
        sys.exit(1)

    print(f"BLOGGER_BLOG_ID(시크릿) = {BLOG_ID}\n")

    access_token = get_access_token()

    check_token_identity(access_token)
    check_userinfo(access_token)
    list_accessible_blogs(access_token)
    try_draft_post(access_token)


if __name__ == "__main__":
    main()
