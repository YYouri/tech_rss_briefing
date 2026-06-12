"""
05_update_history.py
발행 완료 후 토픽 이력을 업데이트한다.
최근 30일 이력을 유지하며, 동일 주제 반복 발행을 방지한다.
"""

import json
import os
from datetime import datetime, timedelta

RESULT_FILE  = "data/blog_post.json"
HISTORY_FILE = "data/topic_history.json"
KEEP_DAYS    = 30

def main():
    # 결과 파일 로드
    if not os.path.exists(RESULT_FILE):
        print("[WARN] post_result.json 없음 → 이력 업데이트 스킵")
        return

    with open(RESULT_FILE, encoding="utf-8") as f:
        result = json.load(f)

    # 기존 이력 로드
    history: list[dict] = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)

    # 새 항목 추가
    new_entry = {
        "topic":      result["topic"],
        "title":      result["title"],
        "url":        result.get("url", ""),
        "tags":       result.get("tags", ""),
        "date":       datetime.now().isoformat(),
    }
    history.append(new_entry)

    # 30일 이전 항목 제거
    cutoff  = datetime.now() - timedelta(days=KEEP_DAYS)
    history = [
        h for h in history
        if datetime.fromisoformat(h["date"]) >= cutoff
    ]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"[이력 업데이트] 현재 {len(history)}개 항목 (최근 {KEEP_DAYS}일)")
    for h in history[-5:]:
        print(f"  - {h['date'][:10]} | {h['topic']} | {h['title'][:40]}")

if __name__ == "__main__":
    main()
