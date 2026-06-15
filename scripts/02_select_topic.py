"""
02_select_topic.py
OpenRouter Free API를 사용해 기사에서 IT 기술 키워드를 추출하고,
오늘 발행할 최적 토픽 1개를 선정한다.
중복 방지: 최근 30일 발행 이력 참조

개선 사항:
- 토픽 선정 후 관련 기사 수 검증 (최소 5개 이상)
- 단일/소수 기사 기반의 너무 구체적인 키워드 추출 방지
- 관련 기사 부족 시 차순위 토픽으로 자동 교체
- 선정된 토픽의 관련 기사만 source_articles에 저장
- AI 기반 유사 토픽 감지 (하드코딩 없음)
- 기술 depth를 위한 키워드 추출 강화
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

MIN_RELATED_ARTICLES = 5

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
            lines.append(f"   {a['summary'][:300]}")
    return "\n".join(lines)


def find_related_articles(topic: str, articles: list[dict]) -> list[dict]:
    """
    토픽 키워드가 제목 또는 요약에 포함된 기사를 반환.
    토픽이 3단어 이상이면 최소 2개 단어 일치를 요구.
    """
    topic_lower = topic.lower()
    keywords = [w for w in topic_lower.split() if len(w) > 2]

    if len(keywords) >= 3:
        min_match = 2
    else:
        min_match = max(1, len(keywords) // 2)

    related = []
    for a in articles:
        text = (a["title"] + " " + a.get("summary", "")).lower()
        if topic_lower in text:
            related.append(a)
        elif keywords and sum(1 for kw in keywords if kw in text) >= min_match:
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
       LLM Inference, On-Device AI, Edge AI, Digital Twin, Zero Trust,
       NVLink, Flash Attention, RLHF, Mixture of Experts, Speculative Decoding)
- 너무 광범위한 상위 개념(AI, 인공지능, 반도체, 클라우드, 빅데이터, IT, 기술,
  소프트웨어, 디지털)은 절대 추출하지 말 것
- 반드시 "최소 3개 이상의 서로 다른 기사"에서 공통적으로 언급되는 키워드만 추출
- count가 2 이하로 추정되는 키워드는 추출하지 말 것
- 각 키워드의 기사 언급 횟수(count)와 중요도(importance, 1-10)를 추정
- 반드시 JSON 배열만 출력 (설명 없이)

출력 형식:
[
  {{"keyword": "HBM", "count": 5, "importance": 9, "reason": "반도체 메모리 핵심 기술"}},
  ...
]

뉴스 기사 목록:
{article_text}
"""
    for attempt in range(3):  # 최대 3회 재시도
        raw   = call_ai(prompt, max_tokens=1500)

        # JSON 배열 추출 시도
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            print(f"[WARN] 키워드 파싱 실패 (시도 {attempt+1}). 재시도...")
            continue

        # 흔한 JSON 오류 보정
        json_str = match.group()
        json_str = json_str.replace("'", '"')          # 작은따옴표 → 큰따옴표
        json_str = re.sub(r",\s*]", "]", json_str)    # trailing comma 제거
        json_str = re.sub(r",\s*}", "}", json_str)    # trailing comma 제거

        try:
            result = json.loads(json_str)
            if result:
                return result
            print(f"[WARN] 빈 배열 반환 (시도 {attempt+1}). 재시도...")
        except Exception as e:
            print(f"[WARN] JSON 파싱 오류 (시도 {attempt+1}): {e}")
            continue

    print("[ERROR] 키워드 추출 3회 모두 실패")
    return []


# ── Step 2: 토픽 선정 + 유사 토픽 감지 + 관련 기사 검증 ──────────────────────

def _try_select_topic(
    candidate_kw: dict,
    scored: list[dict],
    recent_topics: list[str],
) -> dict:
    """
    후보 키워드로 AI에게 제목/태그 생성 + 유사 토픽 감지 요청.
    반환: topic dict (reason에 "유사토픽주의" 포함 시 스킵 대상)
    """
    top_keywords = scored[:10]
    kw_text = "\n".join(
        f"- {k['keyword']} (중요도:{k.get('importance',5)}, 언급:{k.get('count',1)}) {k.get('reason','')}"
        for k in top_keywords
    )
    recent_str = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "없음"

    prompt = f"""당신은 IT 기술 블로그 에디터입니다.
아래에서 선정된 주제로 블로그 포스팅 제목과 태그를 생성하세요.

선정된 주제: {candidate_kw['keyword']}
선정 이유: {candidate_kw.get('reason', '')}

【최근 30일 발행 토픽 이력】
{recent_str}

【유사 토픽 판단 규칙 - 중요】
위 발행 이력을 보고, 선정된 주제가 이미 발행된 토픽과 의미적으로 같거나
매우 유사한 범주라고 판단되면 reason 필드에 반드시 "유사토픽주의:"로 시작하는
설명을 포함하세요.
예시: 이력에 "Agentic AI"가 있는데 "AI Agent"가 선정된 경우
     → reason: "유사토픽주의: Agentic AI와 동일한 범주"

유사하지 않다면 reason에 선정 이유만 간략히 작성하세요.

선정 기준:
1. 일반 독자도 이해 가능한 기술
2. 최근 산업/시장에서 실제로 주목받고 있음
3. 기업 사례가 존재함
4. 투자 추천 없이 기술 설명 가능

반드시 JSON만 출력 (설명 없이):
{{
  "topic": "{candidate_kw['keyword']}",
  "korean_title": "블로그 포스팅 제목 (한국어, SEO 친화적, 28자 이내)",
  "reason": "선정 이유 또는 유사토픽주의: ...",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}

참고 후보 키워드 목록:
{kw_text}
"""
    raw   = call_ai(prompt, max_tokens=512)
    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if not match:
        return {
            "topic":        candidate_kw["keyword"],
            "korean_title": f"{candidate_kw['keyword']} 동향과 전망",
            "reason":       candidate_kw.get("reason", ""),
            "tags":         [candidate_kw["keyword"], "IT기술", "반도체", "AI", "산업동향"],
        }
    try:
        return json.loads(match.group())
    except Exception:
        return {
            "topic":        candidate_kw["keyword"],
            "korean_title": f"{candidate_kw['keyword']} 완전 해설",
            "reason":       "",
            "tags":         [candidate_kw["keyword"]],
        }


def select_topic(
    keywords: list[dict],
    recent_topics: list[str],
    articles: list[dict],
):
    """
    반환값: (topic_dict, related_articles) 또는 (None, None)
    """
    # 최근 발행 및 너무 광범위한 키워드 제외
    filtered = [
        kw for kw in keywords
        if kw["keyword"].lower() not in recent_topics
        and kw["keyword"].lower() not in TOO_BROAD
    ]
    if not filtered:
        print("[WARN] 필터링 후 키워드 없음 → 이력 무시하고 재시도")
        filtered = [
            kw for kw in keywords
            if kw["keyword"].lower() not in TOO_BROAD
        ] or keywords

    # 중요도 × count 점수 정렬
    scored = sorted(
        filtered,
        key=lambda x: x.get("importance", 5) * x.get("count", 1),
        reverse=True,
    )

    # 관련 기사 수 검증 + 유사 토픽 감지 → 통과하는 첫 번째 후보 선택
    for kw in scored[:10]:
        # 1) 관련 기사 수 검증
        related = find_related_articles(kw["keyword"], articles)
        print(f"  [{kw['keyword']}] 관련 기사 {len(related)}개")
        if len(related) < MIN_RELATED_ARTICLES:
            print(f"    → 관련 기사 부족 ({len(related)} < {MIN_RELATED_ARTICLES}), 스킵")
            continue

        # 2) AI 유사 토픽 감지
        topic = _try_select_topic(kw, scored, recent_topics)

        if "유사토픽주의" in topic.get("reason", ""):
            print(f"    → 유사 토픽 감지: {topic['reason']} → 차순위로")
            continue

        # 두 조건 모두 통과
        print(f"  [선정] {kw['keyword']} → {topic['korean_title']}")
        return topic, related

    print(f"[ERROR] 관련 기사 {MIN_RELATED_ARTICLES}개 이상 + 유사 토픽 아닌 키워드를 찾지 못함")
    return None, None


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(RESULT_FILE):
        print("[WARN] blog_post.json 없음 → 이력 업데이트 스킵")
        return

    with open(RESULT_FILE, encoding="utf-8") as f:
        result = json.load(f)

    history: list[dict] = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)

    new_entry = {
        "topic":    result["topic"],
        "title":    result["title"],
        "category": result.get("category", ""),
        "url":      result.get("url", ""),
        "tags":     result.get("tags", ""),
        "date":     datetime.now().isoformat(),
    }

    # ── 중복 방지: 오늘 날짜에 같은 토픽이 이미 있으면 추가 안 함 ──
    today = datetime.now().strftime("%Y-%m-%d")
    already_exists = any(
        h["topic"].lower() == new_entry["topic"].lower()
        and h["date"][:10] == today
        for h in history
    )
    if already_exists:
        print(f"[SKIP] 오늘 이미 발행된 토픽: {new_entry['topic']}")
    else:
        history.append(new_entry)

    # 30일 이전 항목 제거
    cutoff  = datetime.now() - timedelta(days=KEEP_DAYS)
    history = [
        h for h in history
        if datetime.fromisoformat(h["date"]) >= cutoff
    ]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"[이력 업데이트] 현재 {len(history)}개 항목 (최근 {KEEP_DAYS}일)")
    for h in history[-5:]:
        print(f"  - {h['date'][:10]} | {h['topic']} | {h['title'][:40]}")
