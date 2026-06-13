"""
update_exam_history.py
KPC 기술사문제검색 엑셀의 '기출' 탭을 data/exam_history.json으로 변환한다.
GitHub Actions(update_exam_data.yml)에서 자동 실행됨.
"""

import sys
import json
import openpyxl

OUTPUT_FILE = "data/exam_history.json"


def main():
    if len(sys.argv) < 2:
        print("사용법: python update_exam_history.py <엑셀파일.xlsx>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "기출" not in wb.sheetnames:
        print(f"[ERROR] '기출' 시트를 찾을 수 없음. 시트 목록: {wb.sheetnames}")
        sys.exit(1)

    ws = wb["기출"]

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue
        회차, 종목, 유형, 문제 = row[0], row[1], row[2], row[3]
        if 문제 is None:
            continue
        rows.append({
            "round":    int(회차) if 회차 else 0,
            "subject":  str(종목) if 종목 else "",
            "type":     int(유형) if 유형 else 0,
            "question": str(문제).strip(),
        })

    rounds = sorted(set(r["round"] for r in rows))
    print(f"총 {len(rows)}개 문제")
    print(f"회차 범위: {min(rounds)}회 ~ {max(rounds)}회 (총 {len(rounds)}개 회차)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    print(f"저장 완료 → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
