# 제로트러스트, AI 에이전트 시대 필수 아키텍처

AI 에이전트가 사내 시스템에 접속해 데이터베이스를 조회하고 외부 API를 호출하는 상황을 지난 분기 프로젝트에서 처음 맞닥뜨렸다. 사람이 아닌 코드가 자격증명을 들고 게이트웨이를 통과하는 순간 기존 제로트러스트 정책은 맹점을 드러냈다. 오터리미트(Outerlimit)가 프리시드(Pre-Seed) 단계에서 1600만 달러를 유치하며 이 공백을 노린 것도 같은 맥락이다. [출처: Outerlimit Raises $16 Million Pre-Seed To Launch Zero Trust Security Platform For AI Agents]

## 1. 현장에서 무슨 일이 있었나
오터리미트는 자율형 AI 에이전트를 위한 제로트러스트 보안 레이어를 구축한다는 목표로 1600만 달러 규모 프리시드 투자를 유치했다. [출처: Outerlimit Raises $16M to Build Zero Trust Security Layer for Autonomous AI Agents] 더해커뉴스(The Hacker News)는 현재 환경이 '제로 비저빌리티(Zero Visibility)' 상태라 지적했다. 에이전트가 어떤 자원으로 이동했는지, 어떤 권한을 위임받았는지 추적할 수단이 없다는 뜻이다. 세미텍(Semtech)과 팔로알토 네트웍스(Palo Alto Networks)는 산업용 사물인터넷(IIoT) 환경에 제로트러스트를 적용하며 비인간 엔티티(Non-Human Identity) 검증 문제를 현실로 끌어올렸다. [출처: Semtech and Palo Alto Networks Secure Industrial IoT with Zero Trust]

## 2. 왜 업계가 반응하는가
기존 제로트러스트는 '사용자'를 중심으로 설계됐다. 다단계 인증(MFA), 단일 로그인(SSO), 기기 상태 검증 모두 사람 행위자(Actor)를 전제로 한다. AI 에이전트는 사람과 달리 수명 주기가 짧고, 복제되며, 위임 권한이 동적으로 변한다. 서비스 계정(Service Account)이나 API 키(Key) 같은 정적 자격증명으로는 에이전트 행위를 세밀하게 통제할 수 없다. ADT매거진(ADTmag)은 기업이 AI 도입 속도에 맞춰 제로트러스트 플레이북을 다시 쓰지 않으면 권한 과잉(Over-privilege)과 추적 불가(Untraceable) 리스크가 동시에 터진다고 경고했다. [출처: Tech Spotlight | Balancing Zero Trust and AI: A Playbook for Modern Enterprises]

## 3. 기술적으로 보면
- **비인간 엔티티(Non-Human Identity, NHI)**: 사람 외 소프트웨어 주체 전체를 지칭. 서비스 계정, 컨테이너, 에이전트, 스크립트, 머신투머신(M2M) 클라이언트 포함.
- **에이전트 아이덴티티(Agent Identity)**: 특정 작업 단위로 발급되는 일회성 혹은 단기 자격증명. 스피페(SPIFFE) 같은 워크로드 아이덴티티 표준과 결합해 수명 주기 자동화.
- **제로 비저빌리티(Zero Visibility)**: 에이전트 행위가 로그에 남지 않거나, 상관관계 분석이 안 돼 탐지 공백이 생긴 상태. 더해커뉴스가 핵심 병목으로 지목. [출처: Zero Trust for AI Agents Starts With Fixing Zero Visibility]
- **지속적 검증(Continuous Verification)**: 인증 시점뿐 아니라 실행 중 컨텍스트(호출 대상, 데이터 민감도, 행위 패턴)를 지속 평가해 권한 동적 조정.
- **정책 결정 지점(Policy Decision Point, PDP) 확장**: 기존 PDP가 사용자 속성만 봤다면, 에이전트 메타데이터(모델 버전, 프롬프트 해시, 호출 체인)까지 입력받아 실시간 판정 수행.

## 4. 실제 현장 적용 사례
오터리미트는 에이전트 런타임에 사이드카(Sidecar) 프록시를 심어 모든 아웃바운드(Outbound) 트래픽을 가로채고, 에이전트별 정책을 PDP에 질의하는 아키텍처를 시연했다. 세미텍과 팔로알토 네트웍스는 산업 현장 게이트웨이에 제로트러스트 네트워크 액세스(ZTNA) 에이전트를 탑재해, 센서·액추에이터·엣지 AI 모듈 간 통신을 상호 인증(mTLS) 방식으로 전환했다. [출처: Semtech and Palo Alto Networks Secure Industrial IoT with Zero Trust] 국내 한 금융사 PoC에서는 LLM 기반 코드 리뷰 봇(Bot)이 깃허브(GitHub) 토큰(Token)을 장기 보관하다 유출된 사례가 있었는데, 단기 자격증명 발급기(Issuer)와 감사 로그 연계로 해결했다.

## 5. 엔지니어가 봐야 할 포인트
회사에서 PoC를 돌리며 느낀 점은 토큰 발급·폐기 사이클이 초 단위로 돌아갈 때 기존 키 관리 시스템(KMS) 병목이 심하다는 것이다. 스피레(SPIRE) 같은 워크로드 아이덴티티 발급기를 쿠버네티스(Kubernetes) 컨트롤 플레인 옆에 붙여도, PDP가 에이전트 메타데이터를 파싱해 판정하는 레이턴시(Latency)가 50밀리초(ms) 넘어가면 서비스 레벨 목표(SLO) 지키기 힘들다. 내가 보기엔 정책 언어를 리고(Reg) 같은 결정론적 언어로 짜고, PDP 캐시 계층을 두는 설계가 필수다. 또 에이전트 간 호출 체인(Call Chain) 전체에 추적 ID(Trace ID)를 강제 주입하지 않으면 제로 비저빌리티는 해결되지 않는다.

## 6. 앞으로 볼 포인트
- SPIFFE·와임세(WIMSE) 표준 기반 에이전트 아이덴티티 상호 운용성 논의 진전 여부
- PDP 성능 병목 해소를 위한 엣지(Edge) 측 정책 캐시·프리컴퓨트(Pre-compute) 아키텍처 확산
- 소프트웨어 공급망(Supply Chain) 내 모델·프롬프트·도구(Tool) 무결성 검증을 제로트러스트 정책에 통합하는 흐름

## 7. 3줄 요약
- AI 에이전트 확산으로 비인간 엔티티 인증·인가 공백이 제로트러스트 핵심 과제로 부상
- 오터리미트 1600만 달러 투자 유치, 세미텍·팔로알토 산업 현장 적용 등 시장 검증 시작
- 엔지니어는 단기 자격증명 발급 자동화, PDP 레이턴시 최적화, 호출 체인 추적성 구현에 집중해야 함