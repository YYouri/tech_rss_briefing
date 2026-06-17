"""
03_generate_post.py
OpenRouter Free API로 블로그 포스팅 본문을 생성하고 HTML로 변환한다.

이번 수정 — 디자인 시스템 통일:
- 렌더링 로직을 it_html_builder.py 로 분리.
  market_html_builder.py(Stock)와 동일한 토큰(여백/라운드/헤딩 바+배지/리드박스/요약박스 구조)을
  공유하면서 포인트 컬러만 시안 계열로 분기.
- 기존 콘텐츠 생성 로직(call_ai, generate_body, generate_diagram, refine_title,
  fetch_unsplash_image)은 그대로 유지.
- 출처 미태깅 수치는 제거하지 않고 경고만 출력 (이전 수정 유지).
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
)

TOPIC_FILE = "data/selected_topic.json"
POST_FILE  = "data/blog_post.json"

OPENROUTER_API_KEY   = os.environ.get("OPENROUTER_API_KEY")
UNSPLASH_ACCESS_KEY  = os.environ.get("UNSPLASH_ACCESS_KEY")

KST = timezone(timedelta(hours=9))

MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-26b-a4b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-405b-instruct:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────

def mermaid_to_image_url(mermaid_code: str) -> str:
    graphbytes = mermaid_code.encode("utf8")
    base64_string = base64.urlsafe_b64encode(graphbytes).decode("ascii")
    return f"https://mermaid.ink/img/{base64_string}?type=png"


def call_ai(prompt: str, max_tokens: int = 4096) -> str:
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


# ──────────────────────────────────────────
# 대표 이미지 — Unsplash
# ──────────────────────────────────────────

def fetch_unsplash_image(topic: str):
    if not UNSPLASH_ACCESS_KEY:
        print("[WARN] UNSPLASH_ACCESS_KEY 없음 → 대표 이미지 스킵")
        return None

    url = (
        f"https://api.unsplash.com/search/photos"
        f"?query={urllib.parse.quote(topic)}"
        f"&per_page=1&orientation=landscape"
        f"&content_filter=high"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("results", [])
        if not results:
            print(f"[WARN] Unsplash 검색 결과 없음: {topic}")
            return None
        photo = results[0]
        return {
            "url":          photo["urls"]["regular"],
            "thumb":        photo["urls"]["small"],
            "alt":          photo.get("alt_description") or topic,
            "author":       photo["user"]["name"],
            "author_url":   photo["user"]["links"]["html"],
            "unsplash_url": photo["links"]["html"],
        }
    except Exception as e:
        print(f"[WARN] Unsplash 이미지 검색 실패: {e}")
        return None


# ──────────────────────────────────────────
# 기사 컨텍스트 빌더
# ──────────────────────────────────────────

def build_article_context(articles: list, topic: str) -> str:
    topic_lower = topic.lower()
    relevant = [
        a for a in articles
        if topic_lower in a["title"].lower() or topic_lower in a.get("summary", "").lower()
    ][:10]
    if not relevant:
        relevant = articles[:10]

    lines = []
    for i, a in enumerate(relevant, 1):
        lines.append(f"[기사{i}] 제목: {a['title']}")
        lines.append(f"       출처: {a.get('source', '')}")
        if a.get("summary"):
            lines.append(f"       내용: {a['summary'][:500]}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────
# 수치 후처리 — 제거 대신 경고만 출력
# ──────────────────────────────────────────

NUMERIC_PATTERN = re.compile(
    r'\d+(\.\d+)?'
    r'\s*'
    r'(%|퍼센트|억|만|천|조|배|달러|원|배출량|감소|증가|단축|절감|향상|성장률|상승)',
    re.UNICODE
)
SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def sanitize_untagged_numerics(text: str) -> str:
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if NUMERIC_PATTERN.search(stripped) and not SOURCE_TAG_PATTERN.search(stripped):
            print(f"  [경고] 출처 미태깅 수치 발견: {stripped[:80]}...")
    return text


def enforce_three_line_summary(text: str) -> str:
    match = re.search(r'(## 7[^\n]*\n)(.*?)(\Z|## \d)', text, re.DOTALL)
    if not match:
        return text

    section_body = match.group(2)
    after        = match.group(3)

    bullets = [l for l in section_body.split("\n") if l.strip().startswith("- ")]

    if len(bullets) < 3:
        print(f"  [후처리 경고] 3줄 요약 bullet {len(bullets)}개 — 3개 미만")
        while len(bullets) < 3:
            bullets.append("- (요약 항목 생성 필요)")
        fixed_body = "\n".join(bullets) + "\n"
        return text[:match.start(2)] + fixed_body + after

    if len(bullets) > 3:
        print(f"  [후처리] 3줄 요약 bullet {len(bullets)}개 → 3개로 축소")
        fixed_body = "\n".join(bullets[:3]) + "\n"
        return text[:match.start(2)] + fixed_body + after

    return text


# ──────────────────────────────────────────
# 다이어그램 생성
# ──────────────────────────────────────────

def generate_diagram(topic_data: dict) -> str:
    topic = topic_data["topic"]
    prompt = f"""'{topic}' 기술의 핵심 구조나 작동 흐름을 보여주는
간단한 Mermaid 다이어그램 코드를 작성하세요.

규칙:
- graph TD 또는 graph LR 형식
- 노드는 5~8개 이내, 한국어 라벨 사용
- 색상 없이 기본 스타일만
- 노드 라벨에는 괄호, 따옴표, 특수문자 사용 완전 금지
- 설명 없이 mermaid 코드만 출력 (코드블록 없이 순수 코드만)
"""
    raw = call_ai(prompt, max_tokens=300)
    raw = re.sub(r"```mermaid|```", "", raw).strip()
    return raw


# ──────────────────────────────────────────
# 본문 생성
# ──────────────────────────────────────────

def generate_body(topic_data: dict) -> str:
    topic    = topic_data["topic"]
    title    = topic_data["korean_title"]
    reason   = topic_data.get("reason", "")
    articles = topic_data.get("source_articles", [])
    ctx      = build_article_context(articles, topic)

    prompt = f"""당신은 15년 경력의 IT 전문 기자이자 현업 엔지니어 출신 칼럼니스트다.
글을 읽는 독자는 AI가 작성한 글을 매우 싫어한다.
반도체·AI·소프트웨어 분야를 현장 취재하며 기업 CTO, 연구소장과 인터뷰해온 실무 전문가입니다.
아래 정보를 바탕으로 블로그 포스팅을 작성하세요.

【주제】{topic}
【제목】{title}
【선정 이유】{reason}
【참조 뉴스】
{ctx}

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
    return call_ai(prompt, max_tokens=4096)


# ──────────────────────────────────────────
# 제목 추천
# ──────────────────────────────────────────

def refine_title(topic_data: dict) -> dict:
    prompt = f"""아래 블로그 제목을 검색 유입에 최적화해서 3개 추천해주세요.

원본 제목: {topic_data['korean_title']}
주제 키워드: {topic_data['topic']}

조건:
- 28자 이내
- 키워드를 제목 앞쪽에 배치
- 숫자로 개수를 암시하는 표현 금지 ("3가지", "5가지" 등)
- 카테고리도 1개 추천

JSON만 출력:
{{"titles": ["제목1", "제목2", "제목3"], "category": "추천 카테고리"}}
"""
    raw = call_ai(prompt, max_tokens=300)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {"titles": [topic_data["korean_title"]], "category": "IT/테크"}


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    if not os.path.exists(TOPIC_FILE):
        print(f"[ERROR] {TOPIC_FILE} 파일이 없습니다.")
        print("       02_select_topic.py를 먼저 실행하세요.")
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
    print(f"[포스팅 생성] 관련 기사: {len(articles)}개")

    # 1. 대표 이미지 검색
    print("\n[대표 이미지 검색 중...]")
    hero_image = fetch_unsplash_image(topic)
    if hero_image:
        print(f"[대표 이미지 OK] {hero_image['url'][:60]}...")
    else:
        print("[대표 이미지 없음] 스킵")

    # 2. 본문 생성
    body_md = generate_body(topic_data)
    print(f"\n[본문 생성 완료] {len(body_md)}자")

    body_md = sanitize_untagged_numerics(body_md)
    body_md = enforce_three_line_summary(body_md)

    # 3. 구성도 생성
    print("\n[구성도 생성 중...]")
    diagram_url = ""
    try:
        diagram_code = generate_diagram(topic_data)
        diagram_url  = mermaid_to_image_url(diagram_code)
        print(f"[구성도 URL] {diagram_url[:80]}...")
    except Exception as e:
        print(f"[WARN] 구성도 생성 실패: {e}")

    # 4. HTML 변환 (디자인 시스템 통일된 it_html_builder 사용)
    relevant_articles = articles[:8] if articles else []
    content_html = md_to_html(body_md, relevant_articles)

    # 5. 메타바 삽입 (Stock의 {DASHBOARD}와 동일한 패턴)
    meta_bar_html = build_meta_bar(topic, tags, now_kst)
    content_html  = content_html.replace("{META_BAR}", meta_bar_html)

    # 6. 대표 이미지 삽입 (메타바 바로 다음)
    if hero_image:
        hero_html = render_hero_image(hero_image)
        content_html = content_html.replace(meta_bar_html, meta_bar_html + hero_html, 1)

    # 7. 구성도 삽입 (CORE 섹션 앞)
    if diagram_url:
        diagram_html = render_diagram(diagram_url, topic)
        marker = '>CORE</span>'
        idx = content_html.find(marker)
        if idx != -1:
            h2_start = content_html.rfind('<h2', 0, idx)
            if h2_start != -1:
                content_html = content_html[:h2_start] + diagram_html + content_html[h2_start:]
        else:
            content_html += diagram_html

    # 8. 참고 기사 삽입 (면책 박스 앞)
    if relevant_articles:
        references_html = render_references(relevant_articles)
        marker = '<div style="margin-top:2em;'
        idx = content_html.rfind(marker)
        if idx != -1:
            content_html = content_html[:idx] + references_html + content_html[idx:]

    # 9. 제목 추천
    print("\n[제목/카테고리 추천 중...]")
    refined          = refine_title(topic_data)
    title_candidates = refined.get("titles", [title])
    category         = refined.get("category", "IT/테크")
    final_title      = title_candidates[0] if title_candidates else title

    print(f"[제목 추천] {title_candidates}")
    print(f"[카테고리] {category}")

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
        f.write(f"# {final_title}\n\n")
        f.write(body_md)

    print(f"\n포스팅 저장 완료 → {POST_FILE}")


if __name__ == "__main__":
    main()
