"""
03_generate_post.py
OpenRouter Free API로 블로그 포스팅 본문을 생성하고 HTML로 변환한다.

개선사항:
- 숫자 누락 버그 수정: 출처 없는 수치는 제거 대신 경고만 출력
- 섹션 라벨 수정: MARKET → KPE, 헤딩 띄어쓰기 수정
- 대표 이미지: Unsplash API 연동
- 섹션 접두어 렌더링 개선 (배지 + 제목 사이 공백)
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
import base64
from datetime import datetime

TOPIC_FILE = "data/selected_topic.json"
POST_FILE  = "data/blog_post.json"

OPENROUTER_API_KEY   = os.environ.get("OPENROUTER_API_KEY")
UNSPLASH_ACCESS_KEY  = os.environ.get("UNSPLASH_ACCESS_KEY")

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
# 대표 이미지 — Unsplash
# ──────────────────────────────────────────

def fetch_unsplash_image(topic: str) -> dict | None:
    """Unsplash에서 토픽 관련 이미지 검색. 없으면 None 반환."""
    if not UNSPLASH_ACCESS_KEY:
        print("[WARN] UNSPLASH_ACCESS_KEY 없음 → 대표 이미지 스킵")
        return None

    # 영어 검색어로 변환 (토픽이 한글이면 AI가 변환)
    query = topic.replace(" ", "+")

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
            "url":      photo["urls"]["regular"],
            "thumb":    photo["urls"]["small"],
            "alt":      photo.get("alt_description") or topic,
            "author":   photo["user"]["name"],
            "author_url": photo["user"]["links"]["html"],
            "unsplash_url": photo["links"]["html"],
        }
    except Exception as e:
        print(f"[WARN] Unsplash 이미지 검색 실패: {e}")
        return None


def build_hero_image_html(image: dict, topic: str) -> str:
    """대표 이미지 HTML 생성 (Unsplash 저작권 표기 포함)"""
    return f"""
<div style="margin:0 0 2em;border-radius:12px;overflow:hidden;position:relative;">
  <img
    src="{image['url']}"
    alt="{image['alt']}"
    style="width:100%;max-height:400px;object-fit:cover;display:block;"
    loading="lazy"
  />
  <p style="font-size:0.75em;color:#aaa;margin:6px 0 0;text-align:right;">
    Photo by <a href="{image['author_url']}?utm_source=mystacklog&utm_medium=referral"
    target="_blank" rel="noopener noreferrer" style="color:#aaa;">{image['author']}</a>
    on <a href="https://unsplash.com?utm_source=mystacklog&utm_medium=referral"
    target="_blank" rel="noopener noreferrer" style="color:#aaa;">Unsplash</a>
  </p>
</div>
"""


# ──────────────────────────────────────────
# 기사 컨텍스트 빌더
# ──────────────────────────────────────────

def build_article_context(articles: list[dict], topic: str) -> str:
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
# ✅ 수치 후처리 — 제거 대신 경고만 출력
# ──────────────────────────────────────────

NUMERIC_PATTERN = re.compile(
    r'\d+(\.\d+)?'
    r'\s*'
    r'(%|퍼센트|억|만|천|조|배|달러|원|배출량|감소|증가|단축|절감|향상|성장률|상승)',
    re.UNICODE
)
SOURCE_TAG_PATTERN = re.compile(r'\[출처\s*:\s*.+?\]')


def sanitize_untagged_numerics(text: str) -> str:
    """
    ✅ 수정: 출처 없는 수치는 제거하지 않고 경고만 출력.
    기존 코드가 수치를 삭제해서 '효율을 이상 끌어올린' 같은 문장이 만들어졌음.
    """
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if NUMERIC_PATTERN.search(stripped) and not SOURCE_TAG_PATTERN.search(stripped):
            print(f"  [경고] 출처 미태깅 수치 발견: {stripped[:80]}...")
    return text  # 원문 그대로 반환


def enforce_three_line_summary(text: str) -> str:
    match = re.search(r'(## 8[^\n]*\n)(.*?)(\Z|## \d)', text, re.DOTALL)
    if not match:
        return text

    section_header = match.group(1)
    section_body   = match.group(2)
    after          = match.group(3)

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
# 출처 태그 → HTML 각주 변환
# ──────────────────────────────────────────

def convert_source_tags_to_html(text: str, articles: list[dict]) -> str:
    title_to_url = {}
    for a in articles:
        title_to_url[a["title"].strip()] = a.get("link", "")

    def replace_tag(match):
        tag_content = match.group(0)
        inner = re.sub(r'^\[출처\s*:\s*', '', tag_content).rstrip(']').strip()
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
            return f'<sup style="font-size:0.75em;color:#888;">[{inner[:30]}]</sup>'

    return SOURCE_TAG_PATTERN.sub(replace_tag, text)


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
- 반드시 아래 8개 섹션 구조로 작성
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
## 6. 정보관리기술사 연계

관련 기출:
(있으면 작성, 없으면 없음)

답안 핵심 키워드:
- 키워드1
- 키워드2
- 키워드3

답안 작성 포인트:
- 정의
- 구조
- 활용
- 기대효과

## 7. 앞으로 볼 포인트
- bullet 정확히 3개

## 8. 3줄 요약
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
# ✅ 섹션 라벨 수정 — MARKET → KPE, 헤딩 렌더링 개선
# ──────────────────────────────────────────

SECTION_LABELS = {
    "1": ("TECH",   "#1a73e8"),
    "2": ("TREND",  "#0f9d58"),
    "3": ("CORE",   "#f57c00"),
    "4": ("IMPACT", "#7b1fa2"),
    "5": ("CASE",   "#c62828"),
    "6": ("KPE",    "#00838f"),   # ✅ MARKET → KPE (정보관리기술사)
    "7": ("AHEAD",  "#37474f"),
    "8": ("SUMMARY","#1a73e8"),
}


def render_heading(text: str) -> str:
    match = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
    if not match:
        return (
            f'<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;'
            f'margin:2.2em 0 0.8em;padding-bottom:8px;border-bottom:2px solid #333;">'
            f'{text}</h2>'
        )

    num, title_text = match.group(1), match.group(2)
    label_info = SECTION_LABELS.get(num)

    if label_info:
        label, color = label_info
        badge = (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'font-size:0.7em;font-weight:700;padding:3px 9px;border-radius:4px;'
            f'margin-right:10px;vertical-align:middle;letter-spacing:0.5px;">'
            f'{label}</span>'
        )
    else:
        badge = ""

    return (
        f'<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;'
        f'margin:2.2em 0 0.8em;padding-bottom:8px;border-bottom:2px solid #eee;">'
        f'{badge}{title_text}</h2>'  # ✅ 배지와 제목 사이 공백 자연스럽게
    )


def render_core_elements_cards(bullet_lines: list[str]) -> str:
    cards = []
    for line in bullet_lines:
        text = line[2:].strip()
        m = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)$", text)
        if m:
            term, desc = m.group(1), m.group(2)
        else:
            term, desc = "", text

        if term:
            cards.append(
                '<div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;">'
                f'<strong style="color:#1a73e8;font-size:0.98em;">{term}</strong>'
                f'<p style="margin:6px 0 0;font-size:0.92em;color:#555;line-height:1.6;">{desc}</p>'
                '</div>'
            )
        else:
            cards.append(
                '<div style="background:#f8f9fa;border-radius:10px;padding:14px 16px;">'
                f'<p style="margin:0;font-size:0.92em;color:#555;line-height:1.6;">{desc}</p>'
                '</div>'
            )

    return (
        '<div style="display:flex;flex-wrap:wrap;gap:12px;margin:1em 0;">'
        + "".join(
            f'<div style="flex:1 1 calc(50% - 6px);min-width:220px;">{c}</div>'
            for c in cards
        )
        + "</div>"
    )


def render_summary_box(bullet_lines: list[str]) -> str:
    items = "".join(
        f'<li style="margin-bottom:8px;line-height:1.7;color:#333;">{line[2:].strip()}</li>'
        for line in bullet_lines
    )
    return (
        '<div style="background:#eef4ff;border-radius:10px;padding:18px 20px;margin:1.5em 0;">'
        '<p style="font-weight:700;color:#1a73e8;margin:0 0 10px;font-size:1.02em;">한눈에 보기</p>'
        f'<ul style="padding-left:1.3em;margin:0;">{items}</ul>'
        '</div>'
    )


def md_to_html(md: str, title: str, articles: list[dict] = None) -> str:
    md = sanitize_untagged_numerics(md)
    if articles:
        md = convert_source_tags_to_html(md, articles)

    lines = md.split("\n")
    html_lines = []
    in_ul = False
    ul_buffer = []
    current_section = None

    def flush_ul():
        nonlocal in_ul, ul_buffer
        if not ul_buffer:
            in_ul = False
            return

        if current_section == "3":
            html_lines.append(render_core_elements_cards(ul_buffer))
        elif current_section == "8":
            html_lines.append(render_summary_box(ul_buffer))
        else:
            html_lines.append('<ul style="padding-left:1.5em;line-height:2.0;margin:0.5em 0;">')
            for l in ul_buffer:
                text = l[2:].strip()
                text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
                html_lines.append(f'  <li style="margin-bottom:6px;">{text}</li>')
            html_lines.append("</ul>")

        ul_buffer.clear()
        in_ul = False

    is_first_content_line = True

    for line in lines:
        stripped = line.strip()

        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            continue

        if line.startswith("## "):
            if in_ul:
                flush_ul()
            heading_text = line[3:].strip()
            html_lines.append(render_heading(heading_text))
            m = re.match(r"^(\d+)\.", heading_text)
            current_section = m.group(1) if m else None
            is_first_content_line = False

        elif line.startswith("- ") or line.startswith("* "):
            is_first_content_line = False
            in_ul = True
            ul_buffer.append(line.strip())

        else:
            if in_ul and stripped:
                flush_ul()

            if stripped:
                text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                text = re.sub(
                    r"`(.+?)`",
                    r'<code style="background:#f1f1f1;padding:2px 6px;border-radius:3px;font-size:0.9em;">\1</code>',
                    text
                )
                if is_first_content_line and current_section is None:
                    html_lines.append(
                        f'<p style="line-height:1.9;margin:0 0 1.5em;color:#444;'
                        f'font-size:1.05em;border-left:3px solid #1a73e8;'
                        f'padding-left:14px;">{text}</p>'
                    )
                    is_first_content_line = False
                else:
                    html_lines.append(
                        f'<p style="line-height:1.95;margin:0.9em 0;color:#333;font-size:1em;">{text}</p>'
                    )
            else:
                if in_ul:
                    flush_ul()

    if in_ul:
        flush_ul()

    body = "\n".join(html_lines)

    references_html = ""
    if articles:
        ref_items = []
        for a in articles[:8]:
            src_label = {
                "google_news":   "Google News",
                "yahoo_finance": "Yahoo Finance",
                "hacker_news":   "Hacker News",
            }.get(a.get("source", ""), a.get("source", ""))
            ref_items.append(
                f'<li style="margin-bottom:6px;line-height:1.6;">'
                f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#5a8fd6;text-decoration:none;">{a["title"]}</a>'
                f'<span style="color:#aaa;font-size:0.85em;"> — {src_label}</span></li>'
            )
        references_html = f"""
<div style="margin-top:2.5em;padding:16px 20px;background:#fcfcfc;border:1px solid #eee;border-radius:8px;">
<p style="font-size:0.85em;font-weight:700;color:#999;margin:0 0 10px;letter-spacing:0.5px;">참고 기사</p>
<ul style="padding-left:1.3em;margin:0;font-size:0.92em;">
{chr(10).join(ref_items)}
</ul>
</div>
"""

    return f"""<div style="font-family:'Noto Sans KR','Malgun Gothic',sans-serif;max-width:720px;margin:0 auto;color:#333;word-break:keep-all;">

{{HERO_IMAGE}}

{body}

{references_html}

<div style="margin-top:1.5em;padding:18px 20px;background:#fafafa;border:1px solid #e8e8e8;border-radius:8px;font-size:0.85em;color:#999;line-height:1.8;">
본 콘텐츠는 IT 기술 정보 제공 목적으로 작성되었습니다. 투자 판단의 근거로 사용하지 마시기 바랍니다.
</div>

</div>"""


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    if not os.path.exists(TOPIC_FILE):
        print(f"[ERROR] {TOPIC_FILE} 파일이 없습니다.")
        print("       02_select_topic.py를 먼저 실행하세요.")
        sys.exit(1)

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

    body_md = enforce_three_line_summary(body_md)

    # 3. 구성도 생성
    print("\n[구성도 생성 중...]")
    diagram_html = ""
    try:
        diagram_code = generate_diagram(topic_data)
        diagram_url  = mermaid_to_image_url(diagram_code)
        diagram_html = f'''
<div style="text-align:center;margin:2em 0;">
  <img src="{diagram_url}" alt="{topic} 구조도" style="max-width:100%;border-radius:8px;border:1px solid #eee;" loading="lazy" />
  <p style="font-size:0.85em;color:#999;margin-top:8px;">{topic} 핵심 구조도</p>
</div>
'''
        print(f"[구성도 URL] {diagram_url[:80]}...")
    except Exception as e:
        print(f"[WARN] 구성도 생성 실패: {e}")

    # 4. HTML 변환
    relevant_articles = articles[:8] if articles else []
    body_html = md_to_html(body_md, title, relevant_articles)

    # 5. 대표 이미지 삽입
    hero_html = build_hero_image_html(hero_image, topic) if hero_image else ""
    body_html = body_html.replace("{HERO_IMAGE}", hero_html)

    # 6. 구성도 삽입 (CORE 섹션 앞)
    if diagram_html:
        marker = '>CORE</span>'
        idx = body_html.find(marker)
        if idx != -1:
            h2_start = body_html.rfind('<h2', 0, idx)
            if h2_start != -1:
                body_html = body_html[:h2_start] + diagram_html + body_html[h2_start:]
        else:
            body_html += diagram_html

    # 7. 제목 추천
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
        "content_html":     body_html,
        "content_md":       body_md,
        "tags":             ",".join(tags),
        "created_at":       datetime.now().isoformat(),
        "hero_image":       hero_image,
    }

    os.makedirs("data", exist_ok=True)

    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    with open("data/blog_post.html", "w", encoding="utf-8") as f:
        f.write(body_html)

    with open("data/blog_post.md", "w", encoding="utf-8") as f:
        f.write(f"# {final_title}\n\n")
        f.write(body_md)

    print(f"\n포스팅 저장 완료 → {POST_FILE}")


if __name__ == "__main__":
    main()
