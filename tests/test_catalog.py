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
