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
