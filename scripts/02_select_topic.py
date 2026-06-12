"""
02_select_topic.py
OpenRouter Free API를 사용해 기사에서 IT 기술 키워드를 추출하고,
오늘 발행할 최적 토픽 1개를 선정한다.
중복 방지: 최근 30일 발행 이력 참조
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta

ARTICLES_FILE  = "data/raw_articles.json"
HISTORY_FILE   = "data/topic_history.json"
TOPIC_FILE     = "data/selected_topic.json"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "google/gemma-3-27b-it:free",
    "microsoft/phi-4:free",
]

# ── OpenRouter 호출 ───────────────────────────────────────────────────────────

def call_ai(prompt: str, max_tokens: int = 1024) -> str:
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY 없음")
        sys.exit(1)

    for model in MODELS:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json; charset=utf-8",
                "HTTP-Referer": "https://github.com",
                "X-Title": "Tech Blog",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read().decode("utf-8"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            if content:
                print(f"[OK] 모델 성공: {model}")
                return content.strip()
            print(f"[WARN] {model} 응답 없음, 다음 모델 시도")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"[WARN] {model} 실패: {e.code} - {body[:200]}")
        except Exception as e:
            print(f"[WARN] {model} 예외: {e}")

    print("[ERROR] 모든 모델 실패")
    sys.exit(1)

# ── 최근 30일 발행 이력 로드 ──────────────────────────────────────────────────

def load_recent_topics() -> list[str]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        history: list[dict] = json.load(f)
    cutoff = datetime.now() - timedelta(days=30)
    recent = [
        h["topic"].lower()
        for h in history
        if datetime.fromisoformat(h["date"]) >= cutoff
    ]
    return recent

# ── 기사 목록 → 텍스트 ───────────────────────────────────────────────────────

def articles_to_text(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("summary"):
            lines.append(f"   {a['summary'][:120]}")
    return "\n".join(lines)

# ── Step 1: 키워드 추출 ───────────────────────────────────────────────────────

def extract_keywords(article_text: str) -> list[dict]:
    prompt = f"""당신은 IT 시장 분석 전문가입니다.
아래 뉴스 기사 목록에서 반복적으로 언급되는 IT 기술 키워드를 추출하세요.

규칙:
- 단순 기업명, 인물명 제외
- 실제 IT 기술, 아키텍처, 표준, 개념만 포함
- 예: HBM, MCP, Agentic AI, CXL, SASE, Physical AI, RAG, LoRA, LLM Inference
- 각 키워드의 기사 언급 횟수와 중요도(1-10)를 추정
- 반드시 JSON 배열만 출력 (설명 없이)

출력 형식:
[
  {{"keyword": "HBM", "count": 5, "importance": 9, "reason": "반도체 메모리 핵심 기술"}},
  ...
]

뉴스 기사 목록:
{article_text}
"""
    raw = call_ai(prompt, max_tokens=1500)

    # JSON 추출
    import re
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        print(f"[WARN] 키워드 파싱 실패. 원본:\n{raw[:300]}")
        return []
    try:
        return json.loads(match.group())
    except Exception as e:
        print(f"[WARN] JSON 파싱 오류: {e}")
        return []

# ── Step 2: 토픽 선정 ─────────────────────────────────────────────────────────

def select_topic(keywords: list[dict], recent_topics: list[str]) -> dict:
    # 최근 30일 발행 키워드 제외
    filtered = [
        kw for kw in keywords
        if kw["keyword"].lower() not in recent_topics
    ]
    if not filtered:
        print("[WARN] 최근 30일 이력 제외 후 키워드 없음 → 이력 무시하고 재시도")
        filtered = keywords

    # 중요도 × count 점수 정렬
    scored = sorted(
        filtered,
        key=lambda x: x.get("importance", 5) * x.get("count", 1),
        reverse=True,
    )

    top_keywords = scored[:10]
    kw_text = "\n".join(
        f"- {k['keyword']} (중요도:{k.get('importance',5)}, 언급:{k.get('count',1)}) {k.get('reason','')}"
        for k in top_keywords
    )

    prompt = f"""당신은 IT 기술 블로그 에디터입니다.
아래 오늘의 상위 IT 기술 키워드 중에서 블로그 포스팅 주제 1개를 선정하세요.

선정 기준:
1. 일반 독자도 이해 가능한 기술
2. 최근 산업/시장에서 실제로 주목받고 있음
3. 기업 사례가 존재함
4. 투자 추천 없이 기술 설명 가능

반드시 JSON만 출력 (설명 없이):
{{
  "topic": "선정된 기술 키워드",
  "korean_title": "블로그 포스팅 제목 (한국어, SEO 친화적)",
  "reason": "선정 이유 (2줄 이내)",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}

후보 키워드:
{kw_text}
"""
    raw = call_ai(prompt, max_tokens=512)

    import re
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        # 폴백: 1등 키워드 사용
        kw = scored[0]["keyword"]
        return {
            "topic": kw,
            "korean_title": f"오늘 시장이 주목하는 기술: {kw}",
            "reason": scored[0].get("reason", ""),
            "tags": [kw, "IT기술", "반도체", "AI", "산업동향"],
        }
    try:
        return json.loads(match.group())
    except Exception:
        kw = scored[0]["keyword"]
        return {"topic": kw, "korean_title": f"{kw} 완전 해설", "reason": "", "tags": [kw]}

# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    with open(ARTICLES_FILE, encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        print("[ERROR] 기사 없음")
        sys.exit(1)

    article_text = articles_to_text(articles)
    recent_topics = load_recent_topics()
    print(f"최근 30일 발행 토픽: {recent_topics}")

    print("\n[Step 1] 키워드 추출 중...")
    keywords = extract_keywords(article_text)
    print(f"추출된 키워드 {len(keywords)}개: {[k['keyword'] for k in keywords[:10]]}")

    if not keywords:
        print("[ERROR] 키워드 추출 실패")
        sys.exit(1)

    print("\n[Step 2] 토픽 선정 중...")
    topic = select_topic(keywords, recent_topics)
    print(f"선정 토픽: {topic['topic']} → {topic['korean_title']}")

    # 키워드 목록도 함께 저장 (포스팅 생성 시 참조)
    topic["all_keywords"] = keywords[:15]
    topic["source_articles"] = articles

    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        json.dump(topic, f, ensure_ascii=False, indent=2)

    print(f"\n토픽 저장 완료 → {TOPIC_FILE}")

if __name__ == "__main__":
    main()
