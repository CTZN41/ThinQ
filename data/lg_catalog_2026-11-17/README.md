# LG 공식몰 3품목 제품·스펙 재수집

수집일: 2026-11-17 (각 레코드 UTC 수집 시각 기록)

| 품목 | 현재 모델 수 | 기존 DB에 없던 모델 | 상세 수집 성공 |
|---|---:|---:|---:|
| 광파오븐·전자레인지 | 36 | 20 | 36 |
| 세탁기 | 100 | 36 | 100 |
| 에어컨 | 292 | 237 | 292 |

총 428개 모델. 공식 목록 항목은 437건이며 모델명 기준으로 중복을 정리했다. 모든 품목의 페이지 합계와 공식 전체 목록 수가 일치함을 coverage.json에서 확인했다.

## 파일

- products_current.json: 제품별 공식 출처, 수집 시각, 원문 값, 설명, 상태, 가격·출시일 원문, 상세 응답 해시.
- products_summary.csv: 전체 모델 목록.
- specifications.csv: 제품별 전체 상세 스펙과 공식 용어 설명.
- new_to_previous_db.csv: 기존 553개 DB에 없던 293개 모델. ‘새로 출시됨’을 의미하지 않음.
- previous_models_not_listed.csv: 이전 3품목 중 현재 목록에 없는 6개 모델. 단종 확정 목록 아님.
- spec_changes.csv: 이전 상세 스펙과 다른 1621개 필드. 이름 변경·공식 페이지 구성 변경도 포함.
- validation.json, coverage.json: 수집·식별 검증 결과.
- collect.py: 재실행 코드. 공식몰의 공개 목록 API와 상세페이지를 사용하며 동시 요청은 3개로 제한.
- flight_helpers.py: 2차 프로젝트 full_collector_template.py에서 가져온 순수 Flight 파싱 함수.

## 기준과 한계

기존 기준은 9월 30일 스펙 수집값, 10월 7일 판매 상태 점검본의 로컬 정제 데이터다. 새 수집은 현재 공개 제품 목록 전체를 대상으로 했으며 실제 신제품만 골라 수집한 것이 아니다. 세트·색상·판매 모델의 구분은 원본 모델명과 상태를 유지했다.

제품의 기능 보유 여부와 코스별 설정 허용 조합은 다르다. 물온도·탈수 단계가 제품 스펙에 있어도 모든 코스에 적용된다고 해석하지 않는다. ThinQ 보유 여부와 API 제어 가능 여부도 다르며 제어 가능성을 검증하지 않았다. 세탁·건조·조리 성능의 재현 실험은 수행하지 않았다. 기존 DB와 데모 실행 프로필은 수정하지 않았다.

## 출처

- https://www.lge.co.kr/category/washing-machines
- https://www.lge.co.kr/category/microwaves-and-ovens
- https://www.lge.co.kr/category/air-conditioners
- 각 모델 source_url / final_url 참조.
