"""
02_select_topic.py
OpenRouter Free API를 사용해 기사에서 IT 기술 키워드를 추출하고,
오늘 발행할 최적 토픽 1개를 선정한다.
중복 방지: 최근 30일 발행 이력 참조

개선 사항:
- 토픽 선정 후 관련 기사 수 검증 (최소 3개 이상)
- 관련 기사 부족 시 차순위 토픽으로 자동 교체
- 선정된 토픽의 관련 기사만 source_articles에 저장
- 기사 요약을 토픽 선정 프롬프트에도 충분히 제공
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta

ARTICLES_FILE = "data/raw_articles.json"
HISTORY_FILE  = "data/topic_history.json"
TOPIC_FILE    = "data/selected_topic.json"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# 관련 기사 최소 기준 — 이 수 미만이면 차순위 토픽으로 교체
MIN_RELATED_ARTICLES = 3

MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super:free",
]

TOO_BROAD = {
    "ai", "인공지능", "반도체", "클라우드", "빅데이터", "it", "기술",
    "소프트웨어", "디지털", "데이터", "머신러닝", "딥러닝", "네트워크",
}


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
        req  = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json; charset=utf-8",
                "HTTP-Referer":  "https://github.com",
                "X-Title":       "Tech Blog",
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


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_recent_topics() -> list[str]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        history: list[dict] = json.load(f)
    cutoff = datetime.now() - timedelta(days=30)
    return [
        h["topic"].lower()
        for h in history
        if datetime.fromisoformat(h["date"]) >= cutoff
    ]


def articles_to_text(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("summary"):
            lines.append(f"   {a['summary'][:300]}")  # 120 → 300
    return "\n".join(lines)


def find_related_articles(topic: str, articles: list[dict]) -> list[dict]:
    """
    토픽 키워드가 제목 또는 요약에 포함된 기사를 반환.
    대소문자 무시, 부분 일치.
    """
    topic_lower = topic.lower()
    # 토픽이 여러 단어일 경우 단어 분리해서 각각 검색
    keywords = [w for w in topic_lower.split() if len(w) > 2]

    related = []
    for a in articles:
        text = (a["title"] + " " + a.get("summary", "")).lower()
        # 전체 토픽 일치 우선
        if topic_lower in text:
            related.append(a)
        # 키워드 중 절반 이상 포함 시 관련 기사로 인정
        elif keywords and sum(1 for kw in keywords if kw in text) >= max(1, len(keywords) // 2):
            related.append(a)

    return related


# ── Step 1: 키워드 추출 ───────────────────────────────────────────────────────

def extract_keywords(article_text: str) -> list[dict]:
    prompt = f"""당신은 IT 시장 분석 전문가입니다.
아래 뉴스 기사 목록에서 반복적으로 언급되는 IT 기술 키워드를 추출하세요.

규칙:
- 단순 기업명, 인물명 제외
- 실제 IT 기술, 아키텍처, 표준, 개념만 포함
- 반드시 "구체적인" 기술/개념이어야 함
  (예: HBM, MCP, Agentic AI, CXL, SASE, Physical AI, RAG, LoRA,
       LLM Inference, On-Device AI, Edge AI, Digital Twin, Zero Trust)
- 너무 광범위한 상위 개념(AI, 인공지능, 반도체, 클라우드, 빅데이터, IT, 기술,
  소프트웨어, 디지털)은 절대 추출하지 말 것
- 'AI'가 자주 언급된다면 더 구체적인 하위 기술을 찾아서 추출
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
    raw   = call_ai(prompt, max_tokens=1500)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        print(f"[WARN] 키워드 파싱 실패. 원본:\n{raw[:300]}")
        return []
    try:
        return json.loads(match.group())
    except Exception as e:
        print(f"[WARN] JSON 파싱 오류: {e}")
        return []


# ── Step 2: 토픽 선정 + 관련 기사 수 검증 ────────────────────────────────────

def select_topic(keywords: list[dict], recent_topics: list[str], articles: list[dict]) -> dict:
    # 최근 발행 및 너무 광범위한 키워드 제외
    filtered = [
        kw for kw in keywords
        if kw["keyword"].lower() not in recent_topics
        and kw["keyword"].lower() not in TOO_BROAD
    ]
    if not filtered:
        print("[WARN] 필터링 후 키워드 없음 → 이력 무시하고 재시도")
        filtered = [kw for kw in keywords if kw["keyword"].lower() not in TOO_BROAD] or keywords

    # 중요도 × count 점수 정렬
    scored = sorted(
        filtered,
        key=lambda x: x.get("importance", 5) * x.get("count", 1),
        reverse=True,
    )

    # ── 핵심 개선: 관련 기사 수 검증 후 토픽 선정 ──
    # 상위 후보들 중 관련 기사가 MIN_RELATED_ARTICLES개 이상인 첫 번째 토픽 선택
    validated_keyword = None
    for kw in scored[:10]:
        related = find_related_articles(kw["keyword"], articles)
        print(f"  [{kw['keyword']}] 관련 기사 {len(related)}개")
        if len(related) >= MIN_RELATED_ARTICLES:
            validated_keyword = kw
            break

    if not validated_keyword:
        print(f"[WARN] 관련 기사 {MIN_RELATED_ARTICLES}개 이상인 토픽 없음 → 기사 수 가장 많은 토픽 선택")
        validated_keyword = max(
            scored[:10],
            key=lambda kw: len(find_related_articles(kw["keyword"], articles)),
            default=scored[0],
        )

    # AI에게 최종 제목/태그 생성 요청
    top_keywords = scored[:10]
    kw_text = "\n".join(
        f"- {k['keyword']} (중요도:{k.get('importance',5)}, 언급:{k.get('count',1)}) {k.get('reason','')}"
        for k in top_keywords
    )

    prompt = f"""당신은 IT 기술 블로그 에디터입니다.
아래에서 선정된 주제로 블로그 포스팅 제목과 태그를 생성하세요.

선정된 주제: {validated_keyword['keyword']}
선정 이유: {validated_keyword.get('reason', '')}

선정 기준:
1. 일반 독자도 이해 가능한 기술
2. 최근 산업/시장에서 실제로 주목받고 있음
3. 기업 사례가 존재함
4. 투자 추천 없이 기술 설명 가능

반드시 JSON만 출력 (설명 없이):
{{
  "topic": "{validated_keyword['keyword']}",
  "korean_title": "블로그 포스팅 제목 (한국어, SEO 친화적, 28자 이내)",
  "reason": "선정 이유 (2줄 이내)",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}

참고 후보 키워드 목록:
{kw_text}
"""
    raw   = call_ai(prompt, max_tokens=512)
    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if not match:
        kw = validated_keyword["keyword"]
        return {
            "topic":        kw,
            "korean_title": f"오늘 시장이 주목하는 기술: {kw}",
            "reason":       validated_keyword.get("reason", ""),
            "tags":         [kw, "IT기술", "반도체", "AI", "산업동향"],
        }
    try:
        return json.loads(match.group())
    except Exception:
        kw = validated_keyword["keyword"]
        return {"topic": kw, "korean_title": f"{kw} 완전 해설", "reason": "", "tags": [kw]}


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    with open(ARTICLES_FILE, encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        print("[ERROR] 기사 없음")
        sys.exit(1)

    article_text  = articles_to_text(articles)
    recent_topics = load_recent_topics()
    print(f"최근 30일 발행 토픽: {recent_topics}")

    print("\n[Step 1] 키워드 추출 중...")
    keywords = extract_keywords(article_text)
    print(f"추출된 키워드 {len(keywords)}개: {[k['keyword'] for k in keywords[:10]]}")

    if not keywords:
        print("[ERROR] 키워드 추출 실패")
        sys.exit(1)

    print("\n[Step 2] 토픽 선정 + 관련 기사 수 검증 중...")
    topic = select_topic(keywords, recent_topics, articles)
    print(f"선정 토픽: {topic['topic']} → {topic['korean_title']}")

    # ── 핵심 개선: 관련 기사만 추려서 저장 ──
    related_articles = find_related_articles(topic["topic"], articles)
    print(f"관련 기사 {len(related_articles)}개 → source_articles에 저장")

    # 관련 기사가 너무 적으면 전체 기사에서 보완
    if len(related_articles) < MIN_RELATED_ARTICLES:
        print(f"[WARN] 관련 기사 부족 → 전체 기사 상위 10개로 보완")
        related_articles = articles[:10]

    topic["all_keywords"]    = keywords[:15]
    topic["source_articles"] = related_articles  # 전체 아닌 관련 기사만

    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        json.dump(topic, f, ensure_ascii=False, indent=2)

    print(f"\n토픽 저장 완료 → {TOPIC_FILE}")
    print(f"source_articles: {len(related_articles)}개")


if __name__ == "__main__":
    main()
