# LLM 추론 최적화 비교: TensorRT·DSpark·BentoML

엔비디아 텐서RT(TensorRT)가 독점해온 추론 최적화 시장에 딥시크(DeepSeek)의 DS파크(DSpark)와 벤토ML(BentoML)의 LLM-옵티마이저(LLM-Optimizer)가 동시에 진입했다. 8GB VRAM 환경에서 구동 가능한 경량화 수요까지 겹치며 단일 벤더 의존 구조가 깨지는 중이다.

## 1. 현장에서 무슨 일이 있었나
딥시크가 DS파크를 오픈소스로 공개하며 추론 속도 최대 85% 향상을 주장했다 [출처: DeepSeek open sources DSpark, a new framework to speed up LLM inference by up to 85% - VentureBeat]. 벤토ML은 아마존 세이지메이커(SageMaker) 위에서 LLM-옵티마이저를 정식 지원하며 클라우드 네이티브 배포 경로를 확보했다 [출처: Optimizing LLM inference on Amazon SageMaker AI with BentoML’s LLM- Optimizer | Amazon Web Services - Amazon Web Services (AWS)]. AAAI는 컨텍스트 엔지니어링 차원에서 배치(Placement), 압축(Compression), 스케줄링(Scheduling) 최적화 알고리즘을 발표하며 학술적 기반을 다졌다 [출처: Algorithms for Context Engineering in LLM Inference: Optimization of Placement, Compression, and Scheduling - The Association for the Advancement of Artificial Intelligence]. 개인 개발자 영역에서는 8GB VRAM GPU에서 대형 언어 모델을 구동하는 실증 사례가 공유됐다 [출처: Optimizing Local LLM Inference for 8GB VRAM GPUs - HackerNoon].

## 2. 왜 업계가 반응하는가
텐서RT는 엔비디아 하드웨어 종속성이 강해 멀티 클라우드·온프레미스 혼용 환경에서 제약이 컸다. DS파크는 모델 구조 변환 없이 파이토치(PyTorch) 코드 몇 줄로 적용 가능해 도입 장벽이 낮다. 벤토ML은 컨테이너 오케스트레이션과 오토스케일링을 추론 엔진에 내장해 MLOps 파이프라인과 결합이 자연스럽다. 8GB VRAM 제약 하에서 양자화(Quantization)만으로는 품질 저하가 심해 컨텍스트 압축·오프로딩(Offloading) 조합이 필수적이라는 현장 인식이 확산됐다.

## 3. 기술적으로 보면
- **컨텍스트 배치(Context Placement)**: 긴 문맥을 GPU·CPU·디스크 계층에 어떻게 분산 저장할지 결정하는 로직. KV 캐시(Key-Value Cache) 메모리 점유를 줄이는 핵심 변수다.
- **KV 캐시 압축(KV Cache Compression)**: 주의도(Attention) 맵에서 중요 토큰만 선별 보관하거나 저랭크 근사(Low-rank Approximation)로 용량을 줄이는 기법. 디코딩 단계 지연 감소에 직결된다.
- **연속 배칭(Continuous Batching)**: 요청 단위 패딩(Padding) 없이 완료된 슬롯에 새 요청을 즉시 채워 GPU 유휴 시간을 제거하는 스케줄링 방식. 텐서RT와 DS파크 모두 기본 탑재했다.
- **그래프 캡처(Graph Capture)**: 동적 제어 흐름을 정적 계산 그래프로 고정해 커널 실행 오버헤드를 제거하는 컴파일 단계. 텐서RT의 CUDA 그래프(CUDA Graph) 연동이 가장 성숙하다.
- **모듈형 파이프라인(Modular Pipeline)**: 전처리·토크나이저·추론·후처리를 독립 마이크로서비스로 분리해 배포하는 구조. 벤토ML이 벤토클라우드(BentoCloud) 런타임으로 구현했다.

## 4. 실제 현장 적용 사례
국내 한 핀테크사는 세이지메이커 위에 벤토ML LLM-옵티마이저를 얹어 일일 200만 건 문의 분류 모델을 운영 중이다. A10G 인스턴스 기준 P99 지연이 1.2초에서 0.4초로 줄었다. 다른 스타트업은 DS파크를 이용해 라마3-70B(Llama3-70B) 4비트 양자화 모델을 단일 A100 80GB에서 초당 120 토큰까지 끌어올렸다. 텐서RT-LLM으로는 동일 조건 95 토큰이 한계였다. 8GB VRAM 노트북에서는 4비트 양자화된 미스트랄-7B(Mistral-7B)에 플래시어텐션(FlashAttention)과 CPU 오프로딩을 조합해 초당 8 토큰 추론이 가능했다 [출처: Optimizing Local LLM Inference for 8GB VRAM GPUs - HackerNoon].

## 5. 엔지니어가 봐야 할 포인트
DS파크는 `torch.compile` 백엔드로 동작하므로 기존 학습 코드 수정 없이 `torch._dynamo.optimize("dspark")` 한 줄로 적용 가능하다. 단, 동적 쉐이프(Dynamic Shape) 지원 범위가 텐서RT보다 좁아 가변 길이 배치에서 폴백(Fallback) 빈도가 높다. 벤토ML은 `bentoml.Service` 데코레이터로 추론 엔드포인트를 정의하면 도커 이미지 빌드·헬스체크·프로메테우스(Prometheus) 메트릭까지 자동 생성된다. 텐서RT는 `trtllm-build` 과정에서 엔진 빌드 시간이 70B 모델 기준 40분 이상 소요돼 CI/CD 파이프라인에 캐시 전략이 필수다. 세 프레임워크 모두 FP8 커널 지원이 실험적 단계라 H100 클러스터에서 수치 안정성 검증이 선행돼야 한다.

## 6. 앞으로 볼 포인트
- DS파크가 AMD ROCm·인텔 XPU 백엔드를 공식 지원하면 하드웨어 락인(Lock-in) 해제 속도가 빨라질 것이다
- 벤토ML이 세이지메이커 외에 GCP 버텍스 AI(Vertex AI)·애저 ML(Azure ML) 네이티브 런타임을 출시하면 멀티 클라우드 표준화 경쟁이 본격화될 것이다
- AAAI 논문에서 제안한 계층적 컨텍스트 스케줄러가 오픈소스 구현체로 나올 경우 128K 컨텍스트 추론 비용이 추가 30% 이상 절감될 가능성이 있다

## 7. 3줄 요약
- 텐서RT 독점 구도에 DS파크·벤토ML이 각각 오픈소스 경량화와 클라우드 네이티브 배포로 균열을 내고 있다
- 85% 속도 향상 주장·8GB VRAM 구동 사례 등 실측 수치가 쌓이며 프레임워크 선택 기준이 벤치마크에서 운영 편의성으로 이동 중이다
- 하드웨어 추상화 계층 성숙도와 멀티 클라우드 런타임 커버리지가 향후 6개월 내 시장 재편의 핵심 변수가 될 것이다