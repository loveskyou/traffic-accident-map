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


def test_multipolygon_uses_first_polygon():
    ring = [[127.03, 37.5], [127.031, 37.5], [127.031, 37.501], [127.03, 37.5]]
    geom = json.dumps({"type": "MultiPolygon", "coordinates": [[ring], [[[128.0, 36.0], [128.1, 36.0], [128.0, 36.0]]]]})
    assert build.polygon_coords(item(1, geom=geom)) == [ring]


def test_year_with_only_empty_results_is_not_available(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    write_raw(raw, "truck", 2024, "11-680", 11, [item(1)])
    write_raw(raw, "truck", 2025, "11-680", 11, [])
    build.build(raw_dir=raw, out_dir=out, years=[2024, 2025], today=datetime.date(2026, 9, 27))
    types = {t["id"]: t for t in read(out / "types.json")}
    assert types["truck"]["years"] == [2024]
    assert not (out / "2025" / "truck.json").exists()


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


def test_all_years_file_merges_same_place(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    write_raw(raw, "lg", 2023, "11-680", 11, [item(1, count=4)])
    write_raw(raw, "lg", 2025, "11-680", 11, [item(2, count=9), item(3, lat="37.6", lng="127.1", count=20)])
    write_raw(raw, "pedestrian", 2024, "11-680", 11, [item(7, count=8)])
    write_raw(raw, "pedestrian", 2025, "11-680", 11, [item(8, count=9)])
    build.build(raw_dir=raw, out_dir=out, years=[2023, 2024, 2025], today=datetime.date(2026, 9, 27))

    lg = read(out / "all" / "lg.json")
    assert len(lg) == 2
    merged = lg[0]
    assert merged["years"] == [2023, 2025]
    assert merged["recs"] == [[2025, 9, 10, 0, 1, 9, 0], [2023, 4, 5, 0, 1, 4, 0]]
    assert (merged["n"], merged["c"], merged["py"], merged["pid"], merged["sd"]) == ("지점2", 9, 2025, "lg-2025-2", 11)
    assert merged["streak"] == 1
    assert lg[1]["years"] == [2025]

    ped = read(out / "all" / "pedestrian.json")
    assert len(ped) == 1 and ped[0]["years"] == [2024, 2025]
    assert "streak" not in ped[0]
    assert "place" not in read(out / "2025" / "lg.json")[0]


def test_all_years_streak_is_longest_run():
    points = {y: [{"id": f"lg-{y}-1", "n": "A", "lat": 37.5, "lng": 127.0, "sd": 11,
                   "c": 3, "k": 3, "d": 0, "s": 0, "l": 3, "w": 0}] for y in (2021, 2022, 2024, 2025)}
    from pipeline.streaks import assign_streaks
    assign_streaks(points, 150)
    merged = build.merge_places(points, annual=True)
    assert merged[0]["years"] == [2021, 2022, 2024, 2025]
    assert merged[0]["streak"] == 2


def test_all_years_ids_are_unique():
    def p(y, fid, lat):
        return {"id": f"lg-{y}-{fid}", "n": "A", "lat": lat, "lng": 127.0, "sd": 11,
                "c": 3, "k": 3, "d": 0, "s": 0, "l": 3, "w": 0}
    points = {2024: [p(2024, 2, 37.5)], 2025: [p(2025, 2, 37.7)]}
    from pipeline.streaks import assign_streaks
    assign_streaks(points, 150)
    ids = [m["id"] for m in build.merge_places(points, annual=True)]
    assert len(set(ids)) == 2
