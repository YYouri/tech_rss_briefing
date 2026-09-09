# AI Data Center 동향과 전망

퀄컴과 아마존웹서비스(AWS)가 차세대 AI 데이터센터 인프라를 공동 개발한다는 다중 세대 제품 협업을 발표했다. 시장은 205년까지 AI 데이터센터 투자 규모가 32조 달러에 달할 것으로 내다보는데, 이는 철도나 인터넷망 구축 비용을 뛰어넘는 수준이다. 회사에서 인프라 스펙을 검토할 때면 이제는 전력 밀도와 냉각 용량이 랙 단위에서 논의되는 것이 당연해졌다.

## 1. 현장에서 무슨 일이 있었나
퀄컴이 AWS와 손잡고 커스텀 AI 데이터센터 인프라를 다중 세대에 걸쳐 개발하기로 했다. 기존 스마트폰·PC용 칩셋 강자가 클라우드 하이퍼스케일러의 전용 실리콘 파트너로 진입한 것이다. 동시에 TCS는 인도 텔랑가나주에 하이퍼볼트(HyperVault)라는 대규모 AI 데이터센터 캠퍼스를 조성한다고 밝혔다. 미국 텍사스주 러벅에서는 데이터센터 부지 매입을 둘러싼 지역 사회 반발이 시위로 번졌다. 농업용지 잠식과 전력망 과부하 우려가 표면화된 것이다. 주가 반응도 즉각적이었다. 퀄컴 발표 당일 인텔, 암코어, 노바, 퀄컴, 포름팩터 주가가 동반 상승했다. ASML과 TSMC, 인텔이 차세대 칩 제조 마일스톤을 달성한 소식도 겹쳤다. [출처: Qualcomm Announces Multi-Generational Product Collaboration with Amazon to Build Next-Generation AI Data Center Infrastructure] [출처: AI data centers are transforming rural land markets — and fueling a backlash] [출처: Intel, Amkor, Nova, Qualcomm, and FormFactor Stocks Trade Up, What You Need To Know]

## 2. 왜 업계가 반응하는가
투자 규모가 기존 인프라 역사를 다시 쓰고 있다. 2050년까지 누적 투자액 32조 달러는 철도, 전력망, 인터넷 구축 비용을 모두 합친 것보다 크다. [출처: AI data center investment projected to hit $32 trillion by 2050 — infrastructure spending estimated to exceed capital requirements for railways, electrification, or the internet] 반도체 시장만 떼어 봐도 2035년 2,559억 달러 규모로 성장이 예상된다. AI 데이터센터 확장, 고성능 AI 실리콘, 엣지 컴퓨팅 확산이 동력이다. [출처: AI in semiconductor market to be worth $255.90bn by 2035, due to AI data center expansion, advanced AI silicon, and edge computing adoption] 자본 지출(CAPEX) 싸이클이 하드웨어 제조사부터 전력 장비, 부동산, 냉각 설비까지 전방위로 확산 중이다. 실무에서 예산 계획을 잡을 때면 3~5년 단위 CAPEX가 데이터센터 한 건물 짓는 비용으로만 수천억 원 단위로 잡힌다.

## 3. 기술적으로 보면
- **커스텀 실리콘(Custom Silicon)**: 특정 워크로드(추론, 학습, 데이터 전처리)에 최적화된 전용 칩. 범용 GPU 대비 와트당 성능비 개선이 핵심이다.
- **랙 스케일 아키텍처(Rack-scale Architecture)**: 개별 서버가 아닌 랙 단위로 전력, 냉각, 네트워크를 통합 설계하는 방식. CXL(Compute Express Link) 기반 메모리 풀링이 동반된다.
- **액체 냉각(Liquid Cooling)**: 공랭 한계(랙당 30~50kW)를 넘어 100kW 이상 고밀도 랙을 감당하기 위한 필수 기술. 침수식과 직접 접촉식(DTC)이 혼용된다.
- **고전압 직류 배전(HVDC Power Distribution)**: 변환 손실 최소화를 위해 48V 또는 400Vdc 버스 바를 랙까지 내리는 배전 방식. UPS와 배터리 통합도 용이하다.
- **CXL 기반 메모리 풀링(CXL Memory Pooling)**: 서버 간 메모리 공유로 유휴 메모리 낭비를 줄이고 대용량 모델 추론 시 메모리 용량 병목 완화.

## 4. 실제 현장 적용 사례
AWS는 그래비톤(Graviton) 시리즈로 암(Arm) 기반 커스텀 CPU를 이미 상용화했다. 여기에 퀄컴의 추론 가속기 혹은 네트워크 프로세싱 유닛(NPU)을 결합해 '트레이닝-추론 파이프라인' 전체를 커스텀 실리콘으로 커버하려는 그림으로 보인다. TCS 하이퍼볼트 캠퍼스는 모듈러 데이터센터 설계를 적용해 전력 인입부터 쿨링 타워까지 프리패브(Pre-fab) 단위로 현장 조립한다. 구축 기간을 기존 18개월에서 12개월 내외로 단축하는 것이 목표다. 국내 모 통신사 프로젝트에서도 랙당 80kW 설계가 들어와 수냉식 CDU(Coolant Distribution Unit) 선정과 매니폴드 배관 공정 검토에 실무 투입된 경험이 있다. 전력 밀도 상승에 따른 바닥 하중 보강과 누수 감지 센서 망 설계가 병행 이슈로 따라온다.

## 5. 엔지니어가 봐야 할 포인트
회사에서 인프라 RFP를 뜯어보면 스펙 표에 '랙당 kW' 숫자만 있고 냉각 방식은 '협의'로 되어 있는 경우가 많다. 이때 액체 냉각 도입 여부가 전체 TCO를 가른다.CDU 용량 선정 시 리던던시(N+1) 적용 여부와 쿨란트 종류(불소계 vs 수계)에 따른 누수 리스크 평가까지 문서화해야 한다. 전력 쪽에서는 HVDC 버스 바 전압 등급(48V vs 400Vdc)에 따라 PDU, 버스웨이, 차단기 선정 스펙이 완전히 갈린다. 나는 400Vdc 쪽이 중장비급 장비 연동에 유리하다고 보지만, 인증 장비 풀(Pool)이 아직 얇아 조달 리드타임이 길다. 네트워크 단에서는 RoCE v2와 UEC(Ultra Ethernet Consortium) 스펙 준수 여부를 NIC 펌웨어 레벨에서 확인해야 패킷 드랍 없는 학습 클러스터가 나온다. 소프트웨어 스택 최적화 없이 하드웨어만 증설하면 GPU 이용률 30% 벽을 못 넘는다.

## 6. 앞으로 볼 포인트
- 전력망 인입 지연과 변전소 용량 확보가 데이터센터 준공 일정의 병목이 될 것이다
- 커스텀 실리콘 공급망 다변화(파운드리, 패키징, 테스트)가 단일 벤더 리스크를 어떻게 완화할지 지켜봐야 한다
- 냉매 규제(PFAS 제한)와 수계 냉각 전환 시 CDU·매니폴드 재질 변경에 따른 추가 비용 산정이 필요하다

## 7. 3줄 요약
- 퀄컴-AWS 협업과 32조 달러 투자 전망으로 AI 인프라 자본 지출 싸이클이 본격화됐다
- 랙 단위 고밀도 전력·냉각·네트워크 통합 설계가 엔지니어 필수 역량으로 자리 잡았다
- 전력망 제약, 냉매 규제, 커스텀 칩 공급망 리스크가 향후 3~5년 프로젝트 성패를 가를 변수다