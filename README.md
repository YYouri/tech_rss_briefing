# 🤖 Tistory IT 기술 자동화 블로그

> **"오늘 시장이 주목한 IT 기술"** — GitHub Actions + Gemini Free API로 매일 자동 발행

---

## 📐 전체 아키텍처

```
매일 KST 06:00 (UTC 21:00)
        │
        ▼
┌─────────────────────────────────────┐
│        GitHub Actions Runner         │
│                                     │
│  ① collect_news.py                  │
│     ├─ Google News RSS              │
│     ├─ Yahoo Finance RSS            │
│     ├─ Hacker News API              │
│     └─ Reddit JSON API              │
│            │                        │
│            ▼  raw_articles.json     │
│  ② select_topic.py                  │
│     ├─ Gemini: 키워드 추출          │
│     ├─ 중복 이력 필터               │
│     └─ Gemini: 최적 토픽 선정       │
│            │                        │
│            ▼  selected_topic.json   │
│  ③ generate_post.py                 │
│     ├─ Gemini: 본문 생성 (7섹션)    │
│     └─ Markdown → HTML 변환        │
│            │                        │
│            ▼  blog_post.json        │
│  ④ post_tistory.py                  │
│     └─ Tistory Open API 업로드     │
│            │                        │
│            ▼                        │
│  ⑤ update_history.py               │
│     └─ topic_history.json 갱신     │
│            │                        │
│            ▼                        │
│  git commit & push (history only)   │
└─────────────────────────────────────┘
```

---

## 📁 Repository 구조

```
tistory-blog/
├── .github/
│   └── workflows/
│       └── blog_automation.yml   # 자동화 워크플로
├── scripts/
│   ├── 01_collect_news.py        # 뉴스 수집
│   ├── 02_select_topic.py        # 토픽 선정
│   ├── 03_generate_post.py       # 포스팅 생성
│   ├── 04_post_tistory.py        # 티스토리 업로드
│   ├── 05_update_history.py      # 이력 관리
│   └── get_tistory_token.py      # 토큰 발급 헬퍼 (1회용)
├── data/
│   └── topic_history.json        # 발행 이력 (Git 관리)
└── README.md
```

---

## ⚙️ GitHub Secrets 설정

| Secret 이름 | 설명 | 발급 방법 |
|:---|:---|:---|
| `GEMINI_API_KEY` | Gemini Free API 키 | [Google AI Studio](https://aistudio.google.com/) |
| `TISTORY_ACCESS_TOKEN` | 티스토리 액세스 토큰 | `scripts/get_tistory_token.py` 실행 |
| `TISTORY_BLOG_NAME` | 티스토리 블로그명 | URL의 `xxx.tistory.com`에서 `xxx` |
| `REDDIT_CLIENT_ID` | Reddit App ID (선택) | [Reddit Apps](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | Reddit App Secret (선택) | Reddit App 등록 후 확인 |

---

## 🚀 설정 순서

### 1. Repository Fork / Clone

```bash
git clone https://github.com/yourname/tistory-blog
cd tistory-blog
```

### 2. Gemini API 키 발급

1. https://aistudio.google.com/ 접속
2. **Get API Key** → **Create API Key in new project**
3. 발급된 키를 GitHub Secret `GEMINI_API_KEY`에 저장

### 3. 티스토리 앱 등록 & 토큰 발급

1. https://www.tistory.com/guide/api/manage/register 에서 앱 등록
2. `Redirect URI`: `http://localhost:8080` 입력
3. `scripts/get_tistory_token.py`의 `CLIENT_ID`, `CLIENT_SECRET` 입력 후 실행
4. 출력된 Access Token → GitHub Secret `TISTORY_ACCESS_TOKEN` 저장

### 4. 블로그명 저장

```
GitHub → Settings → Secrets → TISTORY_BLOG_NAME
예: myblog (myblog.tistory.com 인 경우)
```

### 5. 수동 실행 테스트

```
GitHub → Actions → Tistory Blog Automation → Run workflow
```

---

## 📊 뉴스 수집 전략

| 소스 | 방식 | 용도 | 비용 |
|:---|:---|:---|:---|
| Google News | RSS | 일반 IT/시장 뉴스 | 무료 |
| Yahoo Finance | RSS | 주요 기술주 관련 뉴스 | 무료 |
| Hacker News | Firebase API | 개발자 커뮤니티 관심도 | 무료 |
| Reddit | JSON API | 기술 커뮤니티 반응 | 무료 (인증 없이도 동작) |

### 토픽 선정 알고리즘

```
수집된 기사 제목/요약
        │
        ▼ Gemini (키워드 추출)
[{keyword, count, importance, reason}, ...]
        │
        ▼ 중복 필터 (최근 30일 이력)
필터된 키워드 목록
        │
        ▼ score = importance × count 정렬
상위 10개 후보
        │
        ▼ Gemini (최종 선정)
오늘의 토픽 1개
```

---

## 🔄 중복 방지 전략

- `data/topic_history.json`에 발행 이력 저장
- **최근 30일** 발행 토픽은 선정에서 자동 제외
- Git에 이력 파일 커밋 → Actions 간 상태 공유
- 모든 후보가 최근 이력과 겹칠 경우 이력 무시하고 재선정 (fallback)

---

## 📝 콘텐츠 구조

| 섹션 | 설명 |
|:---|:---|
| 1. 기술 개요 | 한 줄 정의 + 배경 |
| 2. 왜 지금 주목받는가 | 최근 트렌드 연결 |
| 3. 핵심 기술 요소 | Bullet 3~5개 |
| 4. 산업에 미치는 영향 | 파급 효과 |
| 5. 실제 적용 기업 사례 | 2~4개 기업 |
| 6. 앞으로 주목할 포인트 | 관전 포인트 |
| 7. 3줄 요약 | 핵심 정리 |

---

## ⚠️ 예상 문제점 및 대응

| 문제 | 원인 | 대응 |
|:---|:---|:---|
| Gemini rate limit | Free tier 분당 제한 | 단계별 호출, 재시도 없이 sys.exit (Actions 재실행) |
| 티스토리 Access Token 만료 | 토큰 유효기간 없음 (영구) | 앱 재등록 시에만 재발급 필요 |
| 뉴스 수집 실패 | 네트워크 오류 | 소스별 try/except, 부분 실패 허용 |
| 키워드 JSON 파싱 실패 | Gemini 출력 형식 불안정 | 정규식으로 JSON 블록 추출 + fallback |
| Reddit API 차단 | User-Agent 미설정 | User-Agent 명시, 인증 토큰 옵션 제공 |
| 중복 토픽 고갈 | 30일 이력이 너무 많을 때 | 모두 겹치면 이력 무시하고 재선정 |

---

## 💰 비용 구조

| 항목 | 비용 |
|:---|:---|
| GitHub Actions | 무료 (월 2,000분) |
| Gemini 1.5 Flash | **무료** (분당 15회, 일 1,500회) |
| Google News RSS | 무료 |
| Yahoo Finance RSS | 무료 |
| Hacker News API | 무료 |
| Reddit API | 무료 (기본 플랜) |
| **합계** | **₩0** |

> 하루 1회 실행 기준: GitHub Actions ~5분, Gemini 호출 2회 사용
