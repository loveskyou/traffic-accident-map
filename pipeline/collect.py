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
    """[시도, 시군구] 코드 후보를 차례로 시도한다. 결과가 있는 첫 짝을 쓴다.

    빈 결과는 적어도 한 후보가 "데이터 없음"으로 답하고, 나머지 후보도 "데이터 없음"이거나
    요청 변수 오류(그 연도에 없는 코드)일 때만 돌려준다. 그 밖의 오류가 난 후보가 있거나
    모든 후보가 요청 변수 오류면 오류를 올려 다음 실행에서 다시 받게 한다.
    """
    last_error, param_error, answered = None, None, False
    for sido, gugun in region["codes"]:
        try:
            items = kc.fetch_all(catalog.endpoint(type_id), auth_key, catalog.year_code(type_id, year),
                                 sido, gugun, get=get)
        except kc.QuotaExceeded:
            raise
        except kc.ParamError as error:
            param_error = error
            continue
        except kc.KoroadError as error:
            last_error = error
            continue
        answered = True
        if items:
            return items, [sido, gugun]
    if last_error is not None:
        raise last_error
    if not answered:
        raise param_error
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
