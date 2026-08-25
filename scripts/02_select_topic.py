"""
02_select_topic.py
OpenRouter Free API를 사용해 기사에서 IT 기술 키워드를 추출하고,
오늘 발행할 최적 토픽 1개를 선정한다.
중복 방지: 최근 30일 발행 이력 참조

수정사항:
- main() 함수 전면 재작성 (selected_topic.json 저장 로직 누락 버그 수정)
- source_articles를 selected_topic.json에 포함하여 03번 스크립트로 전달
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from openrouter_free_models import build_model_list, strip_reasoning_blocks, extract_balanced, salvage_json_array

ARTICLES_FILE = "data/raw_articles.json"
HISTORY_FILE  = "data/topic_history.json"
TOPIC_FILE    = "data/selected_topic.json"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MIN_RELATED_ARTICLES = 5

# ⚠ 하드코딩 슬러그는 OpenRouter가 무료 라인업을 몇 주 단위로 갈아치우면서
# 계속 404로 죽는 걸 반복 경험했다 (2026-08-24 실행 로그 참고).
# 근본 해결: 매 실행마다 openrouter_free_models.build_model_list()로
# "지금 시점에 실제로 살아있는" 무료 모델 목록을 조회해서 사용한다.
MODELS = build_model_list(limit=15)

TOO_BROAD = {
    "ai", "인공지능", "반도체", "클라우드", "빅데이터", "it", "기술",
    "소프트웨어", "디지털", "데이터", "머신러닝", "딥러닝", "네트워크",
}


# ── OpenRouter 호출 ───────────────────────────────────────────────────────────

def call_ai(prompt: str, max_tokens: int = 2500, exclude_models: set | None = None,
            used_model_out: list | None = None) -> str:
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY 없음")
        sys.exit(1)
    if not MODELS:
        print("[ERROR] 사용 가능한 무료 모델을 하나도 찾지 못함")
        sys.exit(1)

    exclude_models = exclude_models or set()
    # 이번 호출에서 제외할 모델(직전 시도에서 파싱 불가능한 사고과정만
    # 늘어놓은 모델 등)을 뺀 목록. 전부 제외돼서 남는 게 없으면 그냥
    # 원래 목록으로 재시도한다(모델이 하나도 없는 것보단 낫다).
    models_to_try = [m for m in MODELS if m not in exclude_models] or MODELS

    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            # 리즈닝 모델이 <think> 태그 없이 본문에 사고과정을 그대로 흘려보내는
            # 경우가 있어(2026-08-24 nemotron-3.5-lightning, nemotron-3-ultra
            # 실제 관측), 지원되는 모델에 한해 reasoning을 응답 content에서
            # 제외하도록 요청한다. 미지원 모델에는 무해하게 무시된다.
            "reasoning": {"exclude": True},
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
                if used_model_out is not None:
                    used_model_out.append(model)
                return content.strip()
            print(f"[WARN] {model} 응답 없음, 다음 모델 시도")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"[WARN] {model} 실패: {e.code} - {body[:200]}")
        except Exception as e:
            print(f"[WARN] {model} 예외: {e}")

    print("[ERROR] 모든 모델 실패")
    sys.exit(1)


# ── JSON 추출 유틸은 openrouter_free_models.py로 이동 (07번 스크립트와 공유) ──


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
- 반드시 유효한 JSON 배열만 출력 (설명, 마크다운 코드블록 없이 순수 JSON만)
- 큰따옴표만 사용 (작은따옴표 절대 금지)

출력 형식 예시:
[
  {{"keyword": "HBM", "count": 5, "importance": 9, "reason": "반도체 메모리 핵심 기술"}},
  {{"keyword": "Edge AI", "count": 4, "importance": 8, "reason": "엣지 추론 기술"}}
]

뉴스 기사 목록:
{article_text}
"""

    # 파싱 불가능한 응답만 계속 내놓는 모델은 다음 시도에서 제외한다.
    # (2026-08-24 nemotron-3-ultra-550b-a55b:free가 사고과정만 3500토큰 내내
    # 늘어놓고 JSON을 한 번도 못 낸 채 매번 같은 모델이 다시 뽑히는 것을 확인 —
    # call_ai는 "응답이 왔는지"만 보고 성공 처리하므로, 실제로 쓸모 있는
    # 응답인지는 호출부에서 걸러서 다음 모델로 넘겨야 한다.)
    bad_models: set[str] = set()

    for attempt in range(3):
        used_model: list[str] = []
        raw = call_ai(prompt, max_tokens=6000, exclude_models=bad_models, used_model_out=used_model)
        cleaned = strip_reasoning_blocks(raw)

        json_str = extract_balanced(cleaned, "[", "]")
        if not json_str:
            # 완전히 닫힌 배열은 못 찾았지만, max_tokens에 걸려 끝만 잘렸을
            # 수 있으니 이미 완성된 항목이라도 살려본다.
            salvaged = salvage_json_array(cleaned)
            if salvaged:
                print(f"  → 응답이 중간에 잘렸지만 완성된 항목 {len(salvaged)}개 복구")
                return salvaged
            print(f"[WARN] 키워드 파싱 실패 (시도 {attempt+1}) — 배열을 찾지 못함. 원본 앞부분: {raw[:200]!r}")
            if used_model:
                print(f"  → 다음 시도에서 {used_model[0]} 제외")
                bad_models.add(used_model[0])
            continue

        json_str = re.sub(r",\s*]", "]", json_str)
        json_str = re.sub(r",\s*}", "}", json_str)

        try:
            result = json.loads(json_str)
            if result:
                return result
            print(f"[WARN] 빈 배열 반환 (시도 {attempt+1}). 재시도...")
        except Exception as e:
            print(f"[WARN] JSON 파싱 오류 (시도 {attempt+1}): {e} — 추출된 문자열: {json_str[:200]!r}")
            if used_model:
                bad_models.add(used_model[0])
            continue

    print("[ERROR] 키워드 추출 3회 모두 실패")
    return []


# ── Step 2: 토픽 선정 ──────────────────────────────────────────────────────

def _try_select_topic(
    candidate_kw: dict,
    scored: list[dict],
    recent_topics: list[str],
) -> dict:
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
    raw   = call_ai(prompt, max_tokens=1500)
    json_str = extract_balanced(strip_reasoning_blocks(raw), "{", "}")

    if not json_str:
        return {
            "topic":        candidate_kw["keyword"],
            "korean_title": f"{candidate_kw['keyword']} 동향과 전망",
            "reason":       candidate_kw.get("reason", ""),
            "tags":         [candidate_kw["keyword"], "IT기술", "반도체", "AI", "산업동향"],
        }
    try:
        return json.loads(json_str)
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

    scored = sorted(
        filtered,
        key=lambda x: x.get("importance", 5) * x.get("count", 1),
        reverse=True,
    )

    for kw in scored[:10]:
        related = find_related_articles(kw["keyword"], articles)
        print(f"  [{kw['keyword']}] 관련 기사 {len(related)}개")
        if len(related) < MIN_RELATED_ARTICLES:
            print(f"    → 관련 기사 부족 ({len(related)} < {MIN_RELATED_ARTICLES}), 스킵")
            continue

        topic = _try_select_topic(kw, scored, recent_topics)

        if "유사토픽주의" in topic.get("reason", ""):
            print(f"    → 유사 토픽 감지: {topic['reason']} → 차순위로")
            continue

        print(f"  [선정] {kw['keyword']} → {topic['korean_title']}")
        return topic, related

    print(f"[ERROR] 관련 기사 {MIN_RELATED_ARTICLES}개 이상 + 유사 토픽 아닌 키워드를 찾지 못함")
    return None, None


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    # 1) 수집된 기사 로드
    if not os.path.exists(ARTICLES_FILE):
        print(f"[ERROR] {ARTICLES_FILE} 없음 — 01_collect_news.py를 먼저 실행하세요")
        sys.exit(1)

    with open(ARTICLES_FILE, encoding="utf-8") as f:
        articles: list[dict] = json.load(f)

    if not articles:
        print("[ERROR] 수집된 기사가 없습니다")
        sys.exit(1)

    print(f"[로드] 기사 {len(articles)}개")

    # 2) 최근 발행 이력 로드
    recent_topics = load_recent_topics()
    print(f"[이력] 최근 30일 발행 토픽: {recent_topics or '없음'}")

    # 3) 키워드 추출
    print("\n[키워드 추출 중...]")
    article_text = articles_to_text(articles)
    keywords = extract_keywords(article_text)

    if not keywords:
        print("[ERROR] 키워드 추출 실패")
        sys.exit(1)

    print(f"[키워드] {len(keywords)}개 추출됨:")
    for kw in keywords[:10]:
        print(f"  - {kw['keyword']} (중요도:{kw.get('importance',0)}, 언급:{kw.get('count',0)})")

    # 4) 토픽 선정
    print("\n[토픽 선정 중...]")
    topic_data, related_articles = select_topic(keywords, recent_topics, articles)

    if topic_data is None:
        print("[ERROR] 적합한 토픽을 선정하지 못했습니다")
        sys.exit(1)

    # 5) selected_topic.json 저장 (source_articles 포함)
    os.makedirs("data", exist_ok=True)
    topic_data["source_articles"] = related_articles or []

    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        json.dump(topic_data, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] 선정된 토픽: {topic_data['topic']}")
    print(f"[완료] 블로그 제목: {topic_data['korean_title']}")
    print(f"[완료] 관련 기사: {len(topic_data['source_articles'])}개")
    print(f"[완료] 저장 경로: {TOPIC_FILE}")


if __name__ == "__main__":
    main()
