"""
Blogger 토큰 발급 + API 호출 디버그 스크립트
GitHub Actions 로그에서 토큰 앞 10자리만 출력해 실제 발급 여부 확인
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error

BLOGGER_CLIENT_ID     = os.environ.get("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN_2")
BLOGGER_BLOG_ID       = os.environ.get("BLOGGER_BLOG_ID")

print("=== 환경변수 확인 ===")
print(f"CLIENT_ID     : {'SET ('+BLOGGER_CLIENT_ID[:8]+'...)' if BLOGGER_CLIENT_ID else 'MISSING'}")
print(f"CLIENT_SECRET : {'SET' if BLOGGER_CLIENT_SECRET else 'MISSING'}")
print(f"REFRESH_TOKEN : {'SET ('+BLOGGER_REFRESH_TOKEN[:8]+'...)' if BLOGGER_REFRESH_TOKEN else 'MISSING'}")
print(f"BLOG_ID       : {BLOGGER_BLOG_ID or 'MISSING'}")

print("\n=== Access Token 발급 시도 ===")
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
    token = result.get("access_token", "")
    print(f"access_token  : {'ya29...' if token.startswith('ya29') else 'UNEXPECTED: '+token[:20]}")
    print(f"token_type    : {result.get('token_type')}")
    print(f"scope         : {result.get('scope')}")   # ← 핵심: blogger scope 있는지 확인
    print(f"expires_in    : {result.get('expires_in')}")

    print("\n=== Blogger API 호출 테스트 ===")
    api_req = urllib.request.Request(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(api_req, timeout=15) as r:
        blog = json.loads(r.read().decode("utf-8"))
    print(f"블로그명 : {blog.get('name')}")
    print(f"URL      : {blog.get('url')}")
    print("✅ 권한 정상 — Blogger API 접근 가능")

except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"❌ HTTP {e.code}: {body[:300]}")
except Exception as e:
    print(f"❌ 오류: {e}")
