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


class ParamError(KoroadError):
    """결과 코드 10(요청 변수 오류). 그 연도에 없는 코드로 물었을 때 나온다."""


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
        if code == "10":
            raise ParamError(f"결과 코드 {code} {message}")
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
