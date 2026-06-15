"""
06_exam_history.py
03 단계 결과물(blog_post.json)의 topic을 기준으로
정보관리기술사 기출문제(exam_history.json)에서 관련 문제를 검색해
"기출 이력" 섹션을 본문 끝에 추가한다.

개선사항:
- TOPIC_ALIASES 하드코딩 제거 → AI가 동적으로 검색어 생성
- 태그에 'KPC정보관리기술사' 자동 추가
- AI 모델 폴백 로직 개선
- 기출 섹션 HTML 디자인 개선
- 코드 구조 정리
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error

POST_FILE = "data/blog_post.json"
HTML_FILE = "data/blog_post.html"
EXAM_FILE = "data/exam_history.json"

MAX_MATCHES = 5

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super:free",
]

KPE_TAG = "KPC정보관리기술사"


# ─────────────────────────────────────────
# AI 호출
# ─────────────────────────────────────────

def call_ai(prompt: str, max_tokens: int = 300) -> str:
    if not OPENROUTER_API_KEY:
        print("[WARN] OPENROUTER_API_KEY 없음 → AI 검색어 생성 스킵")
        return "[]"

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
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read().decode("utf-8"))
            content = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if content:
                return content.strip()
        except Exception as e:
            print(f"[WARN] {model} 실패: {e}")

    return "[]"


# ─────────────────────────────────────────
# 검색어 생성 (AI 기반, 하드코딩 없음)
# ─────────────────────────────────────────

def build_search_terms(topic: str, title: str, tags: str, exam_data: list[dict]) -> list[str]:
    """
    AI가 토픽/제목/태그를 분석해 기출문제 검색에 적합한 키워드를 동적으로 생성.
    하드코딩된 TOPIC_ALIASES 없이 완전 자동화.
    """
    # 기출문제 샘플로 컨텍스트 제공
    sample_questions = [item["question"][:60] for item in exam_data[:40]]
    sample_text = "\n".join(sample_questions)

    prompt = f"""당신은 정보관리기술사 시험 전문가입니다.
아래 블로그 포스트 정보를 분석해, 기출문제 검색에 사용할 핵심 키워드를 추출하세요.

[블로그 포스트 정보]
- 토픽: {topic}
- 제목: {title}
- 태그: {tags}

[기출문제 샘플 (참고용)]
{sample_text}

[규칙]
- 한국어와 영어 모두 포함
- 약어와 풀네임 모두 포함 (예: AI, 인공지능)
- 기출문제에 실제로 나올 법한 표현 우선
- 6~10개 이내
- JSON 배열 형식만 출력 (설명 없이)

출력 예시: ["Zero Trust", "제로트러스트", "제로 트러스트", "망분리", "접근제어", "IAM"]
"""
    raw = call_ai(prompt, max_tokens=300)
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            terms = json.loads(match.group())
            # 원본 토픽도 항상 포함
            all_terms = list(set([topic] + [t for t in terms if isinstance(t, str) and t.strip()]))
            return all_terms
        except Exception as e:
            print(f"[WARN] 검색어 파싱 실패: {e}")

    # AI 실패 시 토픽 단어 분리로 폴백
    fallback = list(set([topic] + topic.replace("-", " ").split()))
    return fallback


# ─────────────────────────────────────────
# 기출문제 검색
# ─────────────────────────────────────────

def search_exam_questions(terms: list[str], exam_data: list[dict]) -> list[dict]:
    """검색어 중 하나라도 포함된 기출문제 반환 (최신 회차 우선, round=0 제외)"""
    matched = []
    seen_questions = set()

    for item in exam_data:
        if item.get("round", 0) == 0:
            continue
        q = item["question"]
        for term in terms:
            if not term or len(term) < 2:
                continue
            if term.lower() in q.lower():
                if q not in seen_questions:
                    matched.append(item)
                    seen_questions.add(q)
                break

    matched.sort(key=lambda x: x.get("round", 0), reverse=True)
    return matched


# ─────────────────────────────────────────
# 기출 섹션 HTML 생성
# ─────────────────────────────────────────

def build_exam_section_html(matches: list[dict], topic: str) -> str:
    if not matches:
        return ""

    items_html = []
    for m in matches[:MAX_MATCHES]:
        round_no = m.get("round", "")
        subject  = m.get("subject", "")
        q_text   = m.get("question", "")
        q_text   = re.sub(r"^\d+\.\s*", "", q_text).strip()
        if len(q_text) > 120:
            q_text = q_text[:120] + "…"

        items_html.append(
            f'<li style="margin-bottom:10px;line-height:1.75;font-size:0.91em;">'
            f'<span style="display:inline-block;background:#f0f0f0;color:#888;'
            f'font-size:0.78em;padding:1px 7px;border-radius:10px;margin-bottom:3px;">'
            f'제{round_no}회 · {subject}</span><br>'
            f'<span style="color:#444;">{q_text}</span>'
            f'</li>'
        )

    return f"""
<div style="margin-top:2em;padding:20px 24px;background:#f8f9fb;border-left:4px solid #4a6cf7;border-radius:0 8px 8px 0;">
  <p style="font-size:0.8em;font-weight:700;color:#4a6cf7;margin:0 0 6px;letter-spacing:0.8px;text-transform:uppercase;">
    📋 정보관리기술사 기출 연계
  </p>
  <p style="line-height:1.8;margin:0 0 14px;color:#555;font-size:0.93em;">
    오늘 다룬 <strong style="color:#333;">{topic}</strong> 주제는 정보관리기술사 시험에서도 출제된 바 있습니다.
    실무 개념과 함께 시험 맥락으로도 이해해두면 더욱 깊은 학습이 됩니다.
  </p>
  <ul style="padding-left:1.2em;margin:0;list-style:disc;">
    {chr(10).join(items_html)}
  </ul>
</div>
"""


# ─────────────────────────────────────────
# 태그에 KPC정보관리기술사 추가
# ─────────────────────────────────────────

def add_kpe_tag(tags_str: str) -> str:
    """태그 문자열에 KPC정보관리기술사 태그가 없으면 추가"""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    if KPE_TAG not in tags:
        tags.append(KPE_TAG)
    return ", ".join(tags)


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────

def main():
    if not os.path.exists(POST_FILE):
        print("[WARN] blog_post.json 없음 → 스킵")
        return

    if not os.path.exists(EXAM_FILE):
        print(f"[WARN] {EXAM_FILE} 없음 → 기출 이력 스킵")
        return

    with open(POST_FILE, encoding="utf-8") as f:
        post = json.load(f)

    with open(EXAM_FILE, encoding="utf-8") as f:
        exam_data = json.load(f)

    topic = post["topic"]
    title = post.get("title", "")
    tags  = post.get("tags", "")

    print(f"[기출 이력 검색] 토픽: {topic}")

    # 1. AI로 검색어 동적 생성
    terms = build_search_terms(topic, title, tags, exam_data)
    print(f"  검색어: {terms}")

    # 2. 기출문제 검색
    matches = search_exam_questions(terms, exam_data)
    print(f"  매칭된 기출문제: {len(matches)}개")

    # 3. 태그에 KPC정보관리기술사 추가
    updated_tags = add_kpe_tag(tags)
    if updated_tags != tags:
        print(f"  태그 추가: {KPE_TAG}")
    post["tags"] = updated_tags

    # 4. 기출 섹션 HTML 삽입
    if matches:
        for m in matches[:MAX_MATCHES]:
            print(f"    - 제{m['round']}회 {m['subject']}: {m['question'][:50]}")

        exam_section = build_exam_section_html(matches, topic)
        content_html = post["content_html"]

        # 마무리 섹션(배경색 박스) 앞에 삽입, 없으면 맨 뒤에 추가
        marker = '<div style="margin-top:3em;padding:18px 20px;background:#fafafa;'
        idx = content_html.find(marker)
        if idx != -1:
            content_html = content_html[:idx] + exam_section + "\n" + content_html[idx:]
        else:
            content_html += exam_section

        post["content_html"] = content_html
        post["exam_matches"] = [
            {
                "round":    m["round"],
                "subject":  m["subject"],
                "question": m["question"],
            }
            for m in matches[:MAX_MATCHES]
        ]
    else:
        print("  관련 기출문제 없음 → 기출 섹션 스킵")

    # 5. 파일 저장
    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    content_html = post["content_html"]

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content_html)

    with open("data/blog_post.md", "w", encoding="utf-8") as f:
        f.write(f"# {post['title']}\n\n")
        f.write(post.get("content_md", ""))

    print(f"\n[완료] 기출 이력 섹션 + 태그 업데이트 → {POST_FILE}, {HTML_FILE}")


if __name__ == "__main__":
    main()
