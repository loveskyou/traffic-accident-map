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
