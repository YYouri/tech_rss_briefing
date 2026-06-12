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
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "tngtech/deepseek-r1t-chimera:free",
]


# ── OpenRouter 호출 ───────────────────────────────────────────────────────────

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

# ── 참조 기사 요약 ────────────────────────────────────────────────────────────

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

# ── 본문 생성 ─────────────────────────────────────────────────────────────────

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
- 반드시 아래 7개 섹션 구조로 작성
- 각 섹션은 ## 헤딩 사용
- 전체 분량: 1500~2500자 (한국어 기준)
- 독자 수준: IT에 관심 있는 일반인 / 경제 뉴스 독자
- 주식 추천, 매수/매도 의견, 목표가 절대 금지
- 기업명 언급 가능하나 투자 추천 표현 금지
- SEO를 위해 핵심 키워드를 자연스럽게 반복 포함
- 문체: 친절하고 전문적, 딱딱하지 않게

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

## 6. 앞으로 주목할 포인트
(향후 6~12개월 내 관전 포인트)

## 7. 3줄 요약
- 핵심 1
- 핵심 2
- 핵심 3
"""
    return call_ai(prompt, max_tokens=4096)

# ── Markdown → HTML 변환 ──────────────────────────────────────────────────────

def md_to_html(md: str, title: str) -> str:
    """간단한 Markdown → Tistory용 HTML 변환"""
    lines = md.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        # h2
        if line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            text = line[3:].strip()
            html_lines.append(f'<h2 style="margin-top:2em;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">{text}</h2>')
        # bold
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                html_lines.append('<ul style="line-height:1.9;">')
                in_ul = True
            text = line[2:].strip()
            # **bold**
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            html_lines.append(f"  <li>{text}</li>")
        else:
            if in_ul and line.strip():
                html_lines.append("</ul>")
                in_ul = False
            if line.strip():
                text = line.strip()
                text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
                text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
                html_lines.append(f"<p>{text}</p>")
            else:
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False

    if in_ul:
        html_lines.append("</ul>")

    today = datetime.now().strftime("%Y년 %m월 %d일")
    body = "\n".join(html_lines)

    return f"""<div style="font-family:'Noto Sans KR',sans-serif;max-width:800px;margin:0 auto;line-height:1.8;color:#333;">

<p style="color:#888;font-size:0.85em;">📅 {today} | 오늘 시장이 주목한 IT 기술</p>

{body}

<hr style="margin-top:3em;border:none;border-top:1px solid #e0e0e0;">
<p style="font-size:0.8em;color:#999;">
⚠️ 본 콘텐츠는 IT 기술 정보 제공 목적으로 작성되었으며, 투자 추천이나 매수/매도 의견을 포함하지 않습니다.
</p>

</div>"""

# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    with open(TOPIC_FILE, encoding="utf-8") as f:
        topic_data = json.load(f)

    topic = topic_data["topic"]
    title = topic_data["korean_title"]
    tags  = topic_data.get("tags", [topic, "IT기술", "기술트렌드"])

    print(f"[포스팅 생성] 주제: {topic}")
    print(f"[포스팅 생성] 제목: {title}")

    body_md = generate_body(topic_data)
    print(f"\n[본문 생성 완료] {len(body_md)}자")

    body_html = md_to_html(body_md, title)

    post = {
        "title": title,
        "topic": topic,
        "content_html": body_html,
        "content_md": body_md,
        "tags": ",".join(tags),
        "created_at": datetime.now().isoformat(),
    }

    with open("data/blog_post.html", "w", encoding="utf-8") as f:
        f.write(body_html)


    print(f"포스팅 저장 완료 → {POST_FILE}")

if __name__ == "__main__":
    main()
