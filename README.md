# 전국 교통사고 다발지역 지도

도로교통공단 교통사고정보개방시스템의 다발지역 10종을 2021~2025 기준연도별로 보여 주는 지도입니다.

## 데이터 갱신 (1년에 한 번)
1. `pipeline/data/AccidentHazard_CodeList.xlsx`를 새로 받고, `pipeline/catalog.py`에 새 기준연도의 연도코드를 추가합니다.
2. `python -m pipeline.collect --years <새 연도>`
3. `python -m pipeline.build`
4. `site/data` 변경분을 커밋하고 main에 올리면 자동으로 공개됩니다.

## 시험
- `python -m pytest`
- `npm test`

자료: 도로교통공단 교통사고정보개방시스템
