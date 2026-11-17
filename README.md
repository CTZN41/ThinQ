# ThinQ 제어 데모

## LG 공식 상세 스펙 데이터 (2026-11-17)

세탁기·에어컨·오븐/전자레인지 **443개 항목**의 공식 상세 스펙은 [데이터 안내](data/lg_three_categories_2026-11-17/README.md)에서 확인할 수 있습니다. 점수·리뷰·추천 분석을 제외한 CSV와 JSON, 재수집·병합·추출 코드를 포함합니다. 앱의 제품 등록이나 제어 프로필에 자동 연결된 데이터는 아닙니다.

**최신 UI:** 변경할 값을 고른 뒤 **설정 적용** 버튼 하나로 전송합니다. 별도 미리보기 창은 없습니다. 변경한 항목만 순서대로 적용하며 항목별 결과를 표시합니다.

**최신 실행 상태:** 실제 계정 연결을 확인했고 LIVE 서버가 [8766 포트](http://127.0.0.1:8766)에서 실행 중입니다. 에어컨 2대의 목록·프로필·상태 조회에 성공했습니다. 실제 제어는 아직 수행하지 않았습니다. VS Code 기본 실행 작업도 LIVE/KR/8766으로 변경했습니다. [연결 검증 메모](docs/LIVE_CONNECTION_CHECK.md)

아래 모의 모드 개발 설명은 이전 단계 기록입니다. 모의 서버는 별도의 MOCK 작업 또는 `--mode mock`으로 실행할 수 있습니다.

현재 상태: **PHASE 1 완료 / PHASE 2·4 실기 코드 구현, 실제 검증 대기 / PHASE 3 웹 데모 및 PHASE 5 오프라인 검증 완료**

국가 코드는 **KR(대한민국, 전화 국가번호 +82)** 입니다. 현재 `.env`의 PAT로 실제 계정의 제품·상태 조회를 검증했습니다. 실제 제어 명령 전송은 아직 검증하지 않았습니다. 모의 모드는 별도로 유지하며 LG 서버에 요청하지 않습니다.

한국어 화면과 제품 카드 중심 디자인으로 재설계했습니다. [구현 및 검증 메모](docs/UI_KOREAN_REDESIGN.md)

## 로컬 웹 데모 실행

최초 설치 또는 새 PC에서는 다음을 실행합니다. 현재 PC에는 이미 `.venv`와 의존성을 설치했습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

VS Code **Ctrl+Shift+B** 기본 작업은 `ThinQ: LIVE / KR (8766)`입니다. [실제 연결 화면](http://127.0.0.1:8766)을 사용하세요. 모의 테스트는 별도 작업 `ThinQ: 웹 데모 (MOCK / KR)` 또는 아래 명령으로 실행합니다:

```powershell
.\.venv\Scripts\python.exe -m thinq_demo.web --mode mock
```

[웹 데모 열기](http://127.0.0.1:8765) → 제품 선택 → 값 입력 → 변경 미리보기 → 확인 후 모의 적용.

서버가 이미 실행 중이면 링크만 열면 됩니다. 기본 포트가 사용 중이면 기존 서버를 종료하거나 `--port 8766`처럼 다른 포트를 지정하세요. 웹 서버는 localhost에만 열립니다. 상태는 메모리에만 보관합니다.

## 실제 연결 설정 (새 환경에서)

현재 PC는 설정 완료 상태입니다. 기존 `.env`를 덮어쓰지 마세요. 새 환경에서만 다음 절차를 진행합니다.

1. `.env.example`을 `.env`로 복사합니다.
2. 로컬 편집기에서 `THINQ_PAT=`에 본인 토큰을 설정합니다. `THINQ_COUNTRY=KR`은 그대로 둡니다.
3. 모의 서버를 종료하고 `.\.venv\Scripts\python.exe -m thinq_demo.web --mode live`를 실행합니다.
4. 실제 제품 목록·프로필·상태 조회부터 확인합니다. 명령은 미리보기 확인 버튼을 눌러야 전송됩니다.

인증정보는 브라우저에서 입력/조회하지 않습니다. `.env`는 Git 제외 대상입니다. client ID는 최초 실기 실행 때 `private/client_id.txt`에 생성되어 재사용됩니다. PAT가 비어 있으면 실기 모드는 시작되지 않습니다.

목록은 API가 반환한 모든 종류를 표시하고, 공식 SDK의 30개 제품 종류를 연결 대상으로 매핑합니다. **30개 종류에 대한 실기 성공을 의미하지 않습니다.** 단일 매개변수 setter와 명시적으로 구성한 오븐 조합 명령을 지원하며, 해석되지 않는 다중 매개변수 명령·미지원 속성은 조회만 제공합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

35개 테스트 통과. 선택적 브라우저 검증은 `requirements-dev.txt` 설치 후 MOCK 서버를 실행한 상태에서 `tests/browser_smoke.py`를 실행합니다. 설치된 Microsoft Edge를 사용합니다.

## 실행

Python 3.11 이상 필요. PHASE 1은 표준 라이브러리만 사용하므로 패키지 설치가 필요 없습니다.

이전 터미널 시연은 VS Code 작업 `ThinQ: PHASE 1 모의 시연` 또는 아래 명령으로 계속 사용할 수 있습니다.

터미널에서 직접 실행할 수도 있습니다.

```powershell
cd C:\Users\aicam\Desktop\ThinQ
python -m thinq_demo demo
```

## 명령

```powershell
# 모의 제품 전체 목록
python -m thinq_demo list

# 에어컨의 프로필 해석 결과·현재 값
python -m thinq_demo inspect mock-ac

# 상/하단 구분이 있는 오븐 원본 합성 프로필
python -m thinq_demo inspect mock-oven --raw

# 목표 온도 24.5의 검증/미리보기. 상태 변경은 하지 않음
python -m thinq_demo prepare mock-ac /property/temperature/targetTemperature 24.5

# 아래 요청은 오류 코드 2로 거부됨
python -m thinq_demo prepare mock-ac /property/temperature/targetTemperature 99

# 테스트
python -m unittest discover -s tests -v
```

`prepare`의 값은 JSON 자료형입니다. 숫자·boolean·문자열의 형식을 구분합니다. 전체 시연의 정상/차단 예시는 `demo`로 확인하는 것이 가장 간편합니다.

## 포함한 모의 제품

| ID | 설명 |
|---|---|
| mock-ac | 에어컨: 선택값·소수 간격 온도 |
| mock-air | 공기청정기: 제어 항목과 읽기 전용 센서 |
| mock-washer | 세탁기: 명령과 읽기 전용 운전 상태 |
| mock-fridge | 냉장고: 숫자와 boolean |
| mock-oven | 오븐: 상단/하단·배열·온도 단위 |
| mock-offline | 연결 끊김 차단 사례 |
| mock-unknown | 미지원 속성 형식 차단 사례 |

**모든 데이터는 합성 예제입니다. 특정 LG 모델의 기능, 허용 온도, 실제 응답 형식을 증명하지 않습니다.** 오프라인 제품에 쓰기 속성이 있더라도 현재 명령을 실행할 수 있다는 뜻은 아닙니다.

## 문서

- [전체 PHASE 계획](PLAN.md)
- [PHASE 1 상세 구현 메모](docs/PHASE_1_MEMO.md)
- [PHASE 2 — 실제 연결 코드](docs/PHASE_2_MEMO.md)
- [PHASE 3 — 웹 화면](docs/PHASE_3_MEMO.md)
- [PHASE 4 — 제어 요청 및 확인](docs/PHASE_4_MEMO.md)
- [PHASE 5 — 검증·남은 제약](docs/PHASE_5_MEMO.md)

기존 작업 폴더의 중단 당시 파일은 삭제하지 않았습니다. 현재 실행/수정 기준은 이 바탕화면 폴더입니다.
