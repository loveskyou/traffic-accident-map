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
