"""
03_generate_post.py
OpenRouter Free API로 블로그 포스팅 본문을 생성하고 HTML로 변환한다.

개선 사항:
- 기사 요약 150자 → 500자로 확장
- 수치 사용 시 [출처: 기사제목] 태깅 강제
- 후처리에서 미태깅 수치 문장 자동 제거
- 출처 태그를 HTML 각주 스타일로 변환
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import base64
from datetime import datetime

TOPIC_FILE = "data/selected_topic.json"
POST_FILE  = "data/blog_post.json"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super:free",
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
# 기사 컨텍스트 빌더 — 500자로 확장
# ──────────────────────────────────────────

def build_article_context(articles: list[dict], topic: str) -> str:
    """
    참조 기사를 AI에게 넘길 컨텍스트로 변환.
    - 요약을 500자까지 포함 (기존 150자에서 확장)
    - 기사 제목을 인덱스와 함께 제공해 출처 태깅에 활용
    """
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
            # 500자로 확장
            lines.append(f"       내용: {a['summary'][:500]}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────
# 수치 후처리 — 미태깅 수치 문장 제거
# ──────────────────────────────────────────

# 수치가 포함된 패턴: 숫자 + % 또는 단위(억, 만, 배, 개월 등)
NUMERIC_PATTERN = re.compile(
    r'\d+(\.\d+)?'           # 숫자
    r'\s*'
    r'(%|억|만|천|조|배|개|명|건|회|달러|원|배포|배출|감소|증가|단축|절감|향상|성장|상승)',
    re.UNICODE
)
SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def sanitize_untagged_numerics(text: str) -> str:
    """
    수치가 포함된 문장 중 [출처: ...] 태그가 없는 문장을 제거한다.
    마크다운 bullet(-) 또는 일반 문장 단위로 처리.
    """
    lines = text.split("\n")
    cleaned = []
    removed_count = 0

    for line in lines:
        stripped = line.strip()

        # 수치가 없으면 그냥 통과
        if not NUMERIC_PATTERN.search(stripped):
            cleaned.append(line)
            continue

        # 수치가 있고 출처 태그도 있으면 통과
        if SOURCE_TAG_PATTERN.search(stripped):
            cleaned.append(line)
            continue

        # 수치가 있는데 출처 태그가 없으면 제거
        print(f"  [후처리 제거] {stripped[:80]}...")
        removed_count += 1
        continue

    if removed_count:
        print(f"  [후처리] 미태깅 수치 문장 {removed_count}개 제거됨")

    return "\n".join(cleaned)


def enforce_three_line_summary(text: str) -> str:
    """
    ## 8. 3줄 요약 섹션의 bullet이 3개인지 확인.
    3개 미만이면 경고 출력 (재생성은 하지 않고 로그만).
    3개 초과면 앞 3개만 남김.
    """
    # 섹션 찾기
    match = re.search(r'(## 8[^\n]*\n)(.*?)(\Z|## \d)', text, re.DOTALL)
    if not match:
        return text

    section_header = match.group(1)
    section_body   = match.group(2)
    after          = match.group(3)

    bullets = [l for l in section_body.split("\n") if l.strip().startswith("- ")]

    if len(bullets) < 3:
        print(f"  [후처리 경고] 3줄 요약 bullet {len(bullets)}개 — 3개 미만")
        # 부족한 만큼 빈 항목 추가
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
# 출처 태그 → HTML 각주 변환
# ──────────────────────────────────────────

def convert_source_tags_to_html(text: str, articles: list[dict]) -> str:
    """
    [출처: 기사제목] 태그를 HTML 링크 각주로 변환.
    기사 목록에서 제목 매칭으로 URL 연결.
    """
    # 제목 → URL 매핑 빌드
    title_to_url = {}
    for a in articles:
        title_to_url[a["title"].strip()] = a.get("link", "")

    def replace_tag(match):
        tag_content = match.group(0)  # [출처: 기사제목]
        inner = re.sub(r'^\[출처\s*:\s*', '', tag_content).rstrip(']').strip()

        # 가장 유사한 기사 제목 찾기 (완전 일치 우선, 부분 일치 차선)
        url = title_to_url.get(inner, "")
        if not url:
            for title, u in title_to_url.items():
                if inner[:20] in title or title[:20] in inner:
                    url = u
                    break

        if url:
            return (
                f'<sup style="font-size:0.75em;color:#1a73e8;">'
                f'[<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#1a73e8;text-decoration:none;">{inner[:30]}</a>]</sup>'
            )
        else:
            return (
                f'<sup style="font-size:0.75em;color:#888;">[{inner[:30]}]</sup>'
            )

    return SOURCE_TAG_PATTERN.sub(replace_tag, text)


# ──────────────────────────────────────────
# 다이어그램 생성
# ──────────────────────────────────────────

def generate_diagram(topic_data: dict) -> str:
    topic = topic_data["topic"]
    prompt = f"""'{topic}' 기술의 핵심 구조나 작동 흐름을 보여주는
간단한 Mermaid 다이어그램 코드를 작성하세요.

규칙:
- graph TD (top-down) 또는 graph LR (left-right) 형식
- 노드는 5~8개 이내, 한국어 라벨 사용
- 색상 없이 기본 스타일만
- 노드 라벨에는 괄호, 따옴표, 특수문자 사용 완전 금지 (한글/영문/숫자/공백만)
- 설명 없이 mermaid 코드만 출력 (코드블록 표시 없이 순수 코드만)

예시:
graph LR
    A[입력 데이터] --> B[처리 단계]
    B --> C[출력 결과]
"""
    raw = call_ai(prompt, max_tokens=300)
    raw = re.sub(r"```mermaid|```", "", raw).strip()
    return raw


# ──────────────────────────────────────────
# 본문 생성 — 출처 태깅 강제
# ──────────────────────────────────────────

def generate_body(topic_data: dict) -> str:
    topic    = topic_data["topic"]
    title    = topic_data["korean_title"]
    reason   = topic_data.get("reason", "")
    articles = topic_data.get("source_articles", [])
    ctx      = build_article_context(articles, topic)

    prompt = f"""당신은 IT 기술 전문 블로거입니다.
아래 정보를 바탕으로 블로그 포스팅을 작성하세요.

【주제】{topic}
【제목】{title}
【선정 이유】{reason}
【참조 뉴스】
{ctx}

【작성 규칙】
- 반드시 아래 8개 섹션 구조로 작성
- 각 섹션은 ## 헤딩 사용
- 전체 분량: 1800~2800자 (한국어 기준)
- 독자 수준: IT에 관심 있는 일반인 / 경제 뉴스 독자
- 주식 추천, 매수/매도 의견, 목표가 절대 금지
- 기업명 언급 가능하나 투자 추천 표현 금지
- 문체: 친절하고 전문적, 딱딱하지 않게
- 이모지, 아이콘, 화살표 기호 사용 금지
- 마크다운 표, 구분선, ">" 인용구 사용 금지
- "본 글에서는", "~에 대해 알아보겠습니다" 같은 챗봇식 도입 문구 금지
- 글 시작은 독자의 궁금증이나 일상적 경험으로 자연스럽게 시작

【수치 사용 규칙 — 반드시 준수】
- 수치(숫자+%, 억, 만, 배, 감소, 증가 등)는 참조 뉴스에 명시된 것만 사용
- 수치를 사용할 때는 반드시 문장 끝에 [출처: 기사제목] 형태로 태깅
  예시) "마이크로소프트는 처리 속도가 40% 향상됐다고 밝혔다. [출처: Microsoft Copilot speeds up Dynamics 365]"
- 참조 뉴스에 수치가 없으면 수치 없이 정성적으로 서술
  예시) "처리 속도가 크게 향상됐다는 평가가 나온다."
- [출처: ] 태그 없이 수치를 단정적으로 제시하는 것은 절대 금지
- 출처 불명 수치를 만들어내는 것은 절대 금지

【문장 스타일】
나쁜 예: "AI 기술은 다양한 산업에 큰 영향을 미치고 있습니다."
좋은 예: "메타가 인도 Reliance와 AI 데이터센터 구축 계약을 발표하면서,
        동남아 시장에서 GPU 클러스터 수요가 본격화될 조짐을 보이고 있다. [출처: Meta Reliance AI datacenter deal]"

【출력 형식】
마크다운으로 작성. 섹션 구조:

## 1. 기술 개요
(무엇인가, 한 줄 정의부터 시작)

## 2. 왜 지금 주목받는가
(최근 시장/산업 트렌드와 연결, 참조 뉴스 사건 기반 서술)

## 3. 핵심 기술 요소
(3~5가지 핵심 개념을 bullet로)

## 4. 산업에 미치는 영향
(여러 산업 분야에 미치는 파급 효과)

## 5. 실제 적용 기업 사례
(반드시 참조 뉴스에 실제로 등장하는 기업과 사건만 서술.
참조 뉴스에 없는 기업·제품·사건은 절대 언급 금지.
기업이 참조 뉴스에서 다른 주제로 등장한 경우, 이 토픽과 억지로 연결하지 말 것.
예: 히타치-구글 기사가 Physical AI 관련이라면, Quantum Computing 글에서 히타치를 양자 컴퓨팅 사례로 쓰지 말 것.)

## 6. 경제·시장 관점에서 보기
(참조 뉴스의 구체적 사건 → 해석 구조로 작성.
수치가 있으면 [출처: ] 태깅 후 사용.
없으면 정성적 표현만 사용.
공급망 관련 기업 1~2개 구체적으로 언급)

## 7. 앞으로 주목할 포인트
(향후 6~12개월 내 관전 포인트 3가지, 반드시 bullet 3개)

## 8. 3줄 요약
(반드시 bullet 정확히 3개. 2개 또는 4개 금지.)
- 핵심 1
- 핵심 2
- 핵심 3
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
- 클릭을 유도하는 궁금증 또는 숫자 활용 (예: "~하는 이유", "~3가지", "2026년 ~")
- 키워드를 제목 앞쪽에 배치
- 카테고리도 1개 추천 (예: IT/테크, 반도체, AI/소프트웨어, 산업동향 중)

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
# Markdown → HTML 변환
# ──────────────────────────────────────────

def md_to_html(md: str, title: str, articles: list[dict] = None) -> str:
    # 1) 수치 후처리 — 미태깅 수치 문장 제거
    md = sanitize_untagged_numerics(md)

    # 2) 출처 태그 → HTML 각주 변환
    if articles:
        md = convert_source_tags_to_html(md, articles)

    lines = md.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        stripped = line.strip()

        # 구분선 무시
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            continue

        if line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            text = line[3:].strip()
            html_lines.append(
                f'<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;'
                f'margin:2.2em 0 0.8em;padding-bottom:8px;border-bottom:2px solid #333;">{text}</h2>'
            )
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                html_lines.append('<ul style="padding-left:1.5em;line-height:2.0;margin:0.5em 0;">')
                in_ul = True
            text = line[2:].strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            html_lines.append(f'  <li style="margin-bottom:6px;">{text}</li>')
        else:
            if in_ul and stripped:
                html_lines.append("</ul>")
                in_ul = False
            if stripped:
                text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                text = re.sub(
                    r"`(.+?)`",
                    r'<code style="background:#f1f1f1;padding:2px 6px;border-radius:3px;font-size:0.9em;">\1</code>',
                    text
                )
                html_lines.append(
                    f'<p style="line-height:1.95;margin:0.9em 0;color:#333;font-size:1em;">{text}</p>'
                )
            else:
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False

    if in_ul:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)

    # 참고 기사 링크 섹션
    references_html = ""
    if articles:
        ref_items = []
        for a in articles[:8]:
            src_label = {
                "google_news": "Google News",
                "yahoo_finance": "Yahoo Finance",
                "hacker_news": "Hacker News",
            }.get(a.get("source", ""), a.get("source", ""))
            ref_items.append(
                f'<li style="margin-bottom:8px;line-height:1.6;">'
                f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#1a73e8;text-decoration:none;">{a["title"]}</a>'
                f'<span style="color:#999;font-size:0.85em;"> — {src_label}</span></li>'
            )
        references_html = f"""
<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;margin:2.2em 0 0.8em;
padding-bottom:8px;border-bottom:2px solid #333;">참고 기사</h2>
<ul style="padding-left:1.5em;margin:0.5em 0;">
{chr(10).join(ref_items)}
</ul>
"""

    return f"""<div style="font-family:'Noto Sans KR','Malgun Gothic',sans-serif;max-width:720px;margin:0 auto;color:#333;word-break:keep-all;">

{body}

{references_html}

<div style="margin-top:3em;padding:18px 20px;background:#fafafa;border:1px solid #e8e8e8;border-radius:8px;font-size:0.85em;color:#999;line-height:1.8;">
본 콘텐츠는 IT 기술 정보 제공 목적으로 작성되었습니다. 투자 판단의 근거로 사용하지 마시기 바랍니다.
</div>

</div>"""


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    with open(TOPIC_FILE, encoding="utf-8") as f:
        topic_data = json.load(f)

    topic    = topic_data["topic"]
    title    = topic_data["korean_title"]
    tags     = topic_data.get("tags", [topic, "IT기술", "기술트렌드"])
    articles = topic_data.get("source_articles", [])

    print(f"[포스팅 생성] 주제: {topic}")
    print(f"[포스팅 생성] 제목: {title}")

    body_md = generate_body(topic_data)
    print(f"\n[본문 생성 완료] {len(body_md)}자")

    # 구성도 생성
    print("\n[구성도 생성 중...]")
    diagram_html = ""
    try:
        diagram_code = generate_diagram(topic_data)
        diagram_url  = mermaid_to_image_url(diagram_code)
        diagram_html = f'''
<div style="text-align:center;margin:2em 0;">
  <img src="{diagram_url}" alt="{topic} 구조도" style="max-width:100%;border-radius:8px;border:1px solid #eee;" />
  <p style="font-size:0.85em;color:#999;margin-top:8px;">{topic} 핵심 구조도</p>
</div>
'''
        print(f"[구성도 URL] {diagram_url[:80]}...")
    except Exception as e:
        print(f"[WARN] 구성도 생성 실패: {e}")

    # 참조 기사 필터링
    topic_lower = topic.lower()
    relevant_articles = [
        a for a in articles
        if topic_lower in a["title"].lower() or topic_lower in a.get("summary", "").lower()
    ][:8]
    if not relevant_articles:
        relevant_articles = articles[:8]

    body_html = md_to_html(body_md, title, relevant_articles)

    # 구성도를 "3. 핵심 기술 요소" 섹션 바로 앞에 삽입
    if diagram_html:
        marker = '<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;margin:2.2em 0 0.8em;padding-bottom:8px;border-bottom:2px solid #333;">3.'
        idx = body_html.find(marker)
        if idx != -1:
            body_html = body_html[:idx] + diagram_html + body_html[idx:]
        else:
            body_html += diagram_html

    print("\n[제목/카테고리 추천 중...]")
    refined          = refine_title(topic_data)
    title_candidates = refined.get("titles", [title])
    category         = refined.get("category", "테크인사이트-IT트렌드")
    final_title      = title_candidates[0] if title_candidates else title

    print(f"[제목 추천] {title_candidates}")
    print(f"[카테고리 추천] {category}")

    post = {
        "title":            final_title,
        "title_candidates": title_candidates,
        "category":         category,
        "topic":            topic,
        "content_html":     body_html,
        "content_md":       body_md,
        "tags":             ",".join(tags),
        "created_at":       datetime.now().isoformat(),
    }

    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    with open("data/blog_post.html", "w", encoding="utf-8") as f:
        f.write(body_html)

    print(f"\n포스팅 저장 완료 → {POST_FILE}")
    print(f"HTML 저장 완료  → data/blog_post.html")


if __name__ == "__main__":
    main()
