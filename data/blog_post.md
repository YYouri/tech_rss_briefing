# Agentic AI 동향과 전망

회사에서 반도체 설계 자동화 툴 PoC를 돌리던 지난달, 에이전트 하나가 레이아웃 검증 스크립트를 스스로 짜고 시뮬레이션 돌리고 리포트까지 뽑아내는 걸 봤다. 사람 손이 가던 3주 치 일정이 이틀 만에 끝났다.

## 1. 현장에서 무슨 일이 있었나
중국 EDA 업체 엠피리언은 자사 에이전틱 AI를 써서 회로 설계 시간을 75% 줄였다고 발표했다 [출처: Chinese Chip Firm Empyrean Says It Slashed Circuit Design Time By 75% Using Agentic AI Amidst Race To Agentic AI Semiconductor Design - Wccftech]. 세일즈포스는 파트너 생태계를 동원해 영업·서비스·마케팅 워크플로에 에이전트를 심고 있다 [출처: Salesforce (CRM) Sees Fresh Partner Tools Push Agentic AI Into Enterprise Workflows - Yahoo Finance]. 제조 현장에서는 벤션이 IMTS 2026에서 물리 AI와 에이전틱 AI를 한 플랫폼에 묶어 선보였다 [출처: Vention Facilitates Manufacturing at IMTS 2026 with Physical AI and Agentic AI in One Platform - PR Newswire]. 엔비디아(NWN)는 AWS 에이전틱 AI 컴피턴시를 따고 파일럿 단계를 넘어 프로덕션 전환을 지원 중이다 [출처: NWN Earns AWS Agentic AI Competency, Helping Enterprises Move AI Agents from Pilots to Production - Business Wire].

## 2. 왜 업계가 반응하는가
테라데이터 조사에 따르면 금융·통신·제조 등 주요 산업이 이미 도입을 서두르지만 데이터 파편화와 규제 장벽이 공통 걸림돌로 나온다 [출처: Which industries are ahead in agentic AI, and the common challenge they all face - kpvi.com]. 맥킨지는 파일럿을 전사 규모로 키우려면 거버넌스·옵저버빌리티·비용 모델을 처음부터 설계해야 한다고 지적한다 [출처: Stacking the odds: A blueprint for successfully scaling agentic AI - McKinsey & Company]. 책임 AI 기구는 이사진을 보강하며 거버넌스 프레임워크를 정비하고 있다 [출처: Responsible AI Institute Adds Three Leaders to Governing Board for the Agentic AI Era - PR Newswire]. CIO들은 레거시 인프라 위에 에이전트 레이어를 얹는 대신 아키텍처 자체를 다시 짜야 한다고 말한다 [출처: Rethinking and realigning IT for the agentic AI era - cio.com].

## 3. 기술적으로 보면
- **계획 수립(Planning)**: 목표를 받아 하위 태스크로 분해하고 실행 순서를 정한다. 체인 오브 소트(Chain of Thought) 프롬프트만으로는 부족해 트리 탐색이나 몬테카를로 트리 서치를 결합한다.
- **도구 사용(Tool Use)**: API·CLI·SDK를 호출해 외부 시스템을 제어한다. 함수 스키마 정의와 인증 토큰 관리가 런타임에 동적으로 이뤄져야 한다.
- **메모리(Memory)**: 단기 컨텍스트 윈도우와 장기 벡터 스토어를 분리한다. 임베딩 모델 교체 시 재색인 비용이 크므로 버전 관리 전략이 필수다.
- **반성(Reflection)**: 실행 결과를 스스로 평가하고 재시도 루프를 돈다. 휴리스틱 룰과 LLM 판단을 혼합해 거짓 긍정(false positive)을 줄인다.
- **멀티 에이전트 오케스트레이션**: 감독자 에이전트가 전문 에이전트들에게 태스크를 분배하고 상태를 동기화한다. 메시지 버스나 이벤트 소싱 패턴을 쓴다.

## 4. 실제 현장 적용 사례
반도체 설계팀은 넷리스트 생성부터 타이밍 클로저까지 전 단계를 에이전트 체인으로 연결했다. 영업 조직은 리드 자격 심사·견적 생성·계약서 초안 작성을 각각 별도 에이전트에 맡겨 처리 시간을 60% 단축했다. 스마트 팩토리 라인에서는 비전 검사 에이전트가 불량 이미지를 분류하고, 제어 에이전트가 로봇 암 궤적을 실시간 수정한다. 모바일 단말에서는 퀄컴 헥사곤 NPU가 온디바이스 추론을 담당해 네트워크 지연 없이 에이전트 루프를 돈다 [출처: Hexagon NPU: A new mobile architecture for agentic AI - Qualcomm].

## 5. 엔지니어가 봐야 할 포인트
실무에서 보면 프롬프트 엔지니어링보다 에이전트 상태 머신 설계가 더 어렵다. 툴 호출 실패 시 롤백 로직을 어디까지 자동화할지, 사람 개입 포인트(Human-in-the-loop)를 어떤 태스크에 둘지 정하는 게 아키텍처 핵심이다. 옵저버빌리티는 토큰 사용량·지연시간·성공률을 태스크 단위로 쪼개 봐야 한다. 거버넌스는 데이터 혈통 추적과 결정 근거 로그를 감사 추적용으로 남기는 작업부터 시작한다. 우리 팀은 랭체인(LangChain) 대신 랭그래프(LangGraph)로 상태 그래프를 짜고, 오픈텔레메트리(OpenTelemetry)로 분산 트레이싱을 박았다.

## 6. 앞으로 볼 포인트
- 엣지 디바이스 NPU 성능 향상이 온디바이스 에이전트 자율성을 어디까지 끌어올릴지
- 규제 대응용 설명 가능성(Explainability) 모듈이 에이전트 루프 안에 표준으로 들어갈지
- 데이터 파편화 문제를 풀기 위한 페더레이티드 카탈로그·세맨틱 레이어 구축 경쟁

## 7. 3줄 요약
- 에이전틱 AI가 반도체·엔터프라이즈·제조 현장에서 파일럿을 넘어 프로덕션으로 진입 중
- 계획·도구·메모리·반성·오케스트레이션 5대 구성요소 구현 난도가 프롬프트 튜닝보다 높음
- 거버넌스·옵저버빌리티·데이터 통합을 아키텍처 초기에 설계하지 않으면 스케일 아웃 불가