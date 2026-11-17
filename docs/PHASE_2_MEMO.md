# PHASE 2 — 실제 연결 코드

2026-11-17 / 상태: 코드 구현 및 오프라인 검증. 실제 계정 조회는 PAT 미입력으로 미검증.

## 결정

국가 코드는 KR이다. +82는 전화번호 국가번호라서 API에는 전달하지 않는다. 설정 변환기는 KR, +82, 82, 대한민국을 KR로 정규화한다. 기본값 역시 KR이다.

공식 `thinqconnect==1.0.14`, `aiohttp==3.14.5`를 프로젝트 `.venv`에 설치했다. 직접 의존성은 `requirements.txt`, 전체 설치 버전은 `requirements-lock.txt`에 고정했다. PHASE 1의 독립 CLI는 표준 라이브러리만으로 실행 가능하다.

## 설정과 인증

`config.py`에서 실기 모드에 한해 `.env` 및 환경변수를 읽는다. 환경변수가 파일보다 우선한다. 모의 모드에서는 이 함수를 호출하지 않아 PAT를 전혀 읽지 않는다. `.env.example`은 PAT 빈칸과 KR만 포함하며 실제 `.env`는 만들지 않았다.

실기 모드에는 PAT·country·client ID가 필요하다. client ID는 최초 실기 시작 시 UUID로 생성하고 `private/client_id.txt`에서 재사용한다. 빈 PAT이면 네트워크 연결 전에 종료한다. `.env`와 private 폴더는 Git 제외다.

## API 연결

`live.py`의 LiveGateway가 aiohttp 세션과 공식 ThinQApi를 수명주기 동안 유지한다. 목록 조회는 `async_get_device_list`, 상세는 `async_get_device_profile`와 `async_get_device_status`를 사용한다. 상세 조회는 선택한 제품에 대해서만 이루어지므로 한 제품의 실패가 전체 목록을 없애지 않는다.

목록에는 지원하지 않는 종류도 남긴다. raw profile/state를 함께 제공한다. online은 응답으로 확정하지 못한 경우 None이며 연결됐다고 임의로 표시하지 않는다.

## 검증 및 한계

- SDK 1.0.14 실제 설치·import 성공, 생성자 시그니처 확인.
- 국가 코드 정규화와 PAT 누락 시 시작 차단 테스트 통과.
- PAT는 입력하지 않았으며 실제 서버 요청은 하지 않았다.
- 인증 성공, 실제 모델 응답, 호출 제한 수치, 국가별/계정별 지원은 미검증이다.
- 사용자별 서비스 운영/OAuth 전환/상용 이용 정책은 이 로컬 데모 범위 밖이다.

출처: [공식 SDK 사용 안내](https://github.com/thinq-connect/pythinqconnect#installation-and-usage), [API 구현](https://github.com/thinq-connect/pythinqconnect/blob/main/thinqconnect/thinq_api.py).
