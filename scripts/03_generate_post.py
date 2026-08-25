"""
03_generate_post.py
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
import base64
from datetime import datetime, timezone, timedelta

from it_html_builder import (
    md_to_html,
    build_meta_bar,
    render_hero_image,
    render_diagram,
    render_references,
    render_cta_button,
)
from openrouter_free_models import build_model_list, strip_reasoning_blocks, extract_balanced

TOPIC_FILE = "data/selected_topic.json"
POST_FILE  = "data/blog_post.json"

OPENROUTER_API_KEY   = os.environ.get("OPENROUTER_API_KEY")
UNSPLASH_ACCESS_KEY  = os.environ.get("UNSPLASH_ACCESS_KEY")

KST = timezone(timedelta(hours=9))

# ⚠ 하드코딩 슬러그는 OpenRouter가 무료 라인업을 몇 주 단위로 갈아치우며 계속
# 404로 깨졌다(02/07번 스크립트와 동일 문제). 매 실행마다 실제로 살아있는
# 무료 모델 목록을 조회해서 쓴다.
MODELS = build_model_list(limit=15)

# ── 카테고리별 CTA 설정 ───────────────────────────────────────────────────────
# 카테고리 문자열이 키에 포함되면 해당 CTA 자동 적용.
# CTA가 필요 없는 카테고리는 매핑에 넣지 않으면 됨.
CTA_MAP = {
    "커리어": {
        "label":       "기술사 시험 준비, 토픽 토론은 네이버 카페에서!",
        "url":         "https://m.cafe.naver.com/ca-fe/kpcitpe?tc=section_home_my_cafe",   # ← 실제 URL로 교체
        "description": "",
        "button_text": "KPC 정보관리기술사 카페 바로가기 →",
    },
    # 필요하면 추가
    # "보안": { "label": "...", "url": "...", ... },
}

def get_cta(category: str) -> dict | None:
    """카테고리 문자열로 CTA 딕셔너리를 반환. 매칭 없으면 None."""
    for key, cta in CTA_MAP.items():
        if key in category:
            return cta
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 이하 기존 코드 그대로
# ─────────────────────────────────────────────────────────────────────────────

def mermaid_to_image_url(mermaid_code: str) -> str:
    graphbytes = mermaid_code.encode("utf8")
    base64_string = base64.urlsafe_b64encode(graphbytes).decode("ascii")
    return f"https://mermaid.ink/img/{base64_string}?type=png"


def call_ai(prompt: str, max_tokens: int = 6000) -> str:
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY 없음")
        sys.exit(1)
    if not MODELS:
        print("[ERROR] 사용 가능한 무료 모델을 하나도 찾지 못함")
        sys.exit(1)
    for model in MODELS:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            # 리즈닝 모델이 <think> 태그 없이 사고과정을 본문에 그대로 흘려보내는
            # 경우가 있어(02/07번 스크립트와 동일 이슈), 지원 모델에 한해 응답에서
            # reasoning을 제외하도록 요청한다. 미지원 모델엔 무해하게 무시됨.
            "reasoning": {"exclude": True},
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
            with urllib.request.urlopen(req, timeout=90) as r:
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


def fetch_unsplash_image(topic: str):
    if not UNSPLASH_ACCESS_KEY:
        print("[WARN] UNSPLASH_ACCESS_KEY 없음 → 대표 이미지 스킵")
        return None
    url = (
        f"https://api.unsplash.com/search/photos"
        f"?query={urllib.parse.quote(topic)}"
        f"&per_page=1&orientation=landscape&content_filter=high"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}", "Accept-Version": "v1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("results", [])
        if not results:
            return None
        photo = results[0]
        return {
            "url":        photo["urls"]["regular"],
            "thumb":      photo["urls"]["small"],
            "alt":        photo.get("alt_description") or topic,
            "author":     photo["user"]["name"],
            "author_url": photo["user"]["links"]["html"],
            "unsplash_url": photo["links"]["html"],
        }
    except Exception as e:
        print(f"[WARN] Unsplash 이미지 검색 실패: {e}")
        return None


def build_article_context(articles: list, topic: str) -> str:
    topic_lower = topic.lower()
    relevant = [
        a for a in articles
        if topic_lower in a["title"].lower() or topic_lower in a.get("summary", "").lower()
    ][:10] or articles[:10]
    lines = []
    for i, a in enumerate(relevant, 1):
        lines.append(f"[기사{i}] 제목: {a['title']}")
        lines.append(f"       출처: {a.get('source', '')}")
        if a.get("summary"):
            lines.append(f"       내용: {a['summary'][:500]}")
        lines.append("")
    return "\n".join(lines)


NUMERIC_PATTERN    = re.compile(r'\d+(\.\d+)?\s*(%|퍼센트|억|만|천|조|배|달러|원|배출량|감소|증가|단축|절감|향상|성장률|상승)', re.UNICODE)
SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def sanitize_untagged_numerics(text: str) -> str:
    for line in text.split("\n"):
        s = line.strip()
        if NUMERIC_PATTERN.search(s) and not SOURCE_TAG_PATTERN.search(s):
            print(f"  [경고] 출처 미태깅 수치 발견: {s[:80]}...")
    return text


def enforce_three_line_summary(text: str) -> str:
    match = re.search(r'(## 7[^\n]*\n)(.*?)(\Z|## \d)', text, re.DOTALL)
    if not match:
        return text
    section_body = match.group(2)
    after        = match.group(3)
    bullets = [l for l in section_body.split("\n") if l.strip().startswith("- ")]
    if len(bullets) < 3:
        while len(bullets) < 3:
            bullets.append("- (요약 항목 생성 필요)")
        return text[:match.start(2)] + "\n".join(bullets) + "\n" + after
    if len(bullets) > 3:
        return text[:match.start(2)] + "\n".join(bullets[:3]) + "\n" + after
    return text


def generate_diagram(topic_data: dict) -> str:
    topic = topic_data["topic"]
    prompt = f"""'{topic}' 기술의 핵심 구조나 작동 흐름을 보여주는
간단한 Mermaid 다이어그램 코드를 작성하세요.
규칙:
- graph TD 또는 graph LR 형식
- 노드는 5~8개 이내, 한국어 라벨 사용
- 색상 없이 기본 스타일만
- 노드 라벨에는 괄호, 따옴표, 특수문자 사용 완전 금지
- 설명 없이 mermaid 코드만 출력 (코드블록 없이 순수 코드만, 사고과정이나 생각 과정을 절대 출력하지 마세요)
"""
    raw = call_ai(prompt, max_tokens=800)
    cleaned = strip_reasoning_blocks(raw)

    # 리즈닝 모델이 코드펜스도 <think> 태그도 없이 "사용자가 다이어그램을
    # 원한다..." 같은 사고과정을 그대로 흘려보내는 경우가 있다(2026-08-24
    # 실제 발행본에서 mermaid.ink URL에 사고과정 원문이 그대로 박혀 들어간
    # 것을 확인). 실제 Mermaid 문법은 "graph TD/LR" 또는 "flowchart"로 줄
    # 시작하지만, 사고과정 중간에도 "graph TD or graph LR..." 처럼 그
    # 문법을 설명하며 같은 키워드를 언급하는 경우가 많아 첫 매치를 쓰면
    # 안 된다. 실제 코드는 보통 맨 마지막에 오므로 마지막 매치를 쓴다.
    matches = list(re.finditer(
        r"^\s*(?:graph\s+(?:TD|LR|TB|BT|RL)|flowchart\s+(?:TD|LR|TB|BT|RL))\b",
        cleaned, re.MULTILINE | re.IGNORECASE,
    ))
    if not matches:
        print(f"[WARN] 다이어그램 생성 실패 — 유효한 Mermaid 코드를 찾지 못함. 원본 앞부분: {raw[:150]!r}")
        return ""
    code = cleaned[matches[-1].start():].strip()
    # 여전히 사고과정 설명일 뿐(예: 뒤에 실제 노드/화살표가 없음) 최소 검증
    if "-->" not in code and "---" not in code:
        print(f"[WARN] 다이어그램 생성 실패 — 노드 연결(-->)이 없어 유효하지 않음. 원본 앞부분: {raw[:150]!r}")
        return ""
    return code


def generate_body(topic_data: dict) -> str:
    topic    = topic_data["topic"]
    title    = topic_data["korean_title"]
    reason   = topic_data.get("reason", "")
    articles = topic_data.get("source_articles", [])
    ctx      = build_article_context(articles, topic)

    prompt = f"""당신은 정보관리기술사를 준비하는 15년차 현업 개발자입니다.
회사에서 직접 이 분야를 다루고, 시험 준비하며 관련 기술을 다시 정리하는 입장에서 글을 씁니다.
글을 읽는 독자는 AI가 작성한 글을 매우 싫어합니다.
아래 정보를 바탕으로 블로그 포스팅을 작성하세요.

【주제】{topic}
【제목】{title}
【선정 이유】{reason}
【참조 뉴스】
{ctx}

【톤 — 리포트와 개인 블로그의 중간】
- 3인칭 기자 톤이 아니라, 현업에서 직접 부딪혀본 사람의 1인칭 관점을 섞는다
- 리드 문단과 5번 섹션(엔지니어가 봐야 할 포인트)에는 "회사에서", "실무에서 보면", "내가 보기엔" 같은 개인 경험 어투를 자연스럽게 1~2번 넣는다
- 나머지 섹션은 기존처럼 사실 중심 분석 구조를 유지한다 — 감상만 나열하지 않는다
- 반말이나 인터넷 말투(ㅋㅋ, ~인 듯, 이모티콘)는 쓰지 않는다. 존댓말·평서문 유지

【핵심 작성 원칙 — AI 느낌 완전 제거】
- "~에 대해 알아보겠습니다", "살펴보도록 하겠습니다", "정리해보았습니다" 같은 챗봇 문구 절대 금지
- "다양한", "혁신적인", "주목할 만한", "중요한" 같은 무의미한 형용사 사용 금지
- 전문가가 현장에서 직접 보고 분석한 것처럼 구체적으로 서술
- 문장은 짧고 밀도 있게. 한 문장에 하나의 정보만
- 어려운 기술 용어는 처음 등장 시 괄호로 간단히 풀이
- 절대 사용 금지: 최근, 또한, 한편, 즉, 따라서, 다양한, 혁신적인, 중요한, 전망이다, 기대된다

【수치 사용 규칙 — 반드시 준수】
- 수치는 참조 뉴스에 명시된 것만 사용
- 수치 사용 시 문장 끝에 반드시 [출처: 기사제목] 태깅
- 참조 뉴스에 수치 없으면 정성적으로만 서술
- [출처: ] 없는 수치 단정 표현 절대 금지

【작성 규칙】
- 반드시 아래 7개 섹션 구조로 작성
- 각 섹션은 ## 헤딩 사용
- 전체 분량: 2000~3000자
- 이모지, 아이콘, 화살표 기호 사용 금지
- 마크다운 표, 구분선, ">" 인용구 사용 금지

【출력 형식】

(리드 문단 — 헤딩 없이 2~3문장. 구체적 사건/상황으로 시작)

## 1. 현장에서 무슨 일이 있었나
## 2. 왜 업계가 반응하는가
## 3. 기술적으로 보면
- **용어**: 설명 형식으로 핵심 구성요소 3~5개
## 4. 실제 현장 적용 사례
## 5. 엔지니어가 봐야 할 포인트
## 6. 앞으로 볼 포인트
- bullet 정확히 3개
## 7. 3줄 요약
- bullet 정확히 3개
"""
    return call_ai(prompt, max_tokens=6000)


def refine_title(topic_data: dict) -> dict:
    prompt = f"""아래 블로그 제목을 검색 유입에 최적화해서 3개 추천해주세요.

원본 제목: {topic_data['korean_title']}
주제 키워드: {topic_data['topic']}

조건:
- 28자 이내
- 키워드를 제목 앞쪽에 배치
- 숫자로 개수를 암시하는 표현 금지 ("3가지", "5가지" 등)
- 카테고리도 1개 추천

아래는 JSON "형식"을 보여주는 예시일 뿐입니다. <> 안의 설명을 그대로 베껴서
출력하지 말고, 실제 제목·카테고리 문자열로 교체해서 출력하세요.
{{"titles": ["<28자 이내 실제 제목 1>", "<실제 제목 2>", "<실제 제목 3>"], "category": "<추천 카테고리명>"}}

JSON만 출력:
"""
    raw = call_ai(prompt, max_tokens=800)
    json_str = extract_balanced(strip_reasoning_blocks(raw), "{", "}")
    fallback = {"titles": [topic_data["korean_title"]], "category": "IT/테크"}
    if not json_str:
        return fallback
    try:
        result = json.loads(json_str)
    except Exception:
        return fallback

    # 모델이 예시의 플레이스홀더(<...>, "제목1" 등)를 그대로 베껴 반환하는
    # 경우가 있다 — 문법적으로는 완전히 유효한 JSON이라 파싱은 통과하므로
    # 별도로 내용 자체를 검증해야 한다(2026-08-25 실제 발행본에서 "제목1"이
    # 그대로 제목으로 나간 것을 확인).
    titles = result.get("titles") or []
    real_titles = [
        t for t in titles
        if isinstance(t, str) and t.strip()
        and not re.match(r"^\s*<.*>\s*$", t)          # <실제 제목 1> 형태
        and not re.match(r"^제목\s*\d*$", t.strip())   # 제목1, 제목2 형태
    ]
    if not real_titles:
        print(f"[WARN] 제목 후보가 전부 플레이스홀더로 보여 원본 제목으로 대체: {titles}")
        return fallback
    result["titles"] = real_titles
    if not result.get("category") or re.match(r"^\s*<.*>\s*$", str(result.get("category"))):
        result["category"] = "IT/테크"
    return result


def markdown_to_plain(md: str, title: str) -> str:
    """마크다운 기호를 제거해 다른 곳(네이버 등)에 가끔 복붙해도 되는 평문으로
    변환. AI 재생성 없이 문자열 치환만으로 처리 — HTML 렌더링용 md 구조는
    그대로 유지하면서, 사람이 읽는 사본만 따로 만든다."""
    text = md

    # [출처: ...] 태그 제거 (평문에서는 각주 링크가 의미 없음)
    text = re.sub(r"\s*\[출처\s*:\s*.+?\]", "", text)

    # 헤딩: "## 1. 제목" -> "■ 제목" (섹션 구분은 남기되 기호는 정리)
    def _heading(m):
        return f"\n■ {m.group(1).strip()}\n"
    text = re.sub(r"^##\s*(?:\d+\.\s*)?(.+)$", _heading, text, flags=re.MULTILINE)

    # 굵게: **텍스트** -> 텍스트
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    # 리스트: "- " -> "· "
    text = re.sub(r"^[-*]\s+", "· ", text, flags=re.MULTILINE)

    # 연속 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return f"{title}\n\n{text}"


def main():
    if not os.path.exists(TOPIC_FILE):
        print(f"[ERROR] {TOPIC_FILE} 파일이 없습니다.")
        sys.exit(1)

    now_kst = datetime.now(KST)

    with open(TOPIC_FILE, encoding="utf-8") as f:
        topic_data = json.load(f)

    topic    = topic_data["topic"]
    title    = topic_data["korean_title"]
    tags     = topic_data.get("tags", [topic, "IT기술", "기술트렌드"])
    articles = topic_data.get("source_articles", [])

    print(f"[포스팅 생성] 주제: {topic}")
    print(f"[포스팅 생성] 제목: {title}")

    # 1. 대표 이미지
    print("\n[대표 이미지 검색 중...]")
    hero_image = fetch_unsplash_image(topic)

    # 2. 본문 생성
    body_md = generate_body(topic_data)
    body_md = sanitize_untagged_numerics(body_md)
    body_md = enforce_three_line_summary(body_md)

    # 3. 구성도
    diagram_url = ""
    try:
        diagram_code = generate_diagram(topic_data)
        if diagram_code:
            diagram_url = mermaid_to_image_url(diagram_code)
    except Exception as e:
        print(f"[WARN] 구성도 생성 실패: {e}")

    # 4. 제목·카테고리 추천
    print("\n[제목/카테고리 추천 중...]")
    refined          = refine_title(topic_data)
    title_candidates = refined.get("titles", [title])
    category         = refined.get("category", "IT/테크")
    final_title      = title_candidates[0] if title_candidates else title
    print(f"[제목] {title_candidates}  [카테고리] {category}")

    # 5. CTA 자동 선택 ─────────────────────────────────────────────────────────
    cta = CTA_MAP["커리어"]
    #cta = get_cta(category)

    # 6. HTML 변환 (cta는 md_to_html에 한 번만 전달)
    relevant_articles = articles[:8]
    content_html = md_to_html(body_md, relevant_articles)

    # 7. 메타바 삽입
    meta_bar_html = build_meta_bar(topic, tags, now_kst)
    content_html  = content_html.replace("{META_BAR}", meta_bar_html)

    # 8. 대표 이미지 삽입
    if hero_image:
        hero_html    = render_hero_image(hero_image)
        content_html = content_html.replace(meta_bar_html, meta_bar_html + hero_html, 1)

    # 9. 구성도 삽입
    if diagram_url:
        diagram_html = render_diagram(diagram_url, topic)
        marker       = '>CORE</span>'
        idx          = content_html.find(marker)
        if idx != -1:
            h2_start     = content_html.rfind('<h2', 0, idx)
            if h2_start != -1:
                content_html = content_html[:h2_start] + diagram_html + content_html[h2_start:]
        else:
            content_html += diagram_html

    # 10. 참고 기사 삽입
    if relevant_articles:
        references_html = render_references(relevant_articles)
        marker          = '<div style="margin-top:2em;'
        idx             = content_html.rfind(marker)
        if idx != -1:
            content_html = content_html[:idx] + references_html + content_html[idx:]
    if cta:
        from it_html_builder import render_cta_button
        cta_html=render_cta_button(**cta)
        marker  ='<div style="margin-top:2em;'
        idx =content_html.rfind(marker)
        if idx!=-1:
            content_html =content_html[:idx]+cta_html+content_html[idx:]
        #print(f"[CTA] '{category}' 카테고리 → CTA 자동 삽입: {cta['label']}")
    else:
        print(f"[CTA] '{category}' 카테고리 → CTA 없음")

    # 11. 저장
    post = {
        "title":            final_title,
        "title_candidates": title_candidates,
        "category":         category,
        "topic":            topic,
        "content_html":     content_html,
        "content_md":       body_md,
        "tags":             ",".join(tags),
        "created_at":       now_kst.isoformat(),
        "hero_image":       hero_image,
    }

    os.makedirs("data", exist_ok=True)
    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)
    with open("data/blog_post.html", "w", encoding="utf-8") as f:
        f.write(content_html)
    with open("data/blog_post.md", "w", encoding="utf-8") as f:
        f.write(f"# {final_title}\n\n{body_md}")

    # 12. 복붙용 평문 버전 저장 (마크다운 기호 제거) — Naver 등 다른 곳에
    # 가끔 그대로 붙여넣을 수 있도록. AI 재생성 없이 문자열 치환만 사용.
    plain_text = markdown_to_plain(body_md, final_title)
    with open("data/blog_post_plain.txt", "w", encoding="utf-8") as f:
        f.write(plain_text)

    print(f"\n포스팅 저장 완료 → {POST_FILE}")
    print("복붙용 평문 저장 완료 → data/blog_post_plain.txt")


if __name__ == "__main__":
    main()
