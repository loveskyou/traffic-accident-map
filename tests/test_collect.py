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


def test_collect_one_empty_then_server_error_raises():
    get = make_get(lambda p, q: EMPTY if q["siDo"] == "51" else (500, "server error"))
    with pytest.raises(kc.KoroadError):
        collect.collect_one("lg", 2021, WONJU, "K", get=get)


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
