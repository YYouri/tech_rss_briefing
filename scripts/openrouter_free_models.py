"""
openrouter_free_models.py
OpenRouter 무료 모델 슬러그를 '하드코딩'하지 않고 실행 시점에 조회한다.

배경: OpenRouter는 무료(:free) 모델 라인업을 예고 없이 몇 주 단위로
갈아치운다 — 실제로 이 레포도 매번 하드코딩된 슬러그가 404로 죽는 걸
반복해서 겪었다. 근본 해결은 "지금 이 순간 실제로 살아있는 무료 모델이
뭔지" 매 실행마다 물어보고 그중에서 고르는 것.

공개 엔드포인트라 API 키 없이도 조회 가능:
  GET https://openrouter.ai/api/v1/models
"""

import json
import re
import urllib.request
import urllib.error

MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"

# 텍스트 생성에 부적합한 모델(번역 전용, 이미지 생성 등)을 배제하기 위한
# 대략적인 필터. 완벽하지 않아도 되고, 죽지 않는 게 목적이다.
_EXCLUDE_ID_SUBSTR = ("whisper", "tts", "embedding", "moderation", "translat", "-vl", "vision")

# 실시간 조회가 실패했을 때(네트워크 문제 등)의 최후 폴백.
# 여기 있는 슬러그도 언젠가 죽을 수 있으니 절대 이것만 믿지 말 것 —
# 아래 openrouter/free(자동 라우터)가 진짜 최후의 보루.
HARDCODED_FALLBACK = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
]


def fetch_live_free_models(limit: int = 15, timeout: int = 15) -> list[str]:
    """지금 시점에 :free 이면서 prompt/completion 가격이 0인 텍스트 모델 슬러그 목록.
    실패하면 빈 리스트를 반환한다 (예외를 던지지 않음 — 폴백은 호출부 책임)."""
    req = urllib.request.Request(
        MODELS_ENDPOINT,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TechBlogBot/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] OpenRouter 모델 목록 조회 실패: {e}")
        return []

    models = data.get("data", [])
    free_ids = []
    for m in models:
        model_id = m.get("id", "")
        if not model_id.endswith(":free"):
            continue
        if any(s in model_id.lower() for s in _EXCLUDE_ID_SUBSTR):
            continue
        pricing = m.get("pricing", {})
        try:
            if float(pricing.get("prompt", "1")) != 0 or float(pricing.get("completion", "1")) != 0:
                continue
        except (TypeError, ValueError):
            continue
        arch = m.get("architecture", {})
        outputs = arch.get("output_modalities") or []
        if outputs and "text" not in outputs:
            continue
        # 컨텍스트 길이가 너무 짧은 모델(번역기 등)은 우선순위에서 밀어낸다.
        context_len = m.get("context_length") or 0
        free_ids.append((context_len, model_id))

    # 컨텍스트 길이가 큰(=보통 더 최신/범용) 모델을 우선 시도
    free_ids.sort(key=lambda x: x[0], reverse=True)
    result = [mid for _, mid in free_ids[:limit]]
    print(f"  [INFO] OpenRouter 실시간 무료 모델 {len(result)}개 확보")
    return result


def build_model_list(limit: int = 15) -> list[str]:
    """실시간 조회 결과 + 하드코딩 폴백을 합쳐 중복 없는 순서로 반환.
    실시간 목록이 항상 우선이고, openrouter/free 자동 라우터가 항상 맨 끝에 붙어
    모든 시도가 실패할 확률을 최소화한다."""
    live = fetch_live_free_models(limit=limit)
    combined = live + [m for m in HARDCODED_FALLBACK if m not in live]
    seen, ordered = set(), []
    for m in combined:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


# ── LLM 응답에서 JSON 안전하게 추출하기 ────────────────────────────────────────
# 추론형(reasoning) 무료 모델(nemotron 등)은 지시해도 <think>...</think> 블록이나
# 코드펜스 안에 최종 JSON을 감싸서 내보내는 경우가 있다. 기존의 탐욕적 정규식
# `\[.*\]` / `\{.*\}`는 이런 부가 텍스트 속 괄호에 속아 첫 '['부터 텍스트 맨
# 끝의 마지막 ']'까지 통째로 잡아먹어 파싱이 깨지는 원인이 됐다
# (2026-08-24 nemotron-3-super 응답에서 실제로 확인된 실패 패턴).



def strip_reasoning_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```json|```", "", text)
    return text.strip()


def extract_balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    """open_ch로 시작하는 모든 후보 구간을 괄호 깊이로 잘라낸 뒤,
    실제로 json.loads가 되는 첫 후보를 반환한다.

    단순히 '첫 open_ch부터 짝 맞는 close_ch까지'만 자르면, 모델이 본문에서
    "이 배열([array])을 보면..."처럼 설명 중에 괄호를 언급한 경우 그 decoy를
    진짜 JSON보다 먼저 집어버린다(2026-08-24 실제 응답에서 재현 확인).
    그래서 후보마다 파싱을 직접 검증해서 진짜 JSON만 통과시킨다.
    """
    # 중첩 구조 내부에는 열고 닫는 괄호 종류가 섞여 있으므로(예: 배열 안의
    # 객체가 트레일링 콤마를 가진 경우) 둘 다 정리해야 한다.
    trailer_fix = re.compile(r",\s*([\]}])")
    for start in (i for i, c in enumerate(text) if c == open_ch):
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    cleaned = trailer_fix.sub(r"\1", candidate)
                    try:
                        json.loads(cleaned)
                        return cleaned
                    except Exception:
                        break  # 이 시작점은 유효한 JSON이 아님 → 다음 '[' / '{'부터 재시도
    return None
