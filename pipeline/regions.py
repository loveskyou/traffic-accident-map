"""교통사고정보개방시스템 요청변수 코드 파일에서 시군구 목록을 만든다."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE_FILE = ROOT / "pipeline" / "data" / "AccidentHazard_CodeList.xlsx"
SITE_REGIONS = ROOT / "site" / "data" / "regions.json"

OLD_SIDO_NAME = {"강원특별자치도": "강원도(구)", "전북특별자치도": "전라북도(구)"}
MERGED = "전남광주통합특별시"
# 코드 파일에서 빠진 예전 시군구. 개편 전 기준연도 자료를 받기 위해 수집 목록에만 넣는다.
LEGACY_EXTRA = [("인천광역시", "동구(구)", 140)]
LEGACY_SUFFIX = "(구)"
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
    known = {(grp, name) for grp, name, _ in gugun_rows}
    extra = [r for r in LEGACY_EXTRA if r[0] in code and (r[0], r[1]) not in known]
    for grp, name, gcode in list(gugun_rows) + extra:
        if grp.endswith(LEGACY_SUFFIX):
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
    """지역 선택 창용 목록. 예전 시군구(이름 끝 "(구)")는 지도에서 위치를 찾을 수 없어 뺀다."""
    out, index = [], {}
    for r in region_list:
        if r["gugun"].endswith(LEGACY_SUFFIX):
            continue
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
