# LLM 추론 최적화: 비용과 지연 시간 단축 전략

지난 분기 사내 GPU 클러스터 증설 요청이 반려됐다. 비용 산출서를 다시 쓰면서 추론 단계에서 나가는 돈이 학습 비용을 훌쩍 넘긴다는 사실을 뼈저리게 느꼈다. 이제는 모델 크기만 키우는 게 아니라, 주어진 하드웨어에서 어떻게 짜내느냐가 생존 문제다.

## 1. 현장에서 무슨 일이 있었나

대용량 언어 모델을 서비스에 올리니 가장 먼저 만난 병목은 KV 캐시(Key-Value Cache) 메모리였다. 컨텍스트 길이가 길어질수록 GPU 메모리가 선형으로 차오른다. 배치 크기를 키워 처리량을 올리려다 OOM(Out Of Memory) 에러만 반복해서 봤다. 스케줄러가 요청을 FIFO(First In First Out)로만 넣으니 선두 요청이 길면 뒤쪽 짧은 요청이 무한 대기하는 헤드 오브 라인 블로킹(Head-of-line Blocking) 현상도 심각했다. 클라우드 인스턴스 요금 청구서를 보며 추론 최적화가 선택이 아니라 필수임을 깨달았다.

## 2. 왜 업계가 반응하는가

GPU 가격은 떨어지지 않는데 모델 파라미터 수는 계속 커진다. 기업 입장에서는 토큰 당 비용(Cost per Token)과 사용자 체감 지연 시간(Time To First Token, TTFT)이 핵심 지표다. 기사에 나온 딥시크(DeepSeek) DSpark가 추론 속도를 최대 85% 높였다는 소식은 하드웨어 교체 없이 소프트웨어 스택만으로 비용을 반토막 낼 수 있음을 보여준다[출처: DeepSeek open sources DSpark, a new framework to speed up LLM inference by up to 85% - VentureBeat]. 아마존 세이지메이커(SageMaker)에서 벤토엠엘(BentoML) 옵티마이저로 자동 튜닝하는 사례 역시 운영 자동화 수요가 크다는 방증이다[출처: Optimizing LLM inference on Amazon SageMaker AI with BentoML’s LLM- Optimizer - Amazon Web Services (AWS)]. 8기가바이트 비램(VRAM) 환경에서도 로컬 추론을 돌리는 엔지니어들의 공유 코드가 끊이지 않는 이유도 같다[출처: Optimizing Local LLM Inference for 8GB VRAM GPUs - HackerNoon].

## 3. 기술적으로 보면

- **페이지드어텐션(PagedAttention)**: KV 캐시를 고정 크기 블록으로 나눠 물리 메모리에 비연속적으로 저장한다. 운영체제 가상 메모리 아이디어를 차용해 메모리 단편화를 줄이고 공유 프픽스(Prefix) 캐싱을 가능하게 한다.
- **연속배칭(Continuous Batching / Iteration-level Scheduling)**: 요청 단위가 아닌 토큰 생성 단위로 스케줄링한다. 끝난 요청은 즉시 빼고 새 요청을 넣어 GPU 유휴 시간을 최소화한다.
- **양자화(Quantization)**: 가중치와 활성화 값을 FP16이나 BF16에서 INT4, INT8로 낮춰 메모리 대역폭 압박을 푼다. GPTQ, AWQ, GGUF 포맷이 현장 표준처럼 쓰인다.
- **스페큘레이티브 디코딩(Speculative Decoding)**: 소형 드래프트 모델이 다음 토큰 여러 개를 예측하고, 대형 타깃 모델이 한 번에 검증한다. 수락률이 높을수록 디코딩 단계가 줄어 지연 시간이 준다.
- **컨텍스트 엔지니어링(Context Engineering)**: AAAI 논문에서 다룬 배치(Placement), 압축(Compression), 스케줄링(Scheduling) 삼박자를 뜻한다. 긴 컨텍스트를 통째로 올리지 않고 필요 구간만 선별하거나 요약해 KV 캐시 점유율을 낮춘다[출처: Algorithms for Context Engineering in LLM Inference: Optimization of Placement, Compression, and Scheduling - The Association for the Advancement of Artificial Intelligence].

## 4. 실제 현장 적용 사례

브이엘엘엠(vLLM)은 페이지드어텐션과 연속배칭을 오픈소스 수준에서 처음 구현해 사실상 표준 엔진이 됐다. 우리 팀도 브이엘엘엠으로 마이그레이션한 뒤 동일 하드웨어에서 처리량이 2배 가까이 올랐다. 딥시크가 공개한 DS파크(DSpark)는 어텐션 연산 커널 최적화와 메모리 액세스 패턴 재설계로 기존 대비 최대 85% 성능 향상을 주장했다[출처: DeepSeek open sources DSpark, a new framework to speed up LLM inference by up to 85% - VentureBeat]. 클라우드 쪽에서는 벤토엠엘이 세이지메이커 위에서 모델별 최적 배치 크기, 텐서 패러럴리즘(Tensor Parallelism) 정도, 양자화 비트를 자동 탐색해준다[출처: Optimizing LLM inference on Amazon SageMaker AI with BentoML’s LLM- Optimizer - Amazon Web Services (AWS)]. 엣지 단에서는 8기가바이트 비램 제약 아래 레이어 오프로딩(Layer Offloading)과 4비트 양자화를 조합해 7B~13B 모델을 돌리는 레시피가 공유된다[출처: Optimizing Local LLM Inference for 8GB VRAM GPUs - HackerNoon].

## 5. 엔지니어가 봐야 할 포인트

회사에서 처음 브이엘엘엠을 올릴 때 처리량만 보고 배치 사이즈를 무작정 키웠다가는 TTFT가 튀는 걸 봤다. 실무에서 보면 처리량(Throughput)과 지연 시간(Latency)은 트레이드오프 관계다. 프로파일러로 커널 실행 시간, 메모리 대역폭 사용률, SM 점유율을 찍어봐야 병목이 보인다. 양자화도 무조건 4비트가 답이 아니다. 정확도 하락이 허용 범위인지 평가셋으로 검증하고, 커널이 하드웨어에서 제대로 도는지(NVIDIA 호퍼(Hopper) 아키텍처의 FP8 텐서 코어 등) 확인해야 한다. 스케줄러 파라미터(최대 토큰 수, 프리필 청크 크기)는 트래픽 패턴에 맞춰 계속 튜닝해야 한다. 벤치마크 숫자만 믿고 프로덕션에 올리면 장애난다.

## 6. 앞으로 볼 포인트

- 하드웨어 세대별 전용 커널(Hopper FP8, 블랙웰(Blackwell) TMA 등)과 추론 엔진의 긴밀한 결합이 가속화될 것이다
- 소형 언어 모델(SLM) 특화 양자화·프루닝(Pruning) 파이프라인이 온디바이스·엣지 배포 표준이 될 것이다
- 긴 컨텍스트 처리를 위한 KV 캐시 압축·선별 기법이 모델 아키텍처 레벨에서 기본 탑재될 것이다

## 7. 3줄 요약

- 추론 비용과 지연 시간을 잡으려면 페이지드어텐션, 연속배칭, 양자화 같은 소프트웨어 스택 최적화가 선행되어야 한다
- DS파크 85% 가속, 벤토엠엘 자동 튜닝, 8GB VRAM 구동 사례처럼 오픈소스와 클라우드 도구가 실질적 대안이 되고 있다
- 엔지니어는 벤치마크 수치보다 프로파일링 기반 병목 분석과 트래픽 패턴 맞춤 튜닝에 집중해야 한다