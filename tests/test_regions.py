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


def test_incheon_donggu_legacy_code_is_added():
    result = by_name(regions.build_regions(SIDO + [("인천광역시", 28)], GUGUN))
    assert result[("인천광역시", "동구(구)")]["codes"] == [[28, 140]]


def test_site_regions_hides_legacy_names():
    rows = GUGUN + [("서울특별시", "남구(구)", 170)]
    out = regions.site_regions(regions.build_regions(SIDO, rows))
    assert all(not g["name"].endswith("(구)") for grp in out for g in grp["gugun"])
    assert by_name(regions.build_regions(SIDO, rows))[("서울특별시", "남구(구)")]["codes"] == [[11, 170]]


@pytest.mark.skipif(not regions.CODE_FILE.exists(), reason="코드 파일 없음")
def test_real_code_file():
    result = regions.load_regions()
    assert len(result) == 271
    assert all(100 <= g <= 999 for r in result for _, g in r["codes"])
    named = by_name(result)
    assert named[("전남광주통합특별시", "광산구")]["codes"] == [[12, 330], [29, 200]]
    assert all(len(r["codes"]) == 2 for r in result if r["sido"] == "전남광주통합특별시")
