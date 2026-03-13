import datetime

with open("analysis.md", encoding="utf-8") as f:
    analysis = f.read()

today = datetime.datetime.now().strftime("%Y년 %m월 %d일")

content = f"""# 📚 기술사 시험 뉴스 브리핑

> 🤖 GitHub Actions + AI가 매일 오전 7시 자동 업데이트합니다.
> 마지막 업데이트: **{today}**

---

{analysis}

---

<details>
<summary>⚙️ 자동화 구성</summary>

| 구성 | 내용 |
|:----:|:-----|
| 뉴스 수집 | ITWorld, 전자신문, ZDNet, 보안뉴스, CIO Korea RSS |
| AI 분석 | OpenRouter |
| 업데이트 | 매일 오전 7시 KST |
| 발송 | Gmail 자동 발송 |

</details>
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(content)

print("README.md 업데이트 완료")