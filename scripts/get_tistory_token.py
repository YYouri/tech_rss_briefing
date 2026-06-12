"""
get_tistory_token.py
티스토리 Access Token 1회 수동 발급 헬퍼
GitHub Secret에 저장할 Access Token을 발급받기 위한 스크립트

사용법:
1. https://www.tistory.com/guide/api/manage/register 에서 앱 등록
2. Client ID, Client Secret, Redirect URI(http://localhost:8080) 확인
3. 아래 상수 입력 후 실행: python get_tistory_token.py
4. 출력된 Access Token을 GitHub Secret TISTORY_ACCESS_TOKEN에 저장
"""

import urllib.parse
import urllib.request
import json
import http.server
import threading
import webbrowser

CLIENT_ID     = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI  = "http://localhost:8080"

AUTH_CODE = None

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        AUTH_CODE = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>Code received! Return to terminal.</h1>")

    def log_message(self, *args):
        pass

def main():
    # 1. 인증 URL 열기
    auth_url = (
        "https://www.tistory.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        "&response_type=code"
    )
    print(f"브라우저를 열어 인증합니다:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # 2. 로컬 서버로 코드 수신
    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
    t = threading.Thread(target=server.handle_request)
    t.start()
    t.join(timeout=60)

    if not AUTH_CODE:
        print("[ERROR] 코드 수신 실패")
        return

    print(f"Authorization Code: {AUTH_CODE}")

    # 3. Access Token 교환
    token_url = (
        "https://www.tistory.com/oauth/access_token"
        f"?client_id={CLIENT_ID}"
        f"&client_secret={CLIENT_SECRET}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&code={AUTH_CODE}"
        "&grant_type=authorization_code"
    )
    with urllib.request.urlopen(token_url) as r:
        resp = r.read().decode("utf-8")

    # 응답: access_token=xxx
    if "access_token=" in resp:
        token = resp.split("access_token=")[1].split("&")[0]
        print(f"\n✅ Access Token:\n{token}")
        print("\nGitHub Repository → Settings → Secrets → New secret")
        print(f"  Name : TISTORY_ACCESS_TOKEN")
        print(f"  Value: {token}")
    else:
        print(f"[ERROR] 토큰 발급 실패: {resp}")

if __name__ == "__main__":
    main()
