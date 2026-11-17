# LG 제품 DB 합본 · 2026-11-17

## 먼저 열 파일

- **LG_제품DB_합본.csv**: 엑셀에서 열 수 있는 UTF-8 BOM 합본. 최신 수집값을 앞쪽에, 기존 61개 필드를 `기존_` 접두사로 뒤쪽에 보존했다.
- **products_merged.json**: 프로그램용 완전한 합본. 각 항목의 `current`는 최신 수집 원문, `legacy`는 기존 DB 원문이다. CSV에서 수식으로 오인될 수 있는 문자열은 작은따옴표로 보호하고 JSON에는 그대로 보존했다.
- **code/crawl.py**: 다시 수집하는 실행 코드. 별도 pip 설치나 API 키 없이 Python 3.10 이상 표준 라이브러리로 실행한다.
- **code/merge.py**: 기존 DB와 수집 결과를 재병합하는 코드.

## 합본 범위와 검증 결과

| 항목 | 개수 |
|---|---:|
| 기존 DB | 553개 모델 |
| 세탁기·오븐·에어컨 수집 결과 | 437개 판매 항목 / 428개 모델 |
| 기존 모델과 연결 | 135개 모델 |
| 기존 DB에 없는 모델 | 293개 모델 |
| 최종 합본 | **855개 판매·기존 항목 / 846개 모델** |

855행은 기존 553개 + 새로운 모델 293개 + 같은 모델명의 추가 판매 식별자 9개로 구성된다. 현재 목록 미확인 6개와 이번 수집 범위 밖 412개도 삭제하지 않았다. 기존 DB에 없는 모델은 신제품 출시를 의미하지 않는다.

현재 수집 437개 항목의 공식 상태 코드는 ACTIVE 169개, READY_FOR_SALE 47개, SOLD_OUT 16개, NOT_FOR_SALE 205개다. 합본 전체를 현재 판매 중인 제품 목록으로 사용하면 안 된다. 필요하면 `현재 판매상태 = ACTIVE`로 필터링한다.

기존 DB의 스펙·가격·리뷰는 2026-09-30 기준이며 판매 상태·이미지는 10-07 재확인 자료다. 새 수집일은 각 current.collected_at에 UTC로 기록되어 있다. 기존 리뷰·분석 점수를 새로 검증하거나 재계산하지 않았다. 기존 가격을 최신 가격의 빈칸에 대신 넣지 않았다.

## 병합 규칙

1. 최신 항목의 고유 키는 `카테고리 + 모델명 + 판매 식별자`다. 같은 모델명이라도 판매 식별자가 다르면 보존한다.
2. 같은 키의 중복 수집은 수집일이 더 늦은 원문을 선택한다.
3. 기존 DB에는 판매 식별자가 없어서 `카테고리 + 모델명`으로 연결한다. 기존 원문을 판매 변형까지 검증된 자료로 간주하지 않는다.
4. 현재 목록에서 발견되지 않은 기존 모델은 단종으로 표시하지 않는다.
5. 스펙과 공식 Product 모델 식별이 검증되지 않은 수집 결과는 병합을 중단한다.
6. 최종 파일의 current를 최신 정보로 사용하고, legacy는 과거 비교·리뷰·원문 확인에 사용한다. ThinQ API 제어 가능 여부는 제품 스펙 크롤링으로 검증되지 않는다.

## 이번 합본 재생성

이 폴더에서 PowerShell로 실행한다.

```powershell
python code/merge.py --variants inputs/same_model_variants.json
```

원래 수집본 428개와 판매 식별자 중복 감사에서 재수집한 15개 원문을 함께 읽는다. 중복 키 6개를 최신 원문으로 갱신하고 빠졌던 9개 항목을 추가한다. inputs의 기존 파일은 수정하지 않는다.

## 새 날짜에 다시 크롤링하고 합치기

```powershell
python code/crawl.py --output runs/new-snapshot
python code/merge.py --current runs/new-snapshot/products_current.json --output runs/new-merged
```

새 크롤러는 처음부터 판매 식별자를 구분하므로 과거 `--variants` 파일을 섞지 않는다. 중단된 동일 실행을 이어갈 때만 `--resume`을 사용한다. 다른 날짜의 새 수집은 새 output 폴더를 사용한다. 출력에 오류가 있으면 오류를 먼저 해결한 후 병합한다.

크롤러는 공식 카테고리 페이지에서 요청 조건을 찾고 공개 목록 API의 모든 페이지를 읽은 후 각 상세 페이지의 구조화 데이터와 스펙을 수집한다. 동시 상세 요청은 3개이며 대기·재시도를 포함한다. 사이트 구조나 공개 API가 변경되면 파서 수정이 필요할 수 있다.

## 출처

- [기존 LG전자 제품 DB](https://docs.google.com/spreadsheets/d/1L4fsrVBTLIFwIbSg87XlaIvk1CEH73kN/edit)
- [LG 세탁기](https://www.lge.co.kr/category/washing-machines)
- [LG 광파오븐·전자레인지](https://www.lge.co.kr/category/microwaves-and-ovens)
- [LG 에어컨](https://www.lge.co.kr/category/air-conditioners)

개별 상세 페이지 URL·수집일·HTML 해시는 JSON에 보존했다. validation.json에 병합 검증 및 입력 SHA256이 있고, SHA256.json에 배포 파일의 해시가 있다.
