# PHASE 3 — 웹 화면 및 공통 제어 구조

2026-11-17 / 상태: 모의 웹 데모 구현 및 브라우저 확인 완료.

## 화면 흐름

제품 목록 → 제품 선택 → 제어값 입력 → 명령 미리보기 → 명시적 확인 → 결과 표시. 원본 프로필, 프로필 해석 결과, 현재 상태를 접어서 볼 수 있다. MOCK/LIVE와 KR을 상단에 표시한다. PAT 입력창은 제공하지 않는다.

웹 서버는 aiohttp, 화면은 정적 HTML/CSS/JavaScript이다. `127.0.0.1:8765`에만 바인딩하며 외부 웹 호스팅은 하지 않았다. CSS는 390px 모바일 폭과 1440px 데스크톱 폭에서 확인했다.

## 공통 처리

모의 모드: PHASE 1 Capability를 폼으로 변환한다. enum/boolean은 선택상자, range는 min/max/step 입력이다.

실기 모드: `sdk_adapter.py`가 공식 SDK가 export하는 기기 클래스와 DeviceType 상수를 매핑한다. 1.0.14의 30개 종류가 매핑된다. 각 제품과 하위 구역의 writable_properties를 읽고 `get_property_set_fn`으로 setter를 찾는다. 단일 매개변수 함수는 프로필 제약과 연결해 폼을 구성한다.

두 개 이상의 매개변수가 있는 함수는 의미를 추측하지 않는다. 예외적으로 오븐의 `set_cook_mode_with_temperature_c/f`는 모드·온도·START 지원을 함께 검증해 제공한다. 임의 메서드명이나 raw JSON을 입력해 서버에서 실행하는 기능은 없다.

## 구현 파일

- `web.py`: 웹 경로·로컬 요청 보호·서버 시작
- `engine.py`: 모드별 조회와 명령 준비·확인
- `sdk_adapter.py`: 공식 SDK 기반 제어 기능과 요청 구성
- `static/index.html`, `app.js`, `style.css`: 화면

## 브라우저 검증

기본 브라우저 자동화 연결을 사용할 수 없어 Playwright+설치된 Microsoft Edge의 headless 모드로 검증했다. PAT/실기 서버가 아닌 MOCK 서버에서만 실행하도록 테스트를 제한했다.

- 7개 제품 표시
- 에어컨 온도 24.5 미리보기와 확인 후 모의 반영
- 오프라인 제품 버튼 비활성
- 미지원 형식 제품 조회 안내
- 390px 화면 가로 넘침 없음
- JavaScript 오류 없음

스크린샷: `docs/screenshots/desktop.png`, `docs/screenshots/mobile.png`.

현재 화면의 실제 제어 라벨 일부는 SDK 속성 이름을 그대로 사용한다. 모든 기능의 한국어 의미/설명을 검증해 번역하는 작업은 후속 개선 대상이다.
