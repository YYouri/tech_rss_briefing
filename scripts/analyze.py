import json
import urllib.request
import urllib.error
import os
import sys

with open("articles.json", encoding="utf-8") as f:
    articles = json.load(f)

if not articles:
    print("수집된 기사가 없습니다.")
    sys.exit(1)

lines = []
for i, a in enumerate(articles, 1):
    lines.append(f"{i}. [{a['domain']}] {a['title']}")
    lines.append(f"   URL: {a['link']}")
    if a['desc']:
        lines.append(f"   요약: {a['desc']}")
    lines.append("")
article_text = "\n".join(lines)

prompt = """당신은 정보처리기술사 시험 전문 분석가입니다.
아래 뉴스 기사들을 분석하여 정확히 다음 마크다운 형식으로만 출력하세요.
설명, 인사말, 기타 텍스트는 절대 출력하지 마세요.

## 기술사 시험 뉴스 브리핑

| 순번 | 도메인 | 연관 토픽 | 기사 요약 (한글 2줄 이내) | 관련 기출 | URL |
|:----:|:------:|:---------:|:-------------------------|:---------|:----|

## 핵심 키워드

| 키워드 | 설명 | 기술사 관련도 |
|:------:|:-----|:------------:|

## 예상 출제 포인트

1. **토픽명**: 출제 예상 이유 및 핵심 개념

## 학습 추천

| 우선순위 | 토픽 | 학습 포인트 |
|:--------:|:-----|:-----------|

규칙:
- 도메인: SW/AI/DB/SEC/NW
- 기사 요약은 반드시 한글로
- URL은 실제 기사 URL 그대로 사용
- 관련 기출: 모르면 "최근 출제 경향"

분석할 기사 목록:
""" + article_text

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("OPENROUTER_API_KEY가 없습니다.")
    sys.exit(1)

# 2026년 3월 기준 동작하는 무료 모델 목록
MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "google/gemma-3-27b-it:free",
    "microsoft/phi-4:free",
]

analysis = None

for model in MODELS:
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3000
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "HTTP-Referer": "https://github.com",
                "X-Title": "Tech Briefing"
            }
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        content = result.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            print(f"[OK] 모델 성공: {model}")
            analysis = content
            break
        else:
            print(f"[WARN] {model} 응답 없음, 다음 모델 시도")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[WARN] {model} 실패: {e.code} - {body[:200]}")
    except Exception as e:
        print(f"[WARN] {model} 예외: {e}")

if not analysis:
    print("모든 모델 실패")
    sys.exit(1)

with open("analysis.md", "w", encoding="utf-8") as f:
    f.write(analysis)

print(analysis)