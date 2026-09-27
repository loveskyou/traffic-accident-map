# 전국 교통사고 다발지역 지도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 도로교통공단 다발지역 10종을 2021~2025 기준연도별로 보여 주는 무료 공개 웹 지도를 만든다.

**Architecture:** 파이썬 수집기가 교통사고정보개방시스템 REST API에서 원본을 받아 `raw/`에 저장하고, 가공기가 `site/data/`에 정적 JSON을 만든다. 빌드 과정 없는 HTML·ES 모듈 웹사이트가 이 JSON과 카카오맵으로 지도를 그리고, GitHub Pages가 `site/`를 공개한다.

**Tech Stack:** Python 3.14(표준 라이브러리, openpyxl, pytest), Node 24(`node --test`로 순수 JS 시험), HTML/CSS/ES 모듈, 카카오맵 JavaScript SDK(services, clusterer), GitHub Actions + Pages.

**Spec:** `docs/superpowers/specs/2026-09-27-traffic-accident-map-design.md`

## Global Constraints

- 프로젝트 루트: `C:\Users\ahn\Desktop\project\traffic accident` (폴더 이름에 공백이 있으므로 명령에서 항상 따옴표로 감싼다).
- 기준연도는 2021, 2022, 2023, 2024, 2025 다섯 개다.
- API 주소: `https://opendata.koroad.or.kr/data/rest/frequentzone/<경로>`, 요청 변수 `authKey, searchYearCd, siDo, guGun, type=json, numOfRows, pageNo`.
- `searchYearCd`는 연도가 아니라 설계 문서 2장 표의 7자리 연도코드다.
- 인증키는 `config.local.json`의 `koroad_auth_key`에만 둔다. 오류 메시지, 로그, 보고서에 인증키나 인증키가 들어간 주소를 절대 출력하지 않는다.
- 파이썬 의존성은 openpyxl, pytest만 쓴다. 웹사이트 외부 스크립트는 카카오맵 SDK만 쓴다.
- 화면 문구는 한국어다. 출처 문구는 "자료: 도로교통공단 교통사고정보개방시스템", 안내 문구는 "과거 통계이며 현재 도로 상황과 다를 수 있습니다."다.
- 연속 다발지역 계산은 1년 단위 유형(lg, child, bicycle, schoolzone)에만 한다.
- 한국 좌표 범위는 위도 33.0~38.7, 경도 124.5~132.0이다.
- 구역 모양은 카카오맵 확대 단계 5 이하에서만 그린다.

## Review Focus

- 결과가 1건일 때 `items.item`이 목록이 아니라 객체로 오는 응답 → 1건짜리 목록으로 처리해야 한다. (Task 3 `test_single_item_object_becomes_list`)
- 한 시군구 결과가 한 페이지(100건)를 넘는 경우 → 모든 페이지를 받아야 한다. (Task 3 `test_fetch_all_follows_pages`)
- 강원·전북(시도 코드만 바뀜), 전남광주(시도와 시군구 코드가 모두 바뀜) → 결과가 있는 [시도, 시군구] 짝을 찾아 쓰고, 어느 짝으로 받았는지 기록해야 한다. (Task 2 `test_merged_region_uses_old_gugun_code_by_name`, Task 4 `test_collect_one_old_pair_changes_gugun_too`)
- 지점명에 `<`, `&`, `"` 같은 문자가 있는 경우 → 화면이 깨지거나 스크립트가 실행되지 않아야 한다. (Task 8 `escapeHtml`, `detailHtml escapes`)
- 유형 버튼을 빠르게 연달아 누르는 경우 → 늦게 끝난 이전 요청이 최신 화면을 덮어쓰지 않아야 한다. (Task 10 `app.js`의 `renderSeq`, Task 11 브라우저 확인 6번)

---

### Task 0: 사용자 준비물

사용자가 직접 한다. AI는 화면별로 안내만 하고, 키를 대화창으로 받지 않는다.

- [ ] **Step 1: 교통사고정보개방시스템 인증키**

https://opendata.koroad.or.kr 에서 회원가입 → 로그인 → "API 인증키 발급" 메뉴에서 발급. 발급된 키를 Task 1에서 만드는 `config.local.json`에 사용자가 직접 붙여 넣는다.

- [ ] **Step 2: 카카오 개발자 앱**

https://developers.kakao.com → 내 애플리케이션 → 애플리케이션 추가. 앱 설정 → 플랫폼 → Web 플랫폼 등록 → 사이트 도메인에 `http://localhost:8000` 추가. 앱 키 중 **JavaScript 키**를 Task 9에서 `site/js/config.js`에 넣는다. 카카오맵 사용 설정(제품 설정 → 카카오맵)이 꺼져 있으면 켠다.

- [ ] **Step 3: GitHub 계정**

https://github.com 에서 무료 계정을 만든다. Task 12에서 쓴다.

---

### Task 1: 프로젝트 뼈대와 유형 목록

**Files:**
- Create: `pyproject.toml`, `requirements-dev.txt`, `config.example.json`, `package.json`
- Create: `pipeline/__init__.py`, `pipeline/catalog.py`
- Create: `tests/__init__.py`, `tests/test_catalog.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `catalog.BASE_URL: str`, `catalog.YEARS: list[int]`, `catalog.TYPES: list[dict]`, `catalog.TYPES_BY_ID: dict[str, dict]`, `catalog.endpoint(type_id) -> str`, `catalog.year_code(type_id, year) -> str`, `catalog.period_label(type_id, year) -> str`, `catalog.public_types() -> list[dict]` (필드 `id, name, short, color, period, radius_m, criteria, years`).

- [ ] **Step 1: 설정 파일 만들기**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`requirements-dev.txt`:
```
pytest
openpyxl
```

`config.example.json`:
```json
{"koroad_auth_key": "여기에_교통사고정보개방시스템_인증키"}
```

`package.json`:
```json
{
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test \"tests/js/*.test.js\"" }
}
```

`.gitignore` 끝에 추가:
```
# 브라우저 자동화 기록
.playwright-mcp/
```

`pipeline/__init__.py`, `tests/__init__.py`: 빈 파일.

Run: `python -m pip install -r requirements-dev.txt`
Expected: pytest, openpyxl 설치 완료(이미 있으면 "already satisfied").

- [ ] **Step 2: 실패하는 시험 쓰기**

`tests/test_catalog.py`:
```python
from pipeline import catalog


def test_ten_types_with_unique_ids():
    ids = [t["id"] for t in catalog.TYPES]
    assert len(ids) == 10
    assert len(set(ids)) == 10


def test_every_type_has_code_for_every_year():
    for t in catalog.TYPES:
        assert sorted(t["year_codes"]) == catalog.YEARS
        for code in t["year_codes"].values():
            assert len(code) == 7 and code.isdigit()


def test_endpoint_and_year_code():
    assert catalog.endpoint("schoolzone") == "https://opendata.koroad.or.kr/data/rest/frequentzone/schoolzone/child"
    assert catalog.endpoint("pedestrian").endswith("/pedstrians")
    assert catalog.year_code("pedestrian", 2025) == "2026122"
    assert catalog.year_code("lg", 2021) == "2022046"


def test_period_label():
    assert catalog.period_label("lg", 2025) == "2025년 1년간"
    assert catalog.period_label("pedestrian", 2025) == "2023~2025년 3년간"
    assert catalog.period_label("freezing", 2025) == "2021~2025년 겨울철(11~3월)"


def test_annual_types():
    annual = {t["id"] for t in catalog.TYPES if t["period"] == "annual"}
    assert annual == {"lg", "child", "bicycle", "schoolzone"}


def test_public_types_hides_internal_fields():
    pub = catalog.public_types()
    assert len(pub) == 10
    assert set(pub[0]) == {"id", "name", "short", "color", "period", "radius_m", "criteria", "years"}
    assert pub[0]["years"] == catalog.YEARS
```

- [ ] **Step 3: 시험이 실패하는지 확인**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: FAIL (`cannot import name 'catalog'` 또는 `module 'pipeline.catalog' has no attribute`).

- [ ] **Step 4: 구현**

`pipeline/catalog.py`:
```python
"""도로교통공단 교통사고정보개방시스템 다발지역 유형 10종의 고정 정보."""

BASE_URL = "https://opendata.koroad.or.kr/data/rest/frequentzone/"
YEARS = [2021, 2022, 2023, 2024, 2025]

TYPES = [
    {
        "id": "lg", "name": "일반 (시군구별 상위 3곳)", "short": "일반", "path": "lg",
        "period": "annual", "radius_m": 150, "color": "#E4572E",
        "criteria": "1년간 발생한 전체 교통사고 가운데 반경 150m 안에서 3건 이상 발생한 지점 중 시군구별 상위 3곳",
        "year_codes": {2021: "2022046", 2022: "2023026", 2023: "2024056", 2024: "2025119", 2025: "2026134"},
    },
    {
        "id": "pedestrian", "name": "보행자", "short": "보행자", "path": "pedstrians",
        "period": "rolling3", "radius_m": 100, "color": "#6A4C93",
        "criteria": "최근 3년간 보행자 사망·중상 사고가 반경 100m 안에서 7건 이상 발생한 곳",
        "year_codes": {2021: "2022040", 2022: "2023060", 2023: "2024051", 2024: "2025083", 2025: "2026122"},
    },
    {
        "id": "child", "name": "보행어린이", "short": "보행어린이", "path": "child",
        "period": "annual", "radius_m": 200, "color": "#F4A259",
        "criteria": "1년간 12세 이하 어린이 보행자 사고가 반경 200m 안에서 3건 이상(사망사고 포함 시 2건 이상) 발생한 곳",
        "year_codes": {2021: "2022084", 2022: "2023011", 2023: "2024042", 2024: "2025108", 2025: "2026124"},
    },
    {
        "id": "oldman", "name": "보행노인", "short": "보행노인", "path": "oldman",
        "period": "rolling3", "radius_m": 100, "color": "#2A9D8F",
        "criteria": "최근 3년간 65세 이상 보행노인 사망·중상 사고가 반경 100m 안에서 5건 이상 발생한 곳",
        "year_codes": {2021: "2022042", 2022: "2023057", 2023: "2024044", 2024: "2025076", 2025: "2026121"},
    },
    {
        "id": "bicycle", "name": "자전거", "short": "자전거", "path": "bicycle",
        "period": "annual", "radius_m": 100, "color": "#1D70B8",
        "criteria": "1년간 자전거가 관련된 사고가 반경 100m 안에서 4건 이상(사망사고 포함 시 3건 이상) 발생한 곳. 2021년 자료는 반경 200m 기준",
        "year_codes": {2021: "2022083", 2022: "2023016", 2023: "2024046", 2024: "2025081", 2025: "2026114"},
    },
    {
        "id": "motorcycle", "name": "이륜차", "short": "이륜차", "path": "motorcycle",
        "period": "rolling3", "radius_m": 100, "color": "#8C564B",
        "criteria": "최근 3년간 이륜차(원동기장치자전거·사륜ATV 포함) 사망·중상 사고가 반경 100m 안에서 4건 이상 발생한 곳",
        "year_codes": {2021: "2022032", 2022: "2023017", 2023: "2024047", 2024: "2025091", 2025: "2026113"},
    },
    {
        "id": "schoolzone", "name": "어린이보호구역 내 어린이", "short": "스쿨존", "path": "schoolzone/child",
        "period": "annual", "radius_m": 300, "color": "#E9C46A",
        "criteria": "1년간 어린이보호구역에서 12세 이하 어린이 사고가 반경 300m 안에서 2건 이상 발생했거나 사망사고가 난 곳",
        "year_codes": {2021: "2022038", 2022: "2023010", 2023: "2024041", 2024: "2025066", 2025: "2026076"},
    },
    {
        "id": "drunk", "name": "음주운전", "short": "음주운전", "path": "drunk",
        "period": "rolling3", "radius_m": 100, "color": "#C1121F",
        "criteria": "최근 3년간 음주운전 사망·중상 사고가 반경 100m 안에서 3건 이상 발생한 곳",
        "year_codes": {2021: "2022051", 2022: "2023018", 2023: "2024049", 2024: "2025085", 2025: "2026116"},
    },
    {
        "id": "truck", "name": "화물차", "short": "화물차", "path": "truck",
        "period": "rolling3", "radius_m": 100, "color": "#4A4E69",
        "criteria": "최근 3년간 화물차 사망·중상 사고가 반경 100m 안에서 4건 이상 발생한 곳",
        "year_codes": {2021: "2022048", 2022: "2023054", 2023: "2024048", 2024: "2025089", 2025: "2026135"},
    },
    {
        "id": "freezing", "name": "결빙", "short": "결빙", "path": "freezing",
        "period": "rolling5", "radius_m": 200, "color": "#4CC9F0",
        "criteria": "최근 5년간 11~3월 서리·결빙 노면 사고가 반경 200m 안에서 3건 이상(사망사고 포함 시 2건 이상) 발생한 곳",
        "year_codes": {2021: "2022082", 2022: "2023071", 2023: "2024055", 2024: "2025113", 2025: "2026125"},
    },
]

TYPES_BY_ID = {t["id"]: t for t in TYPES}
PUBLIC_FIELDS = ("id", "name", "short", "color", "period", "radius_m", "criteria")


def endpoint(type_id):
    return BASE_URL + TYPES_BY_ID[type_id]["path"]


def year_code(type_id, year):
    return TYPES_BY_ID[type_id]["year_codes"][year]


def period_label(type_id, year):
    period = TYPES_BY_ID[type_id]["period"]
    if period == "annual":
        return f"{year}년 1년간"
    if period == "rolling3":
        return f"{year - 2}~{year}년 3년간"
    return f"{year - 4}~{year}년 겨울철(11~3월)"


def public_types():
    return [{**{k: t[k] for k in PUBLIC_FIELDS}, "years": list(YEARS)} for t in TYPES]
```

- [ ] **Step 5: 시험 통과 확인**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: 6 passed.

- [ ] **Step 6: 커밋**

```bash
git add pyproject.toml requirements-dev.txt config.example.json package.json .gitignore pipeline tests
git commit -m "feat: 유형 10종 목록과 프로젝트 뼈대"
```

---

### Task 2: 지역 목록

**Files:**
- Create: `pipeline/data/AccidentHazard_CodeList.xlsx` (다운로드)
- Create: `pipeline/regions.py`
- Create: `tests/test_regions.py`
- Create(생성물): `site/data/regions.json`

**Interfaces:**
- Consumes: 없음
- Produces: `regions.read_rows(path) -> (sido_rows: list[tuple[str,int]], gugun_rows: list[tuple[str,str,int]])`, `regions.build_regions(sido_rows, gugun_rows) -> list[dict]` (키 `sido, gugun, codes: list[list[int]], geo: str`. `codes`는 [시도 코드, 시군구 코드] 후보 목록이고 새 코드 짝이 맨 앞), `regions.region_key(region) -> str` (첫 후보로 만든 "51-130" 형식), `regions.site_regions(regions) -> list[{"sido": str, "gugun": [{"name": str, "geo": str}]}]`, `regions.load_regions(path=CODE_FILE) -> list[dict]`.

- [ ] **Step 1: 코드 파일 받기**

```bash
mkdir -p pipeline/data
curl -s -A "Mozilla/5.0" -o pipeline/data/AccidentHazard_CodeList.xlsx "https://opendata.koroad.or.kr/api/down/accidenthazard_codelist_down.jsp"
python -c "import zipfile;zipfile.ZipFile('pipeline/data/AccidentHazard_CodeList.xlsx');print('ok')"
```
Expected: `ok`

- [ ] **Step 2: 실패하는 시험 쓰기**

`tests/test_regions.py`:
```python
import pytest

from pipeline import regions

SIDO = [
    ("서울특별시", 11), ("전남광주통합특별시", 12), ("광주광역시(구)", 29), ("강원도(구)", 42),
    ("강원특별자치도", 51), ("전라남도(구)", 46), ("전라북도(구)", 45), ("전북특별자치도", 52),
]
GUGUN = [
    ("서울특별시", "강남구", 680),
    ("강원특별자치도", "원주시", 130),
    ("전북특별자치도", "전주시완산구", 111),
    ("전남광주통합특별시", "광산구", 330),
    ("전남광주통합특별시", "광양시", 190),
    ("전남광주통합특별시", "목포시", 110),
    ("광주광역시(구)", "광산구", 200),
    ("전라남도(구)", "광양시", 230),
    ("전라남도(구)", "목포시", 110),
]


def by_name(result):
    return {(r["sido"], r["gugun"]): r for r in result}


def test_old_groups_are_skipped():
    result = regions.build_regions(SIDO, GUGUN)
    assert len(result) == 6
    assert all(not r["sido"].endswith("(구)") for r in result)


def test_code_candidates():
    r = by_name(regions.build_regions(SIDO, GUGUN))
    assert r[("서울특별시", "강남구")]["codes"] == [[11, 680]]
    assert r[("강원특별자치도", "원주시")]["codes"] == [[51, 130], [42, 130]]
    assert r[("전북특별자치도", "전주시완산구")]["codes"] == [[52, 111], [45, 111]]


def test_merged_region_uses_old_gugun_code_by_name():
    r = by_name(regions.build_regions(SIDO, GUGUN))
    assert r[("전남광주통합특별시", "광산구")]["codes"] == [[12, 330], [29, 200]]
    assert r[("전남광주통합특별시", "광양시")]["codes"] == [[12, 190], [46, 230]]
    assert r[("전남광주통합특별시", "목포시")]["codes"] == [[12, 110], [46, 110]]


def test_geo_address_for_kakao():
    r = by_name(regions.build_regions(SIDO, GUGUN))
    assert r[("서울특별시", "강남구")]["geo"] == "서울특별시 강남구"
    assert r[("전북특별자치도", "전주시완산구")]["geo"] == "전북특별자치도 전주시 완산구"
    assert r[("전남광주통합특별시", "광산구")]["geo"] == "광주광역시 광산구"
    assert r[("전남광주통합특별시", "목포시")]["geo"] == "전라남도 목포시"


def test_region_key():
    r = by_name(regions.build_regions(SIDO, GUGUN))
    assert regions.region_key(r[("강원특별자치도", "원주시")]) == "51-130"


def test_site_regions_groups_in_order():
    out = regions.site_regions(regions.build_regions(SIDO, GUGUN))
    assert [g["sido"] for g in out] == ["서울특별시", "강원특별자치도", "전북특별자치도", "전남광주통합특별시"]
    assert out[3]["gugun"] == [
        {"name": "광산구", "geo": "광주광역시 광산구"},
        {"name": "광양시", "geo": "전라남도 광양시"},
        {"name": "목포시", "geo": "전라남도 목포시"},
    ]


@pytest.mark.skipif(not regions.CODE_FILE.exists(), reason="코드 파일 없음")
def test_real_code_file():
    result = regions.load_regions()
    assert len(result) == 270
    assert all(100 <= g <= 999 for r in result for _, g in r["codes"])
    named = by_name(result)
    assert named[("전남광주통합특별시", "광산구")]["codes"] == [[12, 330], [29, 200]]
    assert all(len(r["codes"]) == 2 for r in result if r["sido"] == "전남광주통합특별시")
```

- [ ] **Step 3: 실패 확인**

Run: `python -m pytest tests/test_regions.py -v`
Expected: FAIL (`cannot import name 'regions'`).

- [ ] **Step 4: 구현**

`pipeline/regions.py`:
```python
"""교통사고정보개방시스템 요청변수 코드 파일에서 시군구 목록을 만든다."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE_FILE = ROOT / "pipeline" / "data" / "AccidentHazard_CodeList.xlsx"
SITE_REGIONS = ROOT / "site" / "data" / "regions.json"

OLD_SIDO_NAME = {"강원특별자치도": "강원도(구)", "전북특별자치도": "전라북도(구)"}
MERGED = "전남광주통합특별시"
GWANGJU_OLD = "광주광역시(구)"
JEONNAM_OLD = "전라남도(구)"


def _clean(value):
    return value.replace("\n", "").strip() if isinstance(value, str) else value


def read_rows(path=CODE_FILE):
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = wb.worksheets
    sido_rows = [
        (_clean(r[0]), int(r[1]))
        for r in sheets[1].iter_rows(min_row=2, values_only=True)
        if r[0] and isinstance(r[1], (int, float))
    ]
    gugun_rows, group = [], None
    for r in sheets[2].iter_rows(min_row=2, values_only=True):
        if r[0]:
            group = _clean(r[0])
        if len(r) < 3 or r[1] is None or not isinstance(r[2], (int, float)):
            continue
        gugun_rows.append((group, _clean(r[1]), int(r[2])))
    wb.close()
    return sido_rows, gugun_rows


def _space_city_gu(name):
    match = re.fullmatch(r"(.+시)(.+구)", name)
    return f"{match.group(1)} {match.group(2)}" if match else name


def build_regions(sido_rows, gugun_rows):
    """시군구마다 [시도 코드, 시군구 코드] 후보를 만든다. 새 코드 짝이 맨 앞이다.

    강원·전북은 시도 코드만 바뀌었다. 전남광주통합특별시는 시군구 코드도 바뀌어서,
    예전 묶음(광주광역시(구), 전라남도(구))에서 같은 이름을 찾아 예전 코드 짝을 만든다.
    """
    code = dict(sido_rows)
    old_by_name = {
        old: {n: g for grp, n, g in gugun_rows if grp == old} for old in (GWANGJU_OLD, JEONNAM_OLD)
    }
    result = []
    for grp, name, gcode in gugun_rows:
        if grp.endswith("(구)"):
            continue
        candidates = [[code[grp], gcode]]
        geo_sido = grp
        if grp in OLD_SIDO_NAME:
            candidates.append([code[OLD_SIDO_NAME[grp]], gcode])
        if grp == MERGED:
            old = GWANGJU_OLD if name in old_by_name[GWANGJU_OLD] else JEONNAM_OLD
            candidates.append([code[old], old_by_name[old][name]])
            geo_sido = "광주광역시" if old == GWANGJU_OLD else "전라남도"
        result.append({"sido": grp, "gugun": name, "codes": candidates, "geo": f"{geo_sido} {_space_city_gu(name)}"})
    return result


def region_key(region):
    sido, gugun = region["codes"][0]
    return f"{sido}-{gugun}"


def site_regions(region_list):
    out, index = [], {}
    for r in region_list:
        if r["sido"] not in index:
            index[r["sido"]] = len(out)
            out.append({"sido": r["sido"], "gugun": []})
        out[index[r["sido"]]]["gugun"].append({"name": r["gugun"], "geo": r["geo"]})
    return out


def load_regions(path=CODE_FILE):
    return build_regions(*read_rows(path))


def main():
    region_list = load_regions()
    SITE_REGIONS.parent.mkdir(parents=True, exist_ok=True)
    SITE_REGIONS.write_text(json.dumps(site_regions(region_list), ensure_ascii=False), encoding="utf-8")
    print(f"시군구 {len(region_list)}곳을 {SITE_REGIONS.relative_to(ROOT)}에 저장했습니다.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 시험 통과 확인과 지역 파일 생성**

Run: `python -m pytest tests/test_regions.py -v`
Expected: 7 passed (코드 파일이 있으므로 실제 파일 시험도 통과).

Run: `python -m pipeline.regions`
Expected: `시군구 270곳을 site/data/regions.json에 저장했습니다.`

- [ ] **Step 6: 커밋**

```bash
git add pipeline/data/AccidentHazard_CodeList.xlsx pipeline/regions.py tests/test_regions.py site/data/regions.json
git commit -m "feat: 요청변수 코드 파일로 시군구 목록과 코드 후보 생성"
```

---

### Task 3: API 호출기

**Files:**
- Create: `pipeline/koroad_client.py`
- Create: `tests/fakes.py`, `tests/test_koroad_client.py`

**Interfaces:**
- Produces: `KoroadError(Exception)`, `QuotaExceeded(KoroadError)`, `http_get(url, timeout=30) -> (int, str)`, `build_url(endpoint, auth_key, year_code, sido, gugun, page, rows) -> str`, `parse_page(status, text) -> (list[dict], int)`, `fetch_all(endpoint, auth_key, year_code, sido, gugun, get=http_get, rows=100) -> list[dict]`.
- Test helpers (`tests/fakes.py`): `make_get(responder)` → `get(url)` 함수(호출 기록 `get.calls: list[(path, query_dict)]`), `ok(items, total=None) -> (200, str)`, `EMPTY`, `PARAM_ERROR`, `QUOTA`.

- [ ] **Step 1: 시험용 가짜 응답 도구**

`tests/fakes.py`:
```python
import json
from urllib.parse import parse_qs, urlparse


def make_get(responder):
    """responder(path, query) -> (status, text). path는 'lg', 'schoolzone/child' 같은 경로."""
    calls = []

    def get(url):
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        path = parsed.path.split("/frequentzone/", 1)[1]
        calls.append((path, query))
        return responder(path, query)

    get.calls = calls
    return get


def ok(items, total=None):
    body = {"resultCode": "00", "resultMsg": "NORMAL_CODE",
            "totalCount": len(items) if total is None else total, "items": {"item": items}}
    return 200, json.dumps(body, ensure_ascii=False)


EMPTY = (200, json.dumps({"resultCode": "03", "resultMsg": "NODATA_ERROR"}))
PARAM_ERROR = (200, json.dumps({"resultCode": "10", "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR"}))
QUOTA = (200, json.dumps({"resultCode": "99", "resultMsg": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"}))


def item(fid, lat="37.5", lng="127.03", count=5, geom=None):
    return {
        "afos_fid": fid, "afos_id": "2026134", "spot_nm": f"지점{fid}", "sido_sgg_nm": "서울 강남구1",
        "occrrnc_cnt": count, "caslt_cnt": count + 1, "dth_dnv_cnt": 0, "se_dnv_cnt": 1,
        "sl_dnv_cnt": count, "wnd_dnv_cnt": 0, "la_crd": lat, "lo_crd": lng,
        "geom_json": geom if geom is not None else json.dumps(
            {"type": "Polygon", "coordinates": [[[127.03, 37.5], [127.031, 37.5], [127.031, 37.501], [127.03, 37.5]]]}),
    }
```

- [ ] **Step 2: 실패하는 시험 쓰기**

`tests/test_koroad_client.py`:
```python
import json

import pytest

from pipeline import koroad_client as kc
from tests.fakes import EMPTY, PARAM_ERROR, QUOTA, item, make_get, ok

EP = "https://opendata.koroad.or.kr/data/rest/frequentzone/lg"


def test_build_url_has_required_params():
    url = kc.build_url(EP, "KEY", "2026134", 51, 130, 2, 100)
    assert url.startswith(EP + "?")
    for part in ["authKey=KEY", "searchYearCd=2026134", "siDo=51", "guGun=130", "type=json", "numOfRows=100", "pageNo=2"]:
        assert part in url


def test_build_url_pads_gugun_to_three_digits():
    assert "guGun=050" in kc.build_url(EP, "K", "1", 11, 50, 1, 10)


def test_parse_success():
    items, total = kc.parse_page(*ok([item(1), item(2)]))
    assert [i["afos_fid"] for i in items] == [1, 2]
    assert total == 2


def test_single_item_object_becomes_list():
    body = {"resultCode": "00", "resultMsg": "NORMAL_CODE", "totalCount": 1, "items": {"item": item(7)}}
    items, total = kc.parse_page(200, json.dumps(body))
    assert [i["afos_fid"] for i in items] == [7]
    assert total == 1


def test_no_data_is_empty_result():
    assert kc.parse_page(*EMPTY) == ([], 0)


def test_param_error_raises():
    with pytest.raises(kc.KoroadError) as e:
        kc.parse_page(*PARAM_ERROR)
    assert not isinstance(e.value, kc.QuotaExceeded)


def test_quota_message_raises_quota():
    with pytest.raises(kc.QuotaExceeded):
        kc.parse_page(*QUOTA)


def test_non_json_raises_and_quota_text_detected():
    with pytest.raises(kc.KoroadError):
        kc.parse_page(200, "<html>error</html>")
    with pytest.raises(kc.QuotaExceeded):
        kc.parse_page(200, "일일 호출 한도 초과")


def test_http_error_raises():
    with pytest.raises(kc.KoroadError):
        kc.parse_page(500, "")


def test_fetch_all_follows_pages():
    all_items = [item(i) for i in range(150)]

    def responder(path, q):
        page, rows = int(q["pageNo"]), int(q["numOfRows"])
        return ok(all_items[(page - 1) * rows: page * rows], total=150)

    get = make_get(responder)
    got = kc.fetch_all(EP, "K", "2026134", 11, 680, get=get, rows=100)
    assert len(got) == 150
    assert [q["pageNo"] for _, q in get.calls] == ["1", "2"]


def test_fetch_all_stops_on_empty_page():
    get = make_get(lambda p, q: EMPTY)
    assert kc.fetch_all(EP, "K", "1", 11, 680, get=get) == []
    assert len(get.calls) == 1


def test_error_message_never_contains_key():
    get = make_get(lambda p, q: (500, "server error"))
    with pytest.raises(kc.KoroadError) as e:
        kc.fetch_all(EP, "SECRETKEY123", "1", 11, 680, get=get)
    assert "SECRETKEY123" not in str(e.value)
```

- [ ] **Step 3: 실패 확인**

Run: `python -m pytest tests/test_koroad_client.py -v`
Expected: FAIL (`cannot import name 'koroad_client'`).

- [ ] **Step 4: 구현**

`pipeline/koroad_client.py`:
```python
"""교통사고정보개방시스템 다발지역 API 한 조합의 모든 페이지를 받는다.

오류 메시지에는 인증키나 인증키가 들어간 주소를 넣지 않는다.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

QUOTA_WORDS = ("LIMITED", "EXCEED", "초과", "한도")


class KoroadError(Exception):
    pass


class QuotaExceeded(KoroadError):
    pass


def http_get(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "traffic-accident-map/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        raise KoroadError(f"네트워크 오류: {error.reason}") from None


def build_url(endpoint, auth_key, year_code, sido, gugun, page, rows):
    query = urllib.parse.urlencode({
        "authKey": auth_key, "searchYearCd": year_code, "siDo": sido, "guGun": f"{int(gugun):03d}",
        "type": "json", "numOfRows": rows, "pageNo": page,
    })
    return f"{endpoint}?{query}"


def _looks_like_quota(text):
    return any(word in text for word in QUOTA_WORDS)


def parse_page(status, text):
    """응답 하나를 판별한다. 반환 (items, total_count). 데이터 없음(03)은 ([], 0)."""
    if status != 200:
        if _looks_like_quota(text):
            raise QuotaExceeded(f"HTTP {status} 한도 초과")
        raise KoroadError(f"HTTP {status}")
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        if _looks_like_quota(text):
            raise QuotaExceeded("한도 초과 응답") from None
        raise KoroadError("JSON이 아닌 응답: " + text[:200]) from None
    code = str(body.get("resultCode", ""))
    message = str(body.get("resultMsg", ""))
    if code == "03":
        return [], 0
    if code != "00":
        if _looks_like_quota(message):
            raise QuotaExceeded(message)
        raise KoroadError(f"결과 코드 {code} {message}")
    container = body.get("items") or {}
    items = container.get("item", []) if isinstance(container, dict) else container
    if isinstance(items, dict):
        items = [items]
    items = items or []
    total = int(body.get("totalCount") or len(items))
    return items, total


def fetch_all(endpoint, auth_key, year_code, sido, gugun, get=http_get, rows=100):
    page, collected = 1, []
    while True:
        status, text = get(build_url(endpoint, auth_key, year_code, sido, gugun, page, rows))
        items, total = parse_page(status, text)
        collected.extend(items)
        if not items or len(collected) >= total:
            return collected
        page += 1
```

- [ ] **Step 5: 시험 통과 확인**

Run: `python -m pytest tests/test_koroad_client.py -v`
Expected: 12 passed.

- [ ] **Step 6: 커밋**

```bash
git add pipeline/koroad_client.py tests/fakes.py tests/test_koroad_client.py
git commit -m "feat: 다발지역 API 호출기와 결과 코드 판별"
```

---

### Task 4: 수집기

**Files:**
- Create: `pipeline/collect.py`
- Create: `tests/test_collect.py`

**Interfaces:**
- Consumes: `catalog.endpoint/year_code/TYPES/TYPES_BY_ID`, `regions.region_key/load_regions`, `koroad_client.fetch_all/build_url/http_get/KoroadError/QuotaExceeded`
- Produces: `collect_one(type_id, year, region, auth_key, get) -> (items, code_used: [sido, gugun])`, `run(type_ids, years, region_list, auth_key, raw_dir, get, pause, log) -> {"status": "complete"|"partial"|"quota", "done": int, "errors": int}`, `probe(auth_key, get, out, log) -> list[dict]`, raw 파일 형식 `raw/<type>/<year>/<첫 후보 시도>-<첫 후보 시군구>.json = {"code_used": [int, int], "items": [...]}`, `raw/progress.json = {"lg|2025|11-680": "done"|"empty"}`.

- [ ] **Step 1: 실패하는 시험 쓰기**

`tests/test_collect.py`:
```python
import json

import pytest

from pipeline import collect
from pipeline import koroad_client as kc
from tests.fakes import EMPTY, PARAM_ERROR, QUOTA, item, make_get, ok

WONJU = {"sido": "강원특별자치도", "gugun": "원주시", "codes": [[51, 130], [42, 130]], "geo": "강원특별자치도 원주시"}
GANGNAM = {"sido": "서울특별시", "gugun": "강남구", "codes": [[11, 680]], "geo": "서울특별시 강남구"}
GWANGSAN = {"sido": "전남광주통합특별시", "gugun": "광산구", "codes": [[12, 330], [29, 200]], "geo": "광주광역시 광산구"}


def test_collect_one_falls_back_to_old_code():
    get = make_get(lambda p, q: EMPTY if q["siDo"] == "51" else ok([item(1)]))
    items, used = collect.collect_one("lg", 2021, WONJU, "K", get=get)
    assert used == [42, 130]
    assert [i["afos_fid"] for i in items] == [1]


def test_collect_one_old_pair_changes_gugun_too():
    get = make_get(lambda p, q: ok([item(1)]) if (q["siDo"], q["guGun"]) == ("29", "200") else EMPTY)
    items, used = collect.collect_one("lg", 2021, GWANGSAN, "K", get=get)
    assert used == [29, 200]
    assert [(q["siDo"], q["guGun"]) for _, q in get.calls] == [("12", "330"), ("29", "200")]


def test_collect_one_all_empty_uses_first_code():
    get = make_get(lambda p, q: EMPTY)
    assert collect.collect_one("lg", 2025, WONJU, "K", get=get) == ([], [51, 130])


def test_collect_one_param_error_then_empty_is_empty():
    get = make_get(lambda p, q: PARAM_ERROR if q["siDo"] == "51" else EMPTY)
    assert collect.collect_one("lg", 2025, WONJU, "K", get=get) == ([], [51, 130])


def test_collect_one_all_errors_raise():
    get = make_get(lambda p, q: PARAM_ERROR)
    with pytest.raises(kc.KoroadError):
        collect.collect_one("lg", 2025, WONJU, "K", get=get)


def test_run_saves_raw_and_skips_done(tmp_path):
    get = make_get(lambda p, q: ok([item(1)]) if q["guGun"] == "680" else EMPTY)
    logs = []
    result = collect.run(["lg"], [2025], [GANGNAM, WONJU], "K", raw_dir=tmp_path, get=get, pause=0, log=logs.append)
    assert result == {"status": "complete", "done": 2, "errors": 0}
    saved = json.loads((tmp_path / "lg" / "2025" / "11-680.json").read_text(encoding="utf-8"))
    assert saved["code_used"] == [11, 680] and saved["items"][0]["afos_fid"] == 1
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress == {"lg|2025|11-680": "done", "lg|2025|51-130": "empty"}
    calls_before = len(get.calls)
    collect.run(["lg"], [2025], [GANGNAM, WONJU], "K", raw_dir=tmp_path, get=get, pause=0, log=logs.append)
    assert len(get.calls) == calls_before


def test_run_stops_on_quota_and_resumes(tmp_path):
    state = {"quota": True}

    def responder(p, q):
        if q["guGun"] == "130" and state["quota"]:
            return QUOTA
        return ok([item(1)])

    get = make_get(responder)
    logs = []
    first = collect.run(["lg"], [2025], [GANGNAM, WONJU], "K", raw_dir=tmp_path, get=get, pause=0, log=logs.append)
    assert first["status"] == "quota"
    assert "내일" in logs[-1]
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert list(progress) == ["lg|2025|11-680"]
    state["quota"] = False
    second = collect.run(["lg"], [2025], [GANGNAM, WONJU], "K", raw_dir=tmp_path, get=get, pause=0, log=logs.append)
    assert second == {"status": "complete", "done": 1, "errors": 0}


def test_run_continues_after_error_and_retries_later(tmp_path):
    get = make_get(lambda p, q: PARAM_ERROR if q["guGun"] == "680" else EMPTY)
    logs = []
    result = collect.run(["lg"], [2025], [GANGNAM, WONJU], "SECRET", raw_dir=tmp_path, get=get, pause=0, log=logs.append)
    assert result == {"status": "partial", "done": 1, "errors": 1}
    assert all("SECRET" not in line for line in logs)
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert "lg|2025|11-680" not in progress


def test_probe_writes_report(tmp_path):
    get = make_get(lambda p, q: ok([item(1)]))
    out = tmp_path / "probe.json"
    report = collect.probe("K", get=get, out=out, log=lambda s: None)
    assert out.exists()
    assert len(report) == 10 * 2 + 4 * 2 * 3 * 2
    assert report[0]["resultCode"] == "00" and report[0]["item_kind"] == "list"


def test_parse_years():
    assert collect.parse_years("2021-2025") == [2021, 2022, 2023, 2024, 2025]
    assert collect.parse_years("2025") == [2025]
    assert collect.parse_years("2021,2023") == [2021, 2023]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_collect.py -v`
Expected: FAIL (`cannot import name 'collect'`).

- [ ] **Step 3: 구현**

`pipeline/collect.py`:
```python
"""교통사고정보개방시스템에서 다발지역 원본을 받아 raw/에 저장한다.

사용법:
  python -m pipeline.collect --probe          탐색 호출
  python -m pipeline.collect                  전체 수집(이어받기)
  python -m pipeline.collect --years 2025     특정 연도만
"""
import argparse
import json
import pathlib
import sys
import time

from . import catalog
from . import koroad_client as kc
from . import regions as regions_mod

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG = ROOT / "config.local.json"

PROBE_REGIONS = [
    {"label": "서울 강남구", "codes": [[11, 680]]},
    {"label": "강원 원주시", "codes": [[51, 130], [42, 130]]},
    {"label": "전북 전주시완산구", "codes": [[52, 111], [45, 111]]},
    {"label": "광주 광산구", "codes": [[12, 330], [29, 200]]},
    {"label": "전남 광양시", "codes": [[12, 190], [46, 230]]},
]


def load_auth_key(path=CONFIG):
    try:
        key = json.loads(path.read_text(encoding="utf-8")).get("koroad_auth_key", "").strip()
    except FileNotFoundError:
        key = ""
    if not key or key.startswith("여기에"):
        raise SystemExit("config.local.json에 koroad_auth_key를 넣어 주세요. config.example.json을 복사해서 만들면 됩니다.")
    return key


def collect_one(type_id, year, region, auth_key, get=kc.http_get):
    """[시도, 시군구] 코드 후보를 차례로 시도한다. 결과가 있는 첫 짝을 쓰고, 모두 비면 첫 짝으로 빈 결과를 돌려준다."""
    last_error, answered = None, False
    for sido, gugun in region["codes"]:
        try:
            items = kc.fetch_all(catalog.endpoint(type_id), auth_key, catalog.year_code(type_id, year),
                                 sido, gugun, get=get)
        except kc.QuotaExceeded:
            raise
        except kc.KoroadError as error:
            last_error = error
            continue
        answered = True
        if items:
            return items, [sido, gugun]
    if not answered:
        raise last_error
    return [], list(region["codes"][0])


def combo_key(type_id, year, region):
    return f"{type_id}|{year}|{regions_mod.region_key(region)}"


def _load_progress(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_progress(path, progress):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(progress, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def run(type_ids, years, region_list, auth_key, raw_dir=RAW_DIR, get=kc.http_get, pause=0.1, log=print):
    progress_path = raw_dir / "progress.json"
    progress = _load_progress(progress_path)
    done = errors = 0
    total = len(type_ids) * len(years) * len(region_list)
    for type_id in type_ids:
        for year in years:
            for region in region_list:
                key = combo_key(type_id, year, region)
                if key in progress:
                    continue
                try:
                    items, code_used = collect_one(type_id, year, region, auth_key, get=get)
                except kc.QuotaExceeded:
                    _save_progress(progress_path, progress)
                    log(f"호출 한도에 걸렸습니다. {len(progress)}/{total} 조합 완료. 내일 같은 명령을 다시 실행하면 이어서 받습니다.")
                    return {"status": "quota", "done": done, "errors": errors}
                except kc.KoroadError as error:
                    errors += 1
                    log(f"오류: {key} — {error}")
                    continue
                out = raw_dir / type_id / str(year) / f"{regions_mod.region_key(region)}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps({"code_used": code_used, "items": items}, ensure_ascii=False), encoding="utf-8")
                progress[key] = "done" if items else "empty"
                _save_progress(progress_path, progress)
                done += 1
                if pause:
                    time.sleep(pause)
    status = "partial" if errors else "complete"
    log(f"수집 {status}: 이번 실행 {done}건 저장, 오류 {errors}건, 전체 {len(progress)}/{total} 조합 완료.")
    return {"status": status, "done": done, "errors": errors}


def _probe_call(type_id, year, sido, gugun, auth_key, get):
    status, text = get(kc.build_url(catalog.endpoint(type_id), auth_key, catalog.year_code(type_id, year), sido, gugun, 1, 100))
    entry = {"type": type_id, "year": year, "sido": sido, "gugun": gugun, "http": status}
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        entry["not_json"] = text[:200]
        return entry
    container = body.get("items")
    raw_items = container.get("item") if isinstance(container, dict) else container
    first = raw_items[0] if isinstance(raw_items, list) and raw_items else (raw_items if isinstance(raw_items, dict) else {})
    entry.update(
        resultCode=body.get("resultCode"), resultMsg=body.get("resultMsg"), top_keys=sorted(body),
        item_kind=type(raw_items).__name__,
        count=len(raw_items) if isinstance(raw_items, list) else (1 if raw_items else 0),
        totalCount=body.get("totalCount"), first_item_keys=sorted(first),
    )
    return entry


def probe(auth_key, get=kc.http_get, out=RAW_DIR / "probe_report.json", log=print):
    report = []
    seoul_sido, seoul_gugun = PROBE_REGIONS[0]["codes"][0]
    for t in catalog.TYPES:
        for year in (2021, 2025):
            report.append({"label": PROBE_REGIONS[0]["label"], **_probe_call(t["id"], year, seoul_sido, seoul_gugun, auth_key, get)})
    for region in PROBE_REGIONS[1:]:
        for type_id in ("lg", "pedestrian"):
            for year in (2021, 2023, 2025):
                for sido, gugun in region["codes"]:
                    report.append({"label": region["label"], **_probe_call(type_id, year, sido, gugun, auth_key, get)})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for e in report:
        log(f"{e['label']} {e['type']} {e['year']} 코드{e['sido']}-{e['gugun']}: HTTP {e['http']} 코드 {e.get('resultCode')} "
            f"{e.get('count', '?')}건 item={e.get('item_kind')} total={e.get('totalCount')}")
    return report


def parse_years(text):
    if "-" in text:
        start, end = (int(x) for x in text.split("-"))
        return list(range(start, end + 1))
    return [int(x) for x in text.split(",")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="교통사고 다발지역 원본 수집")
    parser.add_argument("--probe", action="store_true", help="탐색 호출만 실행")
    parser.add_argument("--types", default="all", help="all 또는 lg,child처럼 쉼표로 구분")
    parser.add_argument("--years", default="2021-2025", help="2021-2025, 2025, 2021,2023")
    args = parser.parse_args(argv)
    key = load_auth_key()
    if args.probe:
        probe(key)
        return 0
    type_ids = [t["id"] for t in catalog.TYPES] if args.types == "all" else args.types.split(",")
    unknown = [t for t in type_ids if t not in catalog.TYPES_BY_ID]
    if unknown:
        raise SystemExit(f"알 수 없는 유형: {unknown}")
    result = run(type_ids, parse_years(args.years), regions_mod.load_regions(), key)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 시험 통과 확인**

Run: `python -m pytest -v`
Expected: 전체 통과 (catalog 6, regions 7, koroad_client 12, collect 10).

- [ ] **Step 5: 커밋**

```bash
git add pipeline/collect.py tests/test_collect.py
git commit -m "feat: 이어받기와 코드 후보 전환을 갖춘 수집기"
```

---

### Task 5: 탐색 호출과 전국 수집 (실제 API)

**Files:**
- Create(사용자): `config.local.json` (git 제외)
- Create: `docs/superpowers/notes/2026-09-27-probe.md`
- Modify(탐색 결과에 따라): `pipeline/koroad_client.py`, `tests/test_koroad_client.py`

**Interfaces:**
- Consumes: Task 4 전부
- Produces: `raw/` 전체 원본, `raw/probe_report.json`, 탐색 결과 기록 문서

- [ ] **Step 1: 사용자가 인증키 넣기**

`config.example.json`을 `config.local.json`으로 복사하고, 사용자가 Task 0 Step 1의 키를 직접 붙여 넣는다. AI는 파일 내용을 읽거나 출력하지 않는다.

```bash
cp config.example.json config.local.json
git check-ignore config.local.json
```
Expected: `config.local.json` (git 제외 확인)

- [ ] **Step 2: 탐색 호출**

Run: `python -m pipeline.collect --probe`
Expected: 서울 강남구 20줄과 코드 전환 지역 48줄이 출력되고 `raw/probe_report.json`이 생긴다.

- [ ] **Step 3: 탐색 결과 판단**

`raw/probe_report.json`을 읽고 아래를 확인한다.

1. 서울 강남구 20건이 모두 `resultCode` "00" 또는 "03"인가. "10"이 나오면 요청 변수 이름 문제다. `build_url`의 `"siDo"`, `"guGun"`을 `"sido"`, `"gugun"`으로 바꾸고, `test_build_url_has_required_params`의 기대값도 같이 바꾼 뒤 다시 실행한다.
2. `top_keys`에 `totalCount`가 있는가. 없으면 `first_item_keys`와 `top_keys`를 보고 `parse_page`의 `total` 계산 위치를 실제 위치로 고치고 시험을 추가한다.
3. `item_kind`가 1건일 때 "dict"인가. dict면 이미 처리된다.
4. `first_item_keys`에 `la_crd, lo_crd, geom_json, occrrnc_cnt` 또는 `occrmc_cnt`가 있는가.
5. 코드 전환 지역(원주, 전주완산, 광산, 광양)에서 연도별로 새 짝과 예전 짝 중 어느 쪽이 결과를 주는가.
6. 한도 초과 응답이 있었는가, 교통사고정보개방시스템 로그인 후 "API 인증키 발급 현황"에 하루 한도가 표시되는가.

- [ ] **Step 4: 탐색 결과 기록**

`docs/superpowers/notes/2026-09-27-probe.md`에 Step 3의 여섯 항목 답을 실제 값으로 적는다. 인증키는 적지 않는다. 코드를 고쳤다면 `python -m pytest -v`가 모두 통과하는지 확인한다.

```bash
git add docs/superpowers/notes/2026-09-27-probe.md pipeline tests
git commit -m "docs: 탐색 호출 결과 기록"
```

- [ ] **Step 5: 전국 수집**

Run: `python -m pipeline.collect`
Expected: 마지막 줄 `수집 complete: ...` 또는 한도 초과 시 `호출 한도에 걸렸습니다 ... 내일 ...`. 한도 초과면 다음 날 같은 명령을 다시 실행한다. `partial`이면 같은 명령을 한 번 더 실행해 오류 조합을 다시 받는다.

- [ ] **Step 6: 수집 결과 확인**

```bash
python -c "import json;p=json.load(open('raw/progress.json',encoding='utf-8'));from collections import Counter;print(len(p), Counter(p.values()))"
```
Expected: 전체 조합 수(시군구 수 × 10 × 5)와 같은 개수, `done`과 `empty` 개수 출력. `raw/`는 git에 올리지 않는다.

---

### Task 6: 연속 계산기

**Files:**
- Create: `pipeline/streaks.py`
- Create: `tests/test_streaks.py`

**Interfaces:**
- Produces: `distance_m(a_lat, a_lng, b_lat, b_lng) -> float`, `assign_streaks(points_by_year: dict[int, list[dict]], radius_m: float) -> dict` (각 점 dict에 `streak: int`, `since: int`을 제자리에서 채움)

- [ ] **Step 1: 실패하는 시험 쓰기**

`tests/test_streaks.py`:
```python
from pipeline.streaks import assign_streaks, distance_m


def pt(lat, lng):
    return {"lat": lat, "lng": lng}


def test_distance_about_100m():
    assert 95 < distance_m(37.5, 127.0, 37.5009, 127.0) < 105


def test_consecutive_years_count_up():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.5003, 127.0)], 2023: [pt(37.5, 127.0003)]}
    assign_streaks(data, 150)
    assert [(p["streak"], p["since"]) for y in (2021, 2022, 2023) for p in data[y]] == [(1, 2021), (2, 2021), (3, 2021)]


def test_gap_resets_streak():
    data = {2021: [pt(37.5, 127.0)], 2022: [], 2023: [pt(37.5, 127.0)]}
    assign_streaks(data, 150)
    assert (data[2023][0]["streak"], data[2023][0]["since"]) == (1, 2023)


def test_far_points_are_different_places():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.51, 127.0)]}
    assign_streaks(data, 150)
    assert data[2022][0]["streak"] == 1


def test_one_place_links_once_per_year():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.5, 127.0), pt(37.5002, 127.0)]}
    assign_streaks(data, 150)
    assert sorted(p["streak"] for p in data[2022]) == [1, 2]


def test_nearest_place_wins():
    data = {2021: [pt(37.5, 127.0), pt(37.5012, 127.0)], 2022: [pt(37.5010, 127.0)]}
    assign_streaks(data, 150)
    assert data[2022][0]["streak"] == 2
    assert data[2022][0]["since"] == 2021
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_streaks.py -v`
Expected: FAIL (`No module named 'pipeline.streaks'`).

- [ ] **Step 3: 구현**

`pipeline/streaks.py`:
```python
"""1년 단위 유형에서 같은 장소가 몇 년 연속 다발지역이었는지 계산한다."""
import math

EARTH_RADIUS_M = 6_371_000


def distance_m(a_lat, a_lng, b_lat, b_lng):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    d_lat = p2 - p1
    d_lng = math.radians(b_lng - a_lng)
    h = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def assign_streaks(points_by_year, radius_m):
    """기준연도 오름차순으로 각 점을 반경 안의 가장 가까운 기존 장소에 연결한다.

    연결된 장소가 바로 전해에도 나왔으면 연속 연수를 1 늘리고, 아니면 1부터 다시 센다.
    한 장소는 한 해에 한 점에만 연결된다.
    """
    places = []
    for year in sorted(points_by_year):
        used = set()
        for point in points_by_year[year]:
            best, best_distance = None, None
            for index, place in enumerate(places):
                if index in used:
                    continue
                d = distance_m(point["lat"], point["lng"], place["lat"], place["lng"])
                if d <= radius_m and (best_distance is None or d < best_distance):
                    best, best_distance = index, d
            if best is None:
                places.append({"streak": 1, "since": year})
                best = len(places) - 1
            elif places[best]["last_year"] == year - 1:
                places[best]["streak"] += 1
            else:
                places[best]["streak"] = 1
                places[best]["since"] = year
            place = places[best]
            place.update(lat=point["lat"], lng=point["lng"], last_year=year)
            used.add(best)
            point["streak"], point["since"] = place["streak"], place["since"]
    return points_by_year
```

- [ ] **Step 4: 시험 통과 확인**

Run: `python -m pytest tests/test_streaks.py -v`
Expected: 6 passed.

- [ ] **Step 5: 커밋**

```bash
git add pipeline/streaks.py tests/test_streaks.py
git commit -m "feat: 연속 다발지역 계산기"
```

---

### Task 7: 가공기와 실제 데이터 가공

**Files:**
- Create: `pipeline/build.py`
- Create: `tests/test_build.py`
- Create(생성물): `site/data/meta.json`, `site/data/types.json`, `site/data/<연도>/<유형>.json`, `site/data/<연도>/<유형>/<시도>.json`

**Interfaces:**
- Consumes: `catalog.TYPES/YEARS/public_types`, `streaks.assign_streaks`, raw 파일 형식(Task 4, `code_used[0]`이 점의 `sd`가 된다)
- Produces: `compact_point(item, type_id, year, sido_used) -> dict`, `valid_coord(lat, lng) -> bool`, `polygon_coords(item) -> list | None`, `build(raw_dir, out_dir, years, today) -> {"bad_coords": int, "no_polygon": int, "points": {type: {year: count}}}`. 점 형식은 설계 문서 6장.

- [ ] **Step 1: 실패하는 시험 쓰기**

`tests/test_build.py`:
```python
import datetime
import json

from pipeline import build
from tests.fakes import item


def write_raw(root, type_id, year, key, sido, items):
    path = root / type_id / str(year) / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"code_used": [sido, int(key.split("-")[1])], "items": items}, ensure_ascii=False), encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_compact_point_converts_and_accepts_typo_field():
    raw = item(9, count=4)
    raw.pop("occrrnc_cnt")
    raw["occrmc_cnt"] = "4"
    raw["wnd_dnv_cnt"] = None
    p = build.compact_point(raw, "freezing", 2025, 11)
    assert p["id"] == "freezing-2025-9"
    assert (p["lat"], p["lng"], p["sd"], p["c"], p["w"]) == (37.5, 127.03, 11, 4, 0)


def test_polygon_parsing():
    assert build.polygon_coords(item(1))[0][0] == [127.03, 37.5]
    assert build.polygon_coords(item(1, geom="{broken")) is None
    assert build.polygon_coords(item(1, geom="")) is None


def test_build_end_to_end(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    write_raw(raw, "lg", 2024, "11-680", 11, [item(1, count=3)])
    write_raw(raw, "lg", 2025, "11-680", 11, [
        item(2, count=9), item(3, lat="37.6", lng="127.1", count=20),
        item(4, lat="", lng=""), item(5, lat="10.0", lng="127.0"), item(6, geom="{broken"),
    ])
    write_raw(raw, "lg", 2025, "51-130", 51, [item(2, count=9)])
    write_raw(raw, "pedestrian", 2025, "11-680", 11, [item(7)])

    report = build.build(raw_dir=raw, out_dir=out, years=[2024, 2025], today=datetime.date(2026, 9, 27))

    lg = read(out / "2025" / "lg.json")
    assert [p["id"] for p in lg] == ["lg-2025-3", "lg-2025-2", "lg-2025-6"]
    same_place = next(p for p in lg if p["id"] == "lg-2025-2")
    assert (same_place["streak"], same_place["since"]) == (2, 2024)
    assert "lg-2025-2" in read(out / "2025" / "lg" / "11.json")
    assert "lg-2025-6" not in read(out / "2025" / "lg" / "11.json")
    assert "streak" not in read(out / "2025" / "pedestrian.json")[0]
    assert report["bad_coords"] == 2
    assert report["no_polygon"] == 1
    assert report["points"]["lg"] == {2024: 1, 2025: 3}

    types = {t["id"]: t for t in read(out / "types.json")}
    assert types["lg"]["years"] == [2024, 2025]
    assert types["pedestrian"]["years"] == [2025]
    assert types["child"]["years"] == []
    assert read(out / "meta.json") == {"updated": "2026-09-27", "years": [2024, 2025]}
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_build.py -v`
Expected: FAIL (`cannot import name 'build'`).

- [ ] **Step 3: 구현**

`pipeline/build.py`:
```python
"""raw/ 원본을 웹사이트용 site/data/ 파일로 가공한다.

사용법: python -m pipeline.build
"""
import datetime
import json
import pathlib

from . import catalog
from .streaks import assign_streaks

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
OUT_DIR = ROOT / "site" / "data"
LAT_RANGE = (33.0, 38.7)
LNG_RANGE = (124.5, 132.0)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def compact_point(item, type_id, year, sido_used):
    lat, lng = float(item["la_crd"]), float(item["lo_crd"])
    count = item.get("occrrnc_cnt", item.get("occrmc_cnt"))
    return {
        "id": f"{type_id}-{year}-{item['afos_fid']}",
        "n": item.get("spot_nm") or "", "r": item.get("sido_sgg_nm") or "",
        "lat": round(lat, 6), "lng": round(lng, 6), "sd": sido_used,
        "c": _int(count), "k": _int(item.get("caslt_cnt")), "d": _int(item.get("dth_dnv_cnt")),
        "s": _int(item.get("se_dnv_cnt")), "l": _int(item.get("sl_dnv_cnt")), "w": _int(item.get("wnd_dnv_cnt")),
    }


def valid_coord(lat, lng):
    return LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LNG_RANGE[0] <= lng <= LNG_RANGE[1]


def polygon_coords(item):
    geom = item.get("geom_json")
    if isinstance(geom, str):
        try:
            geom = json.loads(geom)
        except json.JSONDecodeError:
            return None
    if not isinstance(geom, dict) or geom.get("type") != "Polygon" or not geom.get("coordinates"):
        return None
    try:
        return [[[round(float(x), 6), round(float(y), 6)] for x, y in ring] for ring in geom["coordinates"]]
    except (TypeError, ValueError):
        return None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build(raw_dir=RAW_DIR, out_dir=OUT_DIR, years=catalog.YEARS, today=None):
    report = {"bad_coords": 0, "no_polygon": 0, "points": {}}
    available = {}
    for t in catalog.TYPES:
        type_id = t["id"]
        points_by_year, polygons = {}, {}
        for year in years:
            folder = raw_dir / type_id / str(year)
            if not folder.exists():
                continue
            seen = {}
            for path in sorted(folder.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                for item in data.get("items", []):
                    try:
                        point = compact_point(item, type_id, year, data["code_used"][0])
                    except (KeyError, TypeError, ValueError):
                        report["bad_coords"] += 1
                        continue
                    if not valid_coord(point["lat"], point["lng"]):
                        report["bad_coords"] += 1
                        continue
                    if point["id"] in seen:
                        continue
                    seen[point["id"]] = point
                    coords = polygon_coords(item)
                    if coords is None:
                        report["no_polygon"] += 1
                    else:
                        polygons.setdefault((year, point["sd"]), {})[point["id"]] = coords
            points_by_year[year] = list(seen.values())
        if t["period"] == "annual":
            assign_streaks(points_by_year, t["radius_m"])
        available[type_id] = sorted(points_by_year)
        for year, points in points_by_year.items():
            points.sort(key=lambda p: (-p["c"], p["id"]))
            _write(out_dir / str(year) / f"{type_id}.json", points)
            report["points"].setdefault(type_id, {})[year] = len(points)
        for (year, sido), shapes in polygons.items():
            _write(out_dir / str(year) / type_id / f"{sido}.json", shapes)
    public = catalog.public_types()
    for t in public:
        t["years"] = available.get(t["id"], [])
    _write(out_dir / "types.json", public)
    all_years = sorted({y for ys in available.values() for y in ys})
    _write(out_dir / "meta.json", {"updated": (today or datetime.date.today()).isoformat(), "years": all_years})
    return report


def main():
    report = build()
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sizes = sorted(((p.stat().st_size, p) for p in OUT_DIR.glob("*/*.json")), reverse=True)[:3]
    for size, path in sizes:
        print(f"큰 점 파일: {path.relative_to(ROOT)} {size / 1024:.0f}KB")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 시험 통과 확인**

Run: `python -m pytest -v`
Expected: 전체 통과.

- [ ] **Step 5: 실제 데이터 가공**

Run: `python -m pipeline.build`
Expected: 유형별·연도별 점 개수, `bad_coords`, `no_polygon`, 가장 큰 점 파일 세 개와 크기가 출력된다. 10종 모두 2021~2025에 점이 있어야 한다. 0개인 유형·연도가 있으면 `raw/progress.json`에서 해당 조합이 모두 `empty`인지 확인하고, 모두 empty면 탐색 결과 문서에 적는다.

- [ ] **Step 6: 숫자 대조**

```bash
python - <<'EOF'
import json, pathlib
for t, y in [("lg", 2025), ("pedestrian", 2023), ("schoolzone", 2021)]:
    p = json.loads(pathlib.Path(f"site/data/{y}/{t}.json").read_text(encoding="utf-8"))[0]
    fid = p["id"].rsplit("-", 1)[1]
    for f in pathlib.Path(f"raw/{t}/{y}").glob("*.json"):
        for it in json.loads(f.read_text(encoding="utf-8"))["items"]:
            if str(it["afos_fid"]) == fid:
                print(t, y, p["n"], "사고", p["c"], "=", it.get("occrrnc_cnt", it.get("occrmc_cnt")), "사망", p["d"], "=", it["dth_dnv_cnt"])
EOF
```
Expected: 세 줄 모두 `=` 양쪽 숫자가 같다.

- [ ] **Step 7: 커밋**

```bash
git add pipeline/build.py tests/test_build.py site/data
git commit -m "feat: 가공기와 2021~2025 다발지역 데이터"
```

---

### Task 8: 화면 계산 모듈 (자바스크립트)

**Files:**
- Create: `site/js/logic.js`
- Create: `tests/js/logic.test.js`

**Interfaces:**
- Consumes: `types.json`의 유형 객체(`id, name, short, color, period, criteria, years`), 점 객체(설계 문서 6장)
- Produces: `escapeHtml(v) -> string`, `periodLabel(type, year) -> string`, `activeTypeIds(enabled: Set, types, year) -> string[]`, `filterPoints(points, {streakOnly}) -> points`, `distanceM(aLat, aLng, bLat, bLng) -> number`, `pointsNear(points, lat, lng, meters) -> points`, `inBounds(point, {south, west, north, east}) -> boolean`, `detailHtml(point, type, year) -> string`

- [ ] **Step 1: 실패하는 시험 쓰기**

`tests/js/logic.test.js`:
```js
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml, periodLabel, activeTypeIds, filterPoints, distanceM, pointsNear, inBounds, detailHtml,
} from "../../site/js/logic.js";

const LG = { id: "lg", name: "일반 (시군구별 상위 3곳)", short: "일반", color: "#E4572E", period: "annual", criteria: "기준 <문장>", years: [2024, 2025] };
const PED = { id: "pedestrian", name: "보행자", short: "보행자", color: "#6A4C93", period: "rolling3", criteria: "보행자 기준", years: [2025] };
const FRZ = { id: "freezing", name: "결빙", short: "결빙", color: "#4CC9F0", period: "rolling5", criteria: "결빙 기준", years: [2025] };
const P = { id: "lg-2025-1", n: "서울 <강남> \"역\" & 부근", lat: 37.5, lng: 127.03, sd: 11, c: 12, k: 13, d: 1, s: 3, l: 9, w: 0, streak: 3, since: 2023 };

test("escapeHtml", () => {
  assert.equal(escapeHtml(`<a href="x">&'`), "&lt;a href=&quot;x&quot;&gt;&amp;&#39;");
  assert.equal(escapeHtml(null), "");
});

test("periodLabel", () => {
  assert.equal(periodLabel(LG, 2025), "2025년 1년간");
  assert.equal(periodLabel(PED, 2025), "2023~2025년 3년간");
  assert.equal(periodLabel(FRZ, 2025), "2021~2025년 겨울철(11~3월)");
});

test("activeTypeIds skips types without that year", () => {
  assert.deepEqual(activeTypeIds(new Set(["lg", "pedestrian"]), [LG, PED, FRZ], 2024), ["lg"]);
  assert.deepEqual(activeTypeIds(new Set(["lg", "pedestrian"]), [LG, PED, FRZ], 2025), ["lg", "pedestrian"]);
});

test("filterPoints streakOnly", () => {
  const pts = [{ streak: 1 }, { streak: 2 }, {}];
  assert.equal(filterPoints(pts, { streakOnly: false }).length, 3);
  assert.deepEqual(filterPoints(pts, { streakOnly: true }), [{ streak: 2 }]);
});

test("distanceM about 100m", () => {
  const d = distanceM(37.5, 127.0, 37.5009, 127.0);
  assert.ok(d > 95 && d < 105);
});

test("pointsNear and inBounds", () => {
  const a = { lat: 37.5, lng: 127.0 }, b = { lat: 37.5001, lng: 127.0 }, c = { lat: 37.6, lng: 127.0 };
  assert.deepEqual(pointsNear([a, b, c], 37.5, 127.0, 30), [a, b]);
  const box = { south: 37.4, west: 126.9, north: 37.55, east: 127.1 };
  assert.equal(inBounds(a, box), true);
  assert.equal(inBounds(c, box), false);
});

test("detailHtml escapes and shows counts, period, streak", () => {
  const html = detailHtml(P, LG, 2025);
  assert.ok(html.includes("서울 &lt;강남&gt; &quot;역&quot; &amp; 부근"));
  assert.ok(!html.includes("<강남>"));
  assert.ok(html.includes("12건") && html.includes("1명") && html.includes("3명") && html.includes("9명"));
  assert.ok(html.includes("2025년 1년간"));
  assert.ok(html.includes("3년 연속 다발지역 (2023~2025)"));
  assert.ok(html.includes("선정 기준: 기준 &lt;문장&gt;"));
  assert.ok(html.includes("https://map.kakao.com/link/map/"));
});

test("detailHtml hides streak below 2 and for rolling types", () => {
  assert.ok(!detailHtml({ ...P, streak: 1 }, LG, 2025).includes("연속 다발지역"));
  const { streak, since, ...rolling } = P;
  const html = detailHtml(rolling, PED, 2025);
  assert.ok(!html.includes("연속 다발지역"));
  assert.ok(html.includes("2023~2025년 3년간"));
});
```

- [ ] **Step 2: 실패 확인**

Run: `npm test`
Expected: FAIL (`Cannot find module .../site/js/logic.js`).

- [ ] **Step 3: 구현**

`site/js/logic.js`:
```js
// 화면·지도와 무관한 계산만 둔다. node --test로 시험한다.

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

export function periodLabel(type, year) {
  if (type.period === "annual") return `${year}년 1년간`;
  if (type.period === "rolling3") return `${year - 2}~${year}년 3년간`;
  return `${year - 4}~${year}년 겨울철(11~3월)`;
}

export function activeTypeIds(enabled, types, year) {
  return types.filter((t) => enabled.has(t.id) && t.years.includes(year)).map((t) => t.id);
}

export function filterPoints(points, { streakOnly }) {
  return streakOnly ? points.filter((p) => (p.streak ?? 0) >= 2) : points;
}

export function distanceM(aLat, aLng, bLat, bLng) {
  const rad = (x) => (x * Math.PI) / 180;
  const p1 = rad(aLat), p2 = rad(bLat);
  const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(rad(bLng - aLng) / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

export function pointsNear(points, lat, lng, meters) {
  return points.filter((p) => distanceM(lat, lng, p.lat, p.lng) <= meters);
}

export function inBounds(p, b) {
  return p.lat >= b.south && p.lat <= b.north && p.lng >= b.west && p.lng <= b.east;
}

export function detailHtml(p, type, year) {
  const n = (v) => Number(v) || 0;
  const streak = n(p.streak) >= 2
    ? `<p class="d-streak">${n(p.streak)}년 연속 다발지역 (${n(p.since)}~${year})</p>`
    : "";
  const link = `https://map.kakao.com/link/map/${encodeURIComponent(p.n)},${n(p.lat)},${n(p.lng)}`;
  const count = (label, value, unit) => `<div><dt>${label}</dt><dd>${n(value)}${unit}</dd></div>`;
  return `<h3 class="d-name">${escapeHtml(p.n)}</h3>
<p class="d-type"><span class="dot" style="background:${escapeHtml(type.color)}"></span>${escapeHtml(type.name)} · ${periodLabel(type, year)}</p>
${streak}<dl class="d-counts">${count("사고", p.c, "건")}${count("사망", p.d, "명")}${count("중상", p.s, "명")}${count("경상", p.l, "명")}${count("부상신고", p.w, "명")}</dl>
<p class="d-criteria">선정 기준: ${escapeHtml(type.criteria)}</p>
<a class="d-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">카카오맵에서 보기</a>`;
}
```

- [ ] **Step 4: 시험 통과 확인**

Run: `npm test`
Expected: 8 tests pass.

- [ ] **Step 5: 커밋**

```bash
git add site/js/logic.js tests/js/logic.test.js
git commit -m "feat: 화면 계산 모듈(이스케이프, 기간 문구, 정보 창)"
```

---

### Task 9: 웹사이트 뼈대와 카카오 지도

**Files:**
- Create: `site/index.html`, `site/css/style.css`, `site/js/config.js`, `site/js/data.js`, `site/js/state.js`, `site/js/mapAdapter.js`, `site/js/app.js`

**Interfaces:**
- Consumes: `site/data/meta.json`, `site/data/<연도>/lg.json`
- Produces:
  - `data.js`: `loadJSON(path)`, `getMeta()`, `getTypes()`, `getRegions()`, `getPoints(year, typeId)`, `getPolygons(year, typeId, sido)` (모두 Promise)
  - `state.js`: `createState(initial) -> {get(), set(patch), subscribe(fn) -> unsubscribe}`
  - `mapAdapter.js`: `loadKakao(appKey, timeoutMs=10000) -> Promise<kakao>`, `createMap(kakao, el) -> {showPoints(points, colorOf, onClick), showPolygons(shapes), getLevel(), getBounds(), onIdle(cb), moveTo(lat, lng, level), searchPlaces(query), geocode(address)}`
  - DOM id 목록: `search-form, search-input, search-results, region-open, year, streak-only, type-chips, sheet-toggle, type-list, updated, map, map-error, detail, detail-close, detail-body, region-dialog, region-sido, region-gugun, region-msg, region-cancel, region-go`

- [ ] **Step 1: HTML**

`site/index.html`:
```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>전국 교통사고 다발지역 지도</title>
<meta name="description" content="도로교통공단 자료로 보는 전국 교통사고 다발지역 지도. 보행자, 어린이, 노인, 자전거, 이륜차, 음주운전, 화물차, 결빙 사고 다발지역을 연도별로 확인하세요.">
<link rel="stylesheet" href="css/style.css">
</head>
<body>
<div class="app">
  <aside class="panel">
    <h1 class="title">교통사고 다발지역 지도</h1>
    <form id="search-form" class="search" role="search">
      <input id="search-input" type="search" placeholder="장소·주소 검색 (예: 홍대입구역)" aria-label="장소 또는 주소 검색" autocomplete="off">
      <button type="button" id="region-open" class="btn">지역</button>
      <ul id="search-results" class="results" hidden></ul>
    </form>
    <div class="filters">
      <label><span class="sr-only">기준연도</span><select id="year"></select></label>
      <label class="check"><input type="checkbox" id="streak-only"> 연속 다발만 보기</label>
    </div>
    <section class="sheet">
      <div class="sheet-head">
        <div id="type-chips" class="chips"></div>
        <button type="button" id="sheet-toggle" class="sheet-toggle" aria-expanded="false" aria-controls="type-list" aria-label="유형 설명 펼치기">▲</button>
      </div>
      <ul id="type-list" class="type-list"></ul>
    </section>
    <footer class="foot">
      <p>자료: 도로교통공단 교통사고정보개방시스템 · 갱신 <span id="updated"></span></p>
      <p>과거 통계이며 현재 도로 상황과 다를 수 있습니다.</p>
    </footer>
  </aside>
  <main class="map-wrap">
    <div id="map" class="map" aria-label="교통사고 다발지역 지도"></div>
    <p id="map-error" class="map-error" hidden></p>
    <section id="detail" class="detail" hidden aria-live="polite">
      <button type="button" id="detail-close" class="detail-close" aria-label="닫기">×</button>
      <div id="detail-body"></div>
    </section>
  </main>
</div>
<div id="region-dialog" class="dialog" hidden>
  <div class="dialog-box" role="dialog" aria-modal="true" aria-labelledby="region-title">
    <h2 id="region-title">지역 선택</h2>
    <select id="region-sido" aria-label="시도"></select>
    <select id="region-gugun" aria-label="시군구" disabled><option value="">시군구 선택</option></select>
    <p id="region-msg" class="muted"></p>
    <div class="dialog-actions">
      <button type="button" id="region-cancel" class="btn">취소</button>
      <button type="button" id="region-go" class="btn primary">이동</button>
    </div>
  </div>
</div>
<script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: CSS**

`site/css/style.css`:
```css
:root {
  --ink: #1b2430; --ink-2: #4a5566; --line: #d9dee5; --bg: #ffffff; --bg-2: #f3f5f8;
  --accent: #1d4ed8; --danger: #b42318;
  --font: "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body { font-family: var(--font); color: var(--ink); background: var(--bg); font-size: 15px; word-break: keep-all; }
[hidden] { display: none !important; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.muted { color: var(--ink-2); font-size: 13px; }

.app { display: grid; grid-template-rows: auto auto 1fr auto auto; height: 100dvh; }
.panel { display: contents; }
.title { display: none; }

.search { grid-row: 1; position: relative; display: flex; gap: 8px; padding: calc(10px + env(safe-area-inset-top, 0px)) 12px 6px; }
.search input { flex: 1; min-width: 0; font: inherit; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; }
.btn { font: inherit; padding: 9px 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--ink); cursor: pointer; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.btn:focus-visible, .chip:focus-visible, .search input:focus-visible, select:focus-visible, .sheet-toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.results { position: absolute; left: 12px; right: 12px; top: 100%; z-index: 20; margin: 0; padding: 4px; list-style: none; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 24px rgba(0, 0, 0, .12); max-height: 50dvh; overflow: auto; }
.results button { display: flex; flex-direction: column; align-items: flex-start; width: 100%; padding: 8px; border: 0; background: none; font: inherit; text-align: left; cursor: pointer; border-radius: 6px; }
.results button:hover { background: var(--bg-2); }
.results span { color: var(--ink-2); font-size: 13px; }
.results .muted { padding: 8px; }

.filters { grid-row: 2; display: flex; align-items: center; gap: 12px; padding: 4px 12px 8px; }
.filters select { font: inherit; padding: 6px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); }
.check { display: flex; align-items: center; gap: 6px; font-size: 14px; }

.map-wrap { grid-row: 3; position: relative; min-height: 0; }
.map { position: absolute; inset: 0; }
.map-error { position: absolute; left: 12px; right: 12px; bottom: 12px; margin: 0; padding: 12px; background: var(--bg); border: 1px solid var(--danger); color: var(--danger); border-radius: 8px; z-index: 5; }

.sheet { grid-row: 4; border-top: 1px solid var(--line); background: var(--bg); }
.sheet-head { display: flex; align-items: center; gap: 8px; padding: 8px 0 8px 12px; }
.chips { display: flex; gap: 6px; overflow-x: auto; flex: 1; scrollbar-width: none; }
.chip { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; font: inherit; font-size: 14px; padding: 6px 11px; border: 1px solid var(--line); border-radius: 999px; background: var(--bg); color: var(--ink-2); cursor: pointer; }
.chip[aria-pressed="true"] { border-color: var(--ink); color: var(--ink); font-weight: 600; background: var(--bg-2); }
.chip:disabled { opacity: .4; cursor: not-allowed; }
.chip-err { color: var(--danger); font-weight: 700; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex: none; }
.sheet-toggle { flex: none; margin-right: 8px; width: 36px; height: 36px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); cursor: pointer; }
.type-list { display: none; margin: 0; padding: 0 12px 8px; list-style: none; max-height: 40dvh; overflow: auto; }
.sheet-open .type-list { display: block; }
.sheet-open .sheet-toggle { transform: rotate(180deg); }
.type-list li { display: grid; grid-template-columns: auto 1fr; gap: 2px 8px; align-items: center; padding: 8px 0; border-top: 1px solid var(--bg-2); }
.type-list p { grid-column: 2; margin: 0; font-size: 13px; color: var(--ink-2); }

.foot { grid-row: 5; padding: 4px 12px calc(6px + env(safe-area-inset-bottom, 0px)); font-size: 11.5px; color: var(--ink-2); background: var(--bg); }
.foot p { margin: 0; }

.detail { position: absolute; left: 8px; right: 8px; bottom: 8px; z-index: 10; max-height: 60%; overflow: auto; padding: 14px 16px; background: var(--bg); border-radius: 12px; box-shadow: 0 8px 28px rgba(0, 0, 0, .2); }
.detail-close { position: absolute; top: 6px; right: 8px; border: 0; background: none; font-size: 22px; cursor: pointer; line-height: 1; padding: 4px; }
.d-name { margin: 0 28px 6px 0; font-size: 16px; }
.d-type { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; font-size: 13px; color: var(--ink-2); }
.d-streak { margin: 0 0 8px; font-weight: 700; color: var(--danger); }
.d-counts { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 0 0 8px; }
.d-counts div { background: var(--bg-2); border-radius: 6px; padding: 6px 2px; text-align: center; }
.d-counts dt { font-size: 11.5px; color: var(--ink-2); }
.d-counts dd { margin: 0; font-weight: 700; font-variant-numeric: tabular-nums; }
.d-criteria { margin: 0 0 8px; font-size: 12.5px; color: var(--ink-2); }
.d-link { font-size: 14px; color: var(--accent); }
.d-list { list-style: none; margin: 0; padding: 0; }
.d-list button { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px; border: 0; border-bottom: 1px solid var(--bg-2); background: none; font: inherit; text-align: left; cursor: pointer; }

.dialog { position: fixed; inset: 0; z-index: 30; display: grid; place-items: center; background: rgba(0, 0, 0, .35); padding: 16px; }
.dialog-box { width: min(360px, 100%); background: var(--bg); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.dialog-box h2 { margin: 0; font-size: 17px; }
.dialog-box select { font: inherit; padding: 9px; border: 1px solid var(--line); border-radius: 8px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }

@media (min-width: 900px) {
  .app { grid-template-columns: 360px 1fr; grid-template-rows: 1fr; }
  .panel { display: flex; flex-direction: column; border-right: 1px solid var(--line); overflow: auto; }
  .title { display: block; margin: 0; padding: 16px 16px 4px; font-size: 19px; }
  .search { padding: 10px 16px 6px; }
  .filters { padding: 4px 16px 8px; }
  .sheet { border-top: 0; }
  .sheet-head { padding-left: 16px; }
  .chips { flex-wrap: wrap; overflow: visible; }
  .sheet-toggle { display: none; }
  .type-list { display: block; max-height: none; padding: 0 16px; }
  .foot { margin-top: auto; padding: 12px 16px; }
  .map-wrap { grid-row: 1; grid-column: 2; }
  .detail { left: auto; right: 16px; top: 16px; bottom: auto; width: 360px; max-height: calc(100% - 32px); }
}
```

- [ ] **Step 3: 설정, 데이터, 상태 모듈**

`site/js/config.js` (사용자가 Task 0 Step 2의 JavaScript 키로 바꾼다. 등록한 주소에서만 작동하는 키라 공개해도 된다):
```js
export const KAKAO_JS_KEY = "여기에_카카오_JavaScript_키";
```

`site/js/data.js`:
```js
const cache = new Map();

export function loadJSON(path) {
  if (!cache.has(path)) {
    const promise = fetch(path)
      .then((res) => {
        if (!res.ok) throw new Error(`${path} ${res.status}`);
        return res.json();
      })
      .catch((error) => {
        cache.delete(path);
        throw error;
      });
    cache.set(path, promise);
  }
  return cache.get(path);
}

export const getMeta = () => loadJSON("data/meta.json");
export const getTypes = () => loadJSON("data/types.json");
export const getRegions = () => loadJSON("data/regions.json");
export const getPoints = (year, typeId) => loadJSON(`data/${year}/${typeId}.json`);
export const getPolygons = (year, typeId, sido) => loadJSON(`data/${year}/${typeId}/${sido}.json`);
```

`site/js/state.js`:
```js
export function createState(initial) {
  let current = { ...initial };
  const listeners = new Set();
  return {
    get: () => current,
    set(patch) {
      current = { ...current, ...patch };
      listeners.forEach((fn) => fn(current));
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
```

- [ ] **Step 4: 지도 담당 모듈**

`site/js/mapAdapter.js`:
```js
// 카카오맵과 대화하는 코드는 이 파일에만 둔다. 다른 지도로 바꿀 때 이 파일만 교체한다.
const SDK_URL = "https://dapi.kakao.com/v2/maps/sdk.js";

export function loadKakao(appKey, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("카카오맵 로드 시간 초과")), timeoutMs);
    const script = document.createElement("script");
    script.src = `${SDK_URL}?appkey=${encodeURIComponent(appKey)}&autoload=false&libraries=services,clusterer`;
    script.onerror = () => {
      clearTimeout(timer);
      reject(new Error("카카오맵 스크립트 로드 실패"));
    };
    script.onload = () => {
      if (!window.kakao || !window.kakao.maps) {
        clearTimeout(timer);
        reject(new Error("카카오맵 초기화 실패"));
        return;
      }
      window.kakao.maps.load(() => {
        clearTimeout(timer);
        resolve(window.kakao);
      });
    };
    document.head.appendChild(script);
  });
}

function circleImage(kakao, color, ring) {
  const size = ring ? 22 : 16;
  const half = size / 2;
  const stroke = ring ? 3 : 1.5;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><circle cx="${half}" cy="${half}" r="${half - stroke}" fill="${color}" fill-opacity="0.9" stroke="${ring ? "#111111" : "#ffffff"}" stroke-width="${stroke}"/></svg>`;
  return new kakao.maps.MarkerImage(
    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    new kakao.maps.Size(size, size),
    { offset: new kakao.maps.Point(half, half) },
  );
}

export function createMap(kakao, el) {
  const map = new kakao.maps.Map(el, { center: new kakao.maps.LatLng(36.35, 127.85), level: 13 });
  const clusterer = new kakao.maps.MarkerClusterer({ map, averageCenter: true, minLevel: 7 });
  const places = new kakao.maps.services.Places();
  const geocoder = new kakao.maps.services.Geocoder();
  const images = new Map();
  let polygons = [];

  const imageFor = (color, ring) => {
    const key = `${color}|${ring}`;
    if (!images.has(key)) images.set(key, circleImage(kakao, color, ring));
    return images.get(key);
  };

  return {
    showPoints(points, colorOf, onClick) {
      clusterer.clear();
      const markers = points.map((p) => {
        const marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(p.lat, p.lng),
          image: imageFor(colorOf(p), (p.streak ?? 0) >= 2),
          title: p.n,
        });
        kakao.maps.event.addListener(marker, "click", () => onClick(p));
        return marker;
      });
      clusterer.addMarkers(markers);
    },
    showPolygons(shapes) {
      polygons.forEach((polygon) => polygon.setMap(null));
      polygons = shapes.map(({ coords, color }) => new kakao.maps.Polygon({
        map,
        path: coords[0].map(([lng, lat]) => new kakao.maps.LatLng(lat, lng)),
        strokeWeight: 1, strokeColor: color, strokeOpacity: 0.8, fillColor: color, fillOpacity: 0.25,
      }));
    },
    getLevel: () => map.getLevel(),
    getBounds() {
      const bounds = map.getBounds();
      const sw = bounds.getSouthWest();
      const ne = bounds.getNorthEast();
      return { south: sw.getLat(), west: sw.getLng(), north: ne.getLat(), east: ne.getLng() };
    },
    onIdle(callback) {
      kakao.maps.event.addListener(map, "idle", callback);
    },
    moveTo(lat, lng, level) {
      map.setLevel(level);
      map.setCenter(new kakao.maps.LatLng(lat, lng));
    },
    searchPlaces(query) {
      return new Promise((resolve, reject) => {
        places.keywordSearch(query, (data, status) => {
          const Status = kakao.maps.services.Status;
          if (status === Status.OK) {
            resolve(data.slice(0, 10).map((d) => ({
              name: d.place_name, address: d.road_address_name || d.address_name, lat: Number(d.y), lng: Number(d.x),
            })));
          } else if (status === Status.ZERO_RESULT) {
            resolve([]);
          } else {
            reject(new Error("장소 검색 오류"));
          }
        });
      });
    },
    geocode(address) {
      return new Promise((resolve) => {
        geocoder.addressSearch(address, (data, status) => {
          const ok = status === kakao.maps.services.Status.OK && data[0];
          resolve(ok ? { lat: Number(data[0].y), lng: Number(data[0].x) } : null);
        });
      });
    },
  };
}
```

- [ ] **Step 5: 임시 진입점**

`site/js/app.js` (Task 10에서 전체를 교체한다):
```js
import { KAKAO_JS_KEY } from "./config.js";
import { loadKakao, createMap } from "./mapAdapter.js";
import { getMeta, getPoints } from "./data.js";

async function main() {
  const meta = await getMeta();
  const year = Math.max(...meta.years);
  let kakao;
  try {
    kakao = await loadKakao(KAKAO_JS_KEY);
  } catch {
    const el = document.getElementById("map-error");
    el.textContent = "지도를 불러오지 못했습니다. 잠시 후 다시 시도하세요.";
    el.hidden = false;
    return;
  }
  const map = createMap(kakao, document.getElementById("map"));
  map.showPoints(await getPoints(year, "lg"), () => "#E4572E", (p) => console.log("clicked", p.id));
}

main();
```

- [ ] **Step 6: 키 넣기와 브라우저 확인**

사용자가 `site/js/config.js`의 키를 바꾼 뒤, AI가 로컬 서버를 띄운다.

Run (백그라운드): `python -m http.server 8000 --directory site --bind 127.0.0.1`

브라우저 자동화 도구로 `http://localhost:8000`을 열고 확인한다.
1. 콘솔에 오류가 없다. (favicon 404는 무시)
2. `document.getElementById('map-error').hidden === true`
3. `document.querySelectorAll('#map img').length > 0` 또는 숫자 원(클러스터) 요소가 있다.
4. 스크린샷에 전국 지도와 점·숫자 원이 보인다.

확인 후 서버를 끈다.

- [ ] **Step 7: 커밋**

```bash
git add site/index.html site/css site/js
git commit -m "feat: 웹사이트 뼈대와 카카오 지도에 일반 다발지역 표시"
```

---

### Task 10: 조작 화면 전체 (유형, 연도, 연속, 구역 모양, 정보 창, 검색, 지역)

**Files:**
- Create: `site/js/ui.js`
- Modify: `site/js/app.js` (전체 교체)

**Interfaces:**
- Consumes: Task 8 `logic.js` 전부, Task 9 `data.js`, `state.js`, `mapAdapter.js`, DOM id 목록
- Produces: `ui.js`의 `showMapError(msg?)`, `showFooter(meta)`, `setupControls({types, years, state})`, `markTypeError(id, on)`, `showDetail(html)`, `showChooser(points, typeById, pick)`, `setupDetailClose()`, `setupSearch(map)`, `setupRegions(map, regions)`

- [ ] **Step 1: 화면 담당 모듈**

`site/js/ui.js`:
```js
import { escapeHtml } from "./logic.js";

const $ = (id) => document.getElementById(id);

export function showMapError(message = "지도를 불러오지 못했습니다. 잠시 후 다시 시도하세요.") {
  const el = $("map-error");
  el.textContent = message;
  el.hidden = false;
}

export function showFooter(meta) {
  $("updated").textContent = meta.updated;
}

export function setupControls({ types, years, state }) {
  const chips = $("type-chips");
  chips.innerHTML = types.map((t) => `<button type="button" class="chip" id="chip-${escapeHtml(t.id)}" data-id="${escapeHtml(t.id)}" aria-pressed="false"><span class="dot" style="background:${escapeHtml(t.color)}"></span>${escapeHtml(t.short)}<span class="chip-err" hidden> !</span></button>`).join("");
  $("type-list").innerHTML = types.map((t) => `<li><span class="dot" style="background:${escapeHtml(t.color)}"></span><b>${escapeHtml(t.name)}</b><p>${escapeHtml(t.criteria)}</p></li>`).join("");

  const yearSelect = $("year");
  yearSelect.innerHTML = [...years].sort((a, b) => b - a).map((y) => `<option value="${y}">${y}년 기준</option>`).join("");

  const sync = (s) => {
    chips.querySelectorAll(".chip").forEach((button) => {
      const type = types.find((t) => t.id === button.dataset.id);
      const available = type.years.includes(s.year);
      button.disabled = !available;
      button.title = available ? "" : `${s.year}년 자료가 없습니다`;
      button.setAttribute("aria-pressed", String(available && s.enabled.has(button.dataset.id)));
    });
    yearSelect.value = String(s.year);
    $("streak-only").checked = s.streakOnly;
  };

  chips.addEventListener("click", (event) => {
    const button = event.target.closest(".chip");
    if (!button || button.disabled) return;
    const next = new Set(state.get().enabled);
    if (next.has(button.dataset.id)) next.delete(button.dataset.id);
    else next.add(button.dataset.id);
    state.set({ enabled: next });
  });
  yearSelect.addEventListener("change", () => state.set({ year: Number(yearSelect.value) }));
  $("streak-only").addEventListener("change", (event) => state.set({ streakOnly: event.target.checked }));
  $("sheet-toggle").addEventListener("click", () => {
    const open = document.body.classList.toggle("sheet-open");
    $("sheet-toggle").setAttribute("aria-expanded", String(open));
  });
  state.subscribe(sync);
  sync(state.get());
}

export function markTypeError(id, on) {
  const button = document.getElementById(`chip-${id}`);
  if (button) button.querySelector(".chip-err").hidden = !on;
}

export function showDetail(html) {
  $("detail-body").innerHTML = html;
  $("detail").hidden = false;
}

export function showChooser(points, typeById, pick) {
  $("detail-body").innerHTML = `<p class="muted">이 자리에 다발지역이 ${points.length}곳 있습니다.</p><ul class="d-list">${points.map((p, i) => `<li><button type="button" data-i="${i}"><span class="dot" style="background:${escapeHtml(typeById[p.t].color)}"></span>${escapeHtml(typeById[p.t].short)} · ${escapeHtml(p.n)}</button></li>`).join("")}</ul>`;
  $("detail").hidden = false;
  $("detail-body").querySelectorAll("button[data-i]").forEach((button) => {
    button.addEventListener("click", () => pick(points[Number(button.dataset.i)]));
  });
}

export function setupDetailClose() {
  $("detail-close").addEventListener("click", () => { $("detail").hidden = true; });
}

export function setupSearch(map) {
  const form = $("search-form");
  const input = $("search-input");
  const list = $("search-results");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    list.hidden = false;
    list.innerHTML = `<li class="muted">검색 중…</li>`;
    try {
      const results = await map.searchPlaces(query);
      if (!results.length) {
        list.innerHTML = `<li class="muted">검색 결과가 없습니다. 지역 버튼으로 찾아보세요.</li>`;
        return;
      }
      list.innerHTML = results.map((r, i) => `<li><button type="button" data-i="${i}"><b>${escapeHtml(r.name)}</b><span>${escapeHtml(r.address)}</span></button></li>`).join("");
      list.querySelectorAll("button[data-i]").forEach((button) => {
        button.addEventListener("click", () => {
          const r = results[Number(button.dataset.i)];
          map.moveTo(r.lat, r.lng, 4);
          list.hidden = true;
        });
      });
    } catch {
      list.innerHTML = `<li class="muted">검색하지 못했습니다. 잠시 후 다시 시도하세요.</li>`;
    }
  });
  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) list.hidden = true;
  });
}

export function setupRegions(map, regions) {
  const dialog = $("region-dialog");
  const sido = $("region-sido");
  const gugun = $("region-gugun");
  const message = $("region-msg");
  sido.innerHTML = `<option value="">시도 선택</option>` + regions.map((r, i) => `<option value="${i}">${escapeHtml(r.sido)}</option>`).join("");
  sido.addEventListener("change", () => {
    const region = regions[Number(sido.value)];
    gugun.innerHTML = `<option value="">시군구 선택</option>` + (region && sido.value !== ""
      ? region.gugun.map((g, i) => `<option value="${i}">${escapeHtml(g.name)}</option>`).join("")
      : "");
    gugun.disabled = sido.value === "";
  });
  $("region-open").addEventListener("click", () => {
    message.textContent = "";
    dialog.hidden = false;
    sido.focus();
  });
  $("region-cancel").addEventListener("click", () => { dialog.hidden = true; });
  $("region-go").addEventListener("click", async () => {
    if (sido.value === "" || gugun.value === "") {
      message.textContent = "시도와 시군구를 모두 골라 주세요.";
      return;
    }
    const target = regions[Number(sido.value)].gugun[Number(gugun.value)];
    const position = await map.geocode(target.geo);
    if (!position) {
      message.textContent = "이 지역의 위치를 찾지 못했습니다. 검색창을 이용해 주세요.";
      return;
    }
    map.moveTo(position.lat, position.lng, 7);
    dialog.hidden = true;
  });
}
```

- [ ] **Step 2: 진입점 전체 교체**

`site/js/app.js`:
```js
import { KAKAO_JS_KEY } from "./config.js";
import { loadKakao, createMap } from "./mapAdapter.js";
import { getMeta, getTypes, getRegions, getPoints, getPolygons } from "./data.js";
import { createState } from "./state.js";
import { activeTypeIds, filterPoints, pointsNear, inBounds, detailHtml } from "./logic.js";
import {
  showMapError, showFooter, setupControls, markTypeError, showDetail, showChooser,
  setupDetailClose, setupSearch, setupRegions,
} from "./ui.js";

const POLYGON_LEVEL = 5;
const NEAR_METERS = 30;

async function main() {
  const [meta, types, regions] = await Promise.all([getMeta(), getTypes(), getRegions()]);
  const typeById = Object.fromEntries(types.map((t) => [t.id, t]));
  const state = createState({ year: Math.max(...meta.years), enabled: new Set(["lg"]), streakOnly: false });
  showFooter(meta);
  setupControls({ types, years: meta.years, state });
  setupDetailClose();

  let kakao;
  try {
    kakao = await loadKakao(KAKAO_JS_KEY);
  } catch {
    showMapError();
    return;
  }
  const map = createMap(kakao, document.getElementById("map"));
  setupSearch(map);
  setupRegions(map, regions);

  let visible = [];
  let renderSeq = 0;

  const openPoint = (point) => {
    const year = state.get().year;
    const near = pointsNear(visible, point.lat, point.lng, NEAR_METERS);
    if (near.length > 1) {
      showChooser(near, typeById, (picked) => showDetail(detailHtml(picked, typeById[picked.t], year)));
    } else {
      showDetail(detailHtml(point, typeById[point.t], year));
    }
  };

  async function renderPolygons() {
    if (map.getLevel() > POLYGON_LEVEL) {
      map.showPolygons([]);
      return;
    }
    const seq = renderSeq;
    const { year } = state.get();
    const bounds = map.getBounds();
    const inView = visible.filter((p) => inBounds(p, bounds));
    const files = new Map();
    for (const p of inView) {
      const key = `${p.t}|${p.sd}`;
      if (!files.has(key)) files.set(key, getPolygons(year, p.t, p.sd).catch(() => ({})));
    }
    const loaded = new Map();
    for (const [key, promise] of files) loaded.set(key, await promise);
    if (seq !== renderSeq) return;
    map.showPolygons(inView.flatMap((p) => {
      const coords = loaded.get(`${p.t}|${p.sd}`)?.[p.id];
      return coords ? [{ coords, color: typeById[p.t].color }] : [];
    }));
  }

  async function renderPoints() {
    const seq = ++renderSeq;
    const { year, enabled, streakOnly } = state.get();
    const lists = await Promise.all(activeTypeIds(enabled, types, year).map(async (id) => {
      try {
        const points = await getPoints(year, id);
        markTypeError(id, false);
        return points.map((p) => ({ ...p, t: id }));
      } catch {
        markTypeError(id, true);
        return [];
      }
    }));
    if (seq !== renderSeq) return;
    visible = filterPoints(lists.flat(), { streakOnly });
    map.showPoints(visible, (p) => typeById[p.t].color, openPoint);
    document.getElementById("detail").hidden = true;
    await renderPolygons();
  }

  state.subscribe(renderPoints);
  map.onIdle(renderPolygons);
  await renderPoints();
}

main().catch((error) => {
  console.error(error);
  showMapError("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.");
});
```

- [ ] **Step 3: 자동 시험 재확인**

Run: `npm test` 그리고 `python -m pytest -q`
Expected: 모두 통과.

- [ ] **Step 4: 브라우저 확인 (PC 1280×800)**

Run (백그라운드): `python -m http.server 8000 --directory site --bind 127.0.0.1`

브라우저 자동화 도구로 `http://localhost:8000`을 열고 순서대로 확인한다.
1. 처음 화면: 2025년 기준이 선택되어 있고, "일반" 버튼만 눌린 상태이며 지도에 점이나 숫자 원이 있다.
2. "보행자" 버튼을 누르면 `aria-pressed="true"`가 되고 다른 색 점이 추가된다. 다시 누르면 사라진다.
3. 연도를 2021로 바꾸면 점이 바뀐다. 10개 버튼이 모두 활성 상태다.
4. "연속 다발만 보기"를 켜면 점 수가 줄고 굵은 테두리 점만 남는다. 끄면 원래대로 돌아온다.
5. 검색창에 "홍대입구역"을 입력하고 제출하면 결과 목록이 나오고, 첫 결과를 누르면 지도가 그곳으로 확대되며 구역 모양(반투명 영역)이 보인다.
6. 유형 버튼 다섯 개를 0.1초 간격으로 연달아 누른 뒤 1초 기다리면, 눌린 버튼과 지도에 표시된 유형 색이 일치한다.
7. 점 하나를 누르면 정보 창에 지점명, 기간 문구, 사고·사망·중상·경상·부상신고 수, 선정 기준, "카카오맵에서 보기" 링크가 나온다. × 로 닫힌다.
8. "지역" → 서울특별시 → 강남구 → 이동을 누르면 강남구로 이동한다. "전남광주통합특별시" → "광산구"도 이동한다.
9. 검색창에 "ㅁㄴㅇㄹㅁㄴㅇㄹ"을 넣으면 "검색 결과가 없습니다. 지역 버튼으로 찾아보세요."가 나온다.
10. 아래(또는 왼쪽 패널 아래)에 출처 문구와 갱신일, 안내 문구가 보인다.

- [ ] **Step 5: 커밋**

```bash
git add site/js/ui.js site/js/app.js
git commit -m "feat: 유형·연도·연속 필터, 구역 모양, 정보 창, 검색, 지역 선택"
```

---

### Task 11: 휴대폰 화면, 오류 상태, 전체 검증

**Files:**
- Modify(확인 결과에 따라): `site/css/style.css`, `site/js/ui.js`

**Interfaces:**
- Consumes: 완성된 웹사이트

- [ ] **Step 1: 휴대폰 크기 확인 (390×844)**

로컬 서버를 띄우고 브라우저 크기를 390×844로 바꾼 뒤 확인한다.
1. 위에서부터 검색줄, 연도·연속 줄, 지도, 유형 버튼 줄, 출처 줄 순서로 보이고 가로 스크롤이 생기지 않는다(`document.documentElement.scrollWidth <= 390`).
2. 유형 버튼 줄이 옆으로 밀려 전부 누를 수 있다.
3. ▲를 누르면 유형 설명 목록이 펼쳐지고, 다시 누르면 접힌다.
4. 정보 창이 지도 아래쪽에 뜨고, 사고 수 다섯 칸이 한 줄에 잘리지 않고 보인다.
5. 지역 선택 창이 화면 안에 들어온다.

문제가 있으면 `style.css`의 해당 규칙을 고치고 다시 확인한다.

- [ ] **Step 2: 오류 상태 확인**

1. 브라우저 자동화 도구의 코드 실행으로 `page.route('**/dapi.kakao.com/**', r => r.abort())`를 건 뒤 새로 고침하면 "지도를 불러오지 못했습니다. 잠시 후 다시 시도하세요."가 보인다. 확인 후 차단을 푼다.
2. `page.route('**/data/2025/pedestrian.json', r => r.abort())`를 건 뒤 새로 고침하고 "보행자"를 누르면 보행자 버튼에 "!"가 붙고, "일반" 점은 계속 보인다. 확인 후 차단을 푼다.

- [ ] **Step 3: 첫 화면 속도**

브라우저 자동화 도구에서 `performance.getEntriesByType('navigation')[0]`과 `data/2025/lg.json` 요청 시간을 확인한다. Task 7 Step 5에서 기록한 가장 큰 점 파일 크기와 함께 탐색 결과 문서에 적는다. 첫 화면에 점이 보일 때까지 3초를 넘으면 사용자에게 보고하고 파일 분할을 제안한다.

- [ ] **Step 4: 숫자 대조 (화면)**

2025년 일반 다발지역에서 점 하나를 눌러 정보 창의 사고·사망 수를 읽고, `site/data/2025/lg.json`의 같은 지점 값과 비교한다.

- [ ] **Step 5: 커밋**

```bash
git add site docs
git commit -m "fix: 휴대폰 화면과 오류 상태 점검 반영"
```

---

### Task 12: GitHub Pages 공개

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: `site/` 전체

- [ ] **Step 1: 배포 설정**

`.github/workflows/pages.yml`:
```yaml
name: Deploy site
on:
  push:
    branches: [main]
  workflow_dispatch: {}
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v4
```

`README.md`:
```markdown
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
```

```bash
git add .github README.md
git commit -m "chore: GitHub Pages 배포 설정과 안내"
```

- [ ] **Step 2: 저장소 만들기와 올리기 (사용자와 함께)**

사용자가 GitHub에서 새 공개 저장소를 만든다(예: `traffic-accident-map`). 올리기 전에 인증키가 저장소에 없는지 확인한다.

```bash
git ls-files | grep -E "config.local|raw/" ; echo "exit=$?"
```
Expected: 출력 없이 `exit=1`.

작업 줄기를 main으로 합친 뒤 올린다. 원격 주소는 사용자가 만든 저장소 주소를 쓴다.
```bash
git checkout -b main
git remote add origin https://github.com/<사용자>/traffic-accident-map.git
git push -u origin main
```
GitHub 저장소 → Settings → Pages → Source를 "GitHub Actions"로 바꾼다. Actions 탭에서 배포가 초록색으로 끝나는지 확인한다. 사용한 action 버전에 대한 경고가 보이면 경고가 안내하는 버전으로 바꾸고 다시 올린다.

- [ ] **Step 3: 카카오 키에 공개 주소 등록**

카카오 개발자 → 앱 → 플랫폼 → Web 사이트 도메인에 `https://<사용자>.github.io`를 추가한다.

- [ ] **Step 4: 공개 사이트 확인**

브라우저 자동화 도구로 `https://<사용자>.github.io/traffic-accident-map/`을 열어 Task 10 Step 4의 1, 2, 5, 7번과 Task 11 Step 1의 1번을 다시 확인한다.
