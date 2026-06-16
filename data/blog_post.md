# On-Device AI, 스마트폰·IoT 현황과 미래 전망

스마트폰에 최신 AI 기능이 바로 적용되면서, 사용자는 네트워크 지연 없이 실시간 영상 편집·음성인식 등을 체험하고 있다. 현장에서는 메모리 설계와 NPU 활용이 핵심 키워드가 되고 있다.

## 1. 현장에서 무슨 일이 있었나
스마트폰 메모리 기업이 HBM(High Bandwidth Memory) 구조를 차용한 Low Latency Wide DRAM을 공개했다. 기존 DRAM 대비 1.5배 높은 전송 속도를 제공하고, 발열을 크게 낮췄다[출처: Low Latency Wide DRAM Adopts HBM’s Integrated Design To Enable On-Device AI In Smartphones]. 같은 시기에 삼성은 Exynos 2600 칩으로 MLPerf 벤치마크에서 온디바이스 AI 성능을 2배 끌어올렸다[출처: Samsung's Exynos 2600 doubles on-device AI performance in MLPerf benchmarks].

## 2. 왜 업계가 반응하는가
AI 연산을 클라우드가 아닌 기기 안에서 처리하면 응답 속도가 개선된다. 동시에 사용자 데이터가 외부로 흐르지 않아 프라이버시 위험이 감소한다. 배터리 소모는 연산량에 비례해 증가하지만, 전용 NPU와 고대역폭 메모리 덕분에 효율이 크게 올라갔다.

## 3. 기술적으로 보면
- **NPU(Neural Processing Unit)**: AI 모델 실행에 최적화된 연산 유닛. 일반 CPU보다 전력당 연산량이 높다.  
- **Low Latency Wide DRAM**: HBM 설계를 차용해 대역폭을 1.5배 확대하고 열을 감소시킨 메모리.  
- **LiteRT**: 구글이 제공하는 런타임 라이브러리. NPU와 직접 연결해 프레임 드롭 없이 실시간 영상·음성 처리를 지원한다[출처: Building real-world on-device AI with LiteRT and NPU - blog.google].  
- **Exynos 2600 AI 코어**: 두 개의 고성능 AI 코어가 병렬로 동작해 MLPerf 점수를 이전 세대 대비 2배 상승시켰다[출처: Samsung's Exynos 2600 doubles on-device AI performance in MLPerf benchmarks].

## 4. 실제 현장 적용 사례
Logitech은 Mobi Fold Travel Mouse에 온디바이스 AI를 탑재해, 사용자의 손동작을 실시간으로 인식해 커서 이동을 최적화했다[출처: Logitech Mobi Fold Travel Mouse With On-Device AI Folds Shut Like A Flip Phone]. Qualcomm은 Dragonwing MBM 실리콘에 AI 가속기를 내장해, 고화질 스트리밍과 동시에 AI 기반 배경 제거 기능을 제공한다[출처: Qualcomm's new Dragonwing MBM silicon combines interactive multimedia with top-tier connectivity & on-device AI]. 구글 안드로이드 앱에서도 설치형 AI 도구 세트를 열어, 사진 보정·음성 명령·실시간 번역을 오프라인에서도 수행한다[출처: Google's underrated AI app unlocked 3 amazing on-device AI tools on my Android phone].

## 5. 엔지니어가 봐야 할 포인트
- 메모리 대역폭과 NPU 활용 비율을 프로파일링한다.  
- 온디바이스 모델은 정밀도와 연산량 사이에서 트레이드오프가 필요하다.  
- 열 관리 설계가 배터리 수명에 직접적인 영향을 준다.  
- SDK(LiteRT 등)와 하드웨어 가속 기능을 조합해 프레임 레이트를 유지한다.

## 6. 정보관리기술사 연계

관련 기출: 없음

답안 핵심 키워드:
- 온디바이스 AI
- Low Latency Wide DRAM
- NPU

답안 작성 포인트:
- 정의
- 구조
- 활용
- 기대효과

## 7. 앞으로 볼 포인트
- 메모리와 NPU 통합 설계가 표준화될 가능성
- 저전력 AI 코어가 IoT Edge 디바이스에 확대 적용
- Generative AI 모델이 모바일 수준으로 경량화 진행

## 8. 3줄 요약
- HBM 기반 DRAM과 Exynos 2600 덕분에 스마트폰 AI 처리 속도가 크게 상승했다.  
- LiteRT와 NPU 조합이 실시간 영상·음성 서비스의 품질을 유지한다.  
- 향후 메모리·AI 코어 통합과 경량화 모델이 IoT 전반에 퍼질 전망이다.