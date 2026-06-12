"""
03_generate_post.py
OpenRouter Free API로 블로그 포스팅 본문을 생성하고 HTML로 변환한다.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime

TOPIC_FILE  = "data/selected_topic.json"
POST_FILE   = "data/blog_post.json"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODELS = [
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super:free",
]

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

def build_article_context(articles: list[dict], topic: str) -> str:
    topic_lower = topic.lower()
    relevant = [
        a for a in articles
        if topic_lower in a["title"].lower() or topic_lower in a.get("summary", "").lower()
    ][:10]
    if not relevant:
        relevant = articles[:10]
    lines = []
    for a in relevant:
        lines.append(f"- [{a['source']}] {a['title']}")
        if a.get("summary"):
            lines.append(f"  {a['summary'][:150]}")
    return "\n".join(lines)

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
- SEO를 위해 핵심 키워드를 자연스럽게 반복 포함
- 문체: 친절하고 전문적, 딱딱하지 않게
- 이모지, 아이콘, 화살표 기호(➡️, 👉, 1️⃣ 등) 사용 금지
- 마크다운 표(|---|), 구분선(---), ">" 인용구 사용 금지
- "본 글에서는", "~에 대해 알아보겠습니다" 같은 챗봇식 도입 문구 금지
- 글 시작은 독자의 궁금증이나 일상적 경험으로 자연스럽게 시작
- 각 섹션 사이 연결 문장은 평서문으로, 인용구 기호 없이 작성
- 비교가 필요하면 문장이나 리스트로 풀어서 설명 (표 형식 대신)

【출력 형식】
마크다운으로 작성. 섹션 구조:

## 1. 기술 개요
(무엇인가, 한 줄 정의부터 시작)

## 2. 왜 지금 주목받는가
(최근 시장/산업 트렌드와 연결)

## 3. 핵심 기술 요소
(3~5가지 핵심 개념을 bullet로)

## 4. 산업에 미치는 영향
(여러 산업 분야에 미치는 파급 효과)

## 5. 실제 적용 기업 사례
(실명 기업 2~4개 구체적 사례)

## 6. 경제·시장 관점에서 보기
(이 기술이 관련 산업/기업의 실적, 공급망, 시장 규모에 어떤 의미를 갖는지 설명.
주가나 매수/매도 언급 없이, "왜 시장이 이 기술을 주목하는가"를 경제 흐름 관점에서 풀어줄 것.
구체적인 시장 규모나 성장률 수치는 참조 뉴스에 명시된 경우에만 사용하고,
출처가 불분명하면 "빠르게 성장하고 있다", "수요가 꾸준히 늘고 있다" 같은
정성적 표현으로 작성. 숫자를 단정적으로 제시하지 말 것)

## 7. 앞으로 주목할 포인트
(향후 6~12개월 내 관전 포인트)

## 8. 3줄 요약
- 핵심 1
- 핵심 2
- 핵심 3
"""
    return call_ai(prompt, max_tokens=4096)

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

def md_to_html(md: str, title: str, articles: list[dict] = None) -> str:
    """Markdown → 네이버/티스토리 블로그 스타일 HTML"""
    lines = md.split("\n")
    html_lines = []
    in_ul = False
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            in_table = False
            return
        header = table_rows[0]
        body_rows = table_rows[2:] if len(table_rows) > 2 else []
        html_lines.append('<table style="width:100%;border-collapse:collapse;margin:1.2em 0;font-size:0.95em;">')
        html_lines.append('<thead><tr>')
        for cell in header:
            html_lines.append(f'<th style="border:1px solid #ddd;padding:10px;background:#f5f5f5;text-align:left;">{cell.strip()}</th>')
        html_lines.append('</tr></thead><tbody>')
        for row in body_rows:
            html_lines.append('<tr>')
            for cell in row:
                cell_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", cell.strip())
                html_lines.append(f'<td style="border:1px solid #ddd;padding:10px;">{cell_html}</td>')
            html_lines.append('</tr>')
        html_lines.append('</tbody></table>')
        table_rows = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c for c in stripped.strip("|").split("|")]
            table_rows.append(cells)
            in_table = True
            continue
        elif in_table:
            flush_table()

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
                text = re.sub(r"`(.+?)`", r'<code style="background:#f1f1f1;padding:2px 6px;border-radius:3px;font-size:0.9em;">\1</code>', text)
                html_lines.append(f'<p style="line-height:1.95;margin:0.9em 0;color:#333;font-size:1em;">{text}</p>')
            else:
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False

    if in_table:
        flush_table()
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
<h2 style="font-size:1.3em;font-weight:700;color:#1a1a1a;margin:2.2em 0 0.8em;padding-bottom:8px;border-bottom:2px solid #333;">참고 기사</h2>
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


def main():
    with open(TOPIC_FILE, encoding="utf-8") as f:
        topic_data = json.load(f)

    topic = topic_data["topic"]
    title = topic_data["korean_title"]
    tags  = topic_data.get("tags", [topic, "IT기술", "기술트렌드"])
    articles = topic_data.get("source_articles", [])

    print(f"[포스팅 생성] 주제: {topic}")
    print(f"[포스팅 생성] 제목: {title}")

    body_md   = generate_body(topic_data)
    print(f"\n[본문 생성 완료] {len(body_md)}자")

    # 참고 기사: 본문 생성에 쓴 것과 동일한 관련 기사 선별
    topic_lower = topic.lower()
    relevant_articles = [
        a for a in articles
        if topic_lower in a["title"].lower() or topic_lower in a.get("summary", "").lower()
    ][:8]
    if not relevant_articles:
        relevant_articles = articles[:8]

    body_html = md_to_html(body_md, title, relevant_articles)

    print("\n[제목/카테고리 추천 중...]")
    refined = refine_title(topic_data)
    title_candidates = refined.get("titles", [title])
    category = refined.get("category", "테크인사이트-IT트렌드")
    final_title = title_candidates[0] if title_candidates else title

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

    print(f"포스팅 저장 완료 → {POST_FILE}")
    print(f"HTML 저장 완료  → data/blog_post.html")

if __name__ == "__main__":
    main()
