"""
06_exam_history.py
03 단계 결과물(blog_post.json)의 topic을 기준으로
정보관리기술사 기출문제(exam_history.json)에서 관련 문제를 검색해
"기출 이력" 섹션을 본문 끝에 추가한다.
"""

import json
import os
import re

POST_FILE = "data/blog_post.json"
HTML_FILE = "data/blog_post.html"
EXAM_FILE = "data/exam_history.json"

MAX_MATCHES = 5

TOPIC_ALIASES = {
    "hbm": ["HBM", "고대역폭메모리", "고대역폭 메모리"],
    "on-device ai": ["온디바이스", "On-Device", "엣지 AI", "Edge AI"],
    "edge ai": ["엣지 AI", "Edge AI", "온디바이스"],
    "agentic ai": ["에이전트", "Agentic", "AI 에이전트"],
    "digital twin": ["디지털트윈", "디지털 트윈"],
    "rag": ["RAG", "검색증강생성"],
    "physical ai": ["피지컬 AI", "Physical AI"],
    "zero trust": ["제로트러스트", "Zero Trust", "제로 트러스트"],
    "quantum computing": ["양자컴퓨팅", "양자 컴퓨팅", "Quantum"],
    "llm inference": ["LLM", "추론", "Inference"],
    "ai governance": ["AI 거버넌스", "거버넌스", "Governance"],
    "ai data center": ["데이터센터", "AI 데이터센터"],
    "mcp": ["MCP", "Model Context Protocol"],
}


def build_search_terms(topic: str) -> list[str]:
    topic_lower = topic.lower().strip()
    terms = set()
    terms.add(topic)

    for key, aliases in TOPIC_ALIASES.items():
        if key in topic_lower or topic_lower in key:
            terms.update(aliases)

    for w in re.split(r"[\s\-_/]+", topic):
        if len(w) >= 3:
            terms.add(w)

    return list(terms)


def search_exam_questions(terms: list[str], exam_data: list[dict]) -> list[dict]:
    """검색어 중 하나라도 포함된 기출문제 반환 (최신 회차 우선, round=0 제외)"""
    matched = []
    seen_questions = set()

    for item in exam_data:
        if item.get("round", 0) == 0:
            continue
        q = item["question"]
        for term in terms:
            if not term:
                continue
            if term.lower() in q.lower():
                if q not in seen_questions:
                    matched.append(item)
                    seen_questions.add(q)
                break

    matched.sort(key=lambda x: x.get("round", 0), reverse=True)
    return matched

def build_exam_section_html(matches: list[dict], topic: str) -> str:
    if not matches:
        return ""

    items_html = []
    for m in matches[:MAX_MATCHES]:
        round_no = m.get("round", "")
        subject  = m.get("subject", "")
        q_text   = m.get("question", "")
        q_text = re.sub(r"^\d+\.\s*", "", q_text)
        if len(q_text) > 120:
            q_text = q_text[:120] + "..."

        items_html.append(
            f'<li style="margin-bottom:8px;line-height:1.7;font-size:0.92em;">'
            f'<span style="color:#aaa;font-size:0.85em;">제{round_no}회 · {subject}</span><br>'
            f'{q_text}</li>'
        )

    return f"""
<div style="margin-top:1.5em;padding:16px 20px;background:#fcfcfc;border:1px solid #eee;border-radius:8px;">
<p style="font-size:0.85em;font-weight:700;color:#999;margin:0 0 10px;letter-spacing:0.5px;">기술사 기출 연계</p>
<p style="line-height:1.8;margin:0 0 10px;color:#777;font-size:0.92em;">
오늘 다룬 <strong style="color:#555;">{topic}</strong>은 정보관리기술사 시험에서도 출제된 적이 있는 주제입니다.
</p>
<ul style="padding-left:1.3em;margin:0;">
{chr(10).join(items_html)}
</ul>
</div>
"""

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
    print(f"[기출 이력 검색] 토픽: {topic}")

    terms = build_search_terms(topic)
    print(f"  검색어: {terms}")

    matches = search_exam_questions(terms, exam_data)
    print(f"  매칭된 기출문제: {len(matches)}개")

    if not matches:
        print("  관련 기출문제 없음 → 섹션 추가 스킵")
        return

    for m in matches[:MAX_MATCHES]:
        print(f"    - 제{m['round']}회 {m['subject']}: {m['question'][:50]}")

    exam_section = build_exam_section_html(matches, topic)

    content_html = post["content_html"]
    marker = '<div style="margin-top:3em;padding:18px 20px;background:#fafafa;'
    idx = content_html.find(marker)
    if idx != -1:
        content_html = content_html[:idx] + exam_section + "\n" + content_html[idx:]
    else:
        content_html += exam_section

    post["content_html"] = content_html
    post["exam_matches"] = [
        {"round": m["round"], "subject": m["subject"], "question": m["question"]}
        for m in matches[:MAX_MATCHES]
    ]

    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content_html)

    print(f"\n[기출 이력 섹션 추가 완료] → {POST_FILE}, {HTML_FILE}")


if __name__ == "__main__":
    main()
