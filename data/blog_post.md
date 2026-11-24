# AI 데이터센터 전력과 냉각, 핵심 인프라 이해

회사에서 새 추론 클러스터 견적을 받아온 날, 회의는 랙당 전력 숫자에서 먼저 멈췄습니다. GPU 단가보다 전력 인입 계통과 냉각 배관 용량이 발목을 잡았기 때문입니다. AI 데이터센터 논쟁의 무게중심이 모델에서 설비로 옮겨간 장면입니다.

## 1. 현장에서 무슨 일이 있었나

Applied Digital이 하이퍼스케일러와 54억 달러 규모의 AI 데이터센터 임대 계약을 맺었습니다. [출처: Applied Digital Secures $5.4 Billion AI Data Center Lease with Hyperscaler] 건물을 지어 임대하는 방식이 AI 학습·추론 수요와 직접 묶인 사례입니다.

미국 뉴저지에서는 주 산업협회가 AI 데이터센터 정책 권고안을 냈습니다. [출처: NJBIA Report Makes Policy Recommendations for NJ AI Data Centers] 전력, 용수, 인허가, 지역 부담을 어떻게 나눌지가 쟁점으로 올라왔습니다.

연방 상원 법안을 두고는 AI 데이터센터와 화석연료 인프라를 함께 빠르게 승인하는지 논쟁이 붙었습니다. [출처: Does Senate bill fast-track AI data centers and fossil fuel infrastructure, as Mark Ruffalo says?] 같은 시기 트럼프 측은 미국 기업이 해외에 AI 데이터센터를 지을 경우 불이익을 주겠다는 방침을 내놨습니다. [출처: Trump seeks to penalize US companies that build AI data centers abroad, even as they face backlash]

케이블 포설 문제도 별도 주제로 다뤄집니다. [출처: Solving cabling challenges behind AI data center growth] 사모 인프라 자금은 데이터센터와 전력 설비로 수십억 달러 단위로 유입되고 있습니다. [출처: The AI data center boom is driving billions into private infrastructure]

## 2. 왜 업계가 반응하는가

AI 데이터센터는 전력을 사오는 시설이 아니라 전력 계통을 새로 협상하는 시설입니다. 변전소 인입 용량, 송전 대기열, 발전 연계 일정이 건물 착공보다 늦게 확정되는 일이 흔합니다.

임대 계약이 길어질수록 전력 확보는 계약 조건이 됩니다. 하이퍼스케일러가 54억 달러를 걸었다는 것은 [출처: Applied Digital Secures $5.4 Billion AI Data Center Lease with Hyperscaler] 건물만 보고 돈을 낸 것이 아니라 전력 인입과 냉각 용량까지 확인했다는 뜻입니다.

정책 리스크도 입지 결정을 흔듭니다. 뉴저지처럼 주 단위 권고안이 나오고, [출처: NJBIA Report Makes Policy Recommendations for NJ AI Data Centers] 상원 법안과 해외 건설 규제가 동시에 움직이면 사업자는 국가와 주를 넘나들며 조건을 비교합니다.

## 3. 기술적으로 보면

- **랙당 전력 밀도**: 한 랙이 끌어쓰는 전력량입니다. 공랭으로 감당하던 수준을 넘으면 액체냉각으로 전환해야 하고, 전원 케이블 굵기와 분전반 구성이 함께 바뀝니다.
- **CDU(냉각수 분배 장치)**: 칩 냉각 루프와 외부 냉각 계통 사이에서 열을 교환하는 설비입니다. 용량 산정이 틀리면 랙 전체가 쓰로틀링에 걸립니다.
- **다이렉트 투 칩 냉각**: 콜드플레이트를 GPU에 직접 붙여 열을 빼는 방식입니다. 공기 대신 배관이 들어오므로 상면 공간과 누수 감지 설계가 달라집니다.
- **버스웨이**: 랙 위로 전력을 나눠 보내는 도체 트레이입니다. 케이블 포설량을 줄이지만 증설 시 차단 범위를 미리 정해야 합니다.
- **PUE**: 전체 전력 대비 IT 전력 비율입니다. 낮을수록 냉각 효율이 좋지만, 운영 현장에서는 냉각수 온도와 유량이 실제 지표로 쓰입니다.

## 4. 실제 현장 적용 사례

Applied Digital 사례는 전력 확보를 선행 조건으로 둔 건설·임대 모델입니다. [출처: Applied Digital Secures $5.4 Billion AI Data Center Lease with Hyperscaler] 부지를 먼저 잡고 계통 협의를 마친 뒤 임차인을 받는 순서입니다.

뉴저지 권고안은 주 정부 차원의 전력 계획과 인허가 정비를 요구합니다. [출처: NJBIA Report Makes Policy Recommendations for NJ AI Data Centers] 데이터센터를 개별 민원이 아니라 지역 인프라 계획 안에 넣자는 접근입니다.

케이블 현장에서는 고밀도 랙 때문에 광 케이블과 전원 케이블을 분리 배치하고, 굽힘 반경과 트레이 적재 하중을 다시 계산합니다. [출처: Solving cabling challenges behind AI data center growth] 랙 하나가 바뀌어도 케이블 샤프트 전체 도면이 바뀝니다.

## 5. 엔지니어가 봐야 할 포인트

실무에서 보면 계통도가 설계도보다 먼저입니다. 인입 용량, 이중화 방식, 변압기 리드타임을 확인하지 않으면 서버 발주 일정은 의미가 없습니다.

냉각 방식이 케이블과 배관 표준을 결정합니다. 공랭 전제로 잡은 트레이와 바닥 높이는 액체냉각으로 바꾸는 순간 재설계 대상입니다.

내가 보기엔 PUE 숫자보다 냉각수 공급 온도, 유량, CDU 이중화가 운영 안정성을 더 잘 보여줍니다. 계약서에는 전력 인입 용량과 증설 우선권 조항을 명시해야 합니다.

## 6. 앞으로 볼 포인트

- 전력 인입 계약과 인허가 일정이 건물 착공 일정과 어떻게 맞물리는지
- 공랭에서 액체냉각으로 넘어갈 때 케이블·배관 표준이 어디까지 바뀌는지
- 해외 건설 규제와 주 단위 정책이 입지 선택에 어떤 변수로 작용하는지

## 7. 3줄 요약

- AI 데이터센터 경쟁은 GPU 확보가 아니라 전력 인입과 냉각 용량 확보 경쟁으로 이동했습니다.
- 54억 달러 임대 계약과 주 단위 정책 권고안은 설비와 제도가 함께 묶여 움직인다는 신호입니다. [출처: Applied Digital Secures $5.4 Billion AI Data Center Lease with Hyperscaler]
- 현장에서는 계통도, 냉각 방식, 케이블 포설 기준을 먼저 확인해야 일정과 비용이 어긋나지 않습니다.