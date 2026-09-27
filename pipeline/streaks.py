"""1년 단위 유형에서 같은 장소가 몇 년 연속 다발지역이었는지 계산한다."""
import math

EARTH_RADIUS_M = 6_371_000


def distance_m(a_lat, a_lng, b_lat, b_lng):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    d_lat = p2 - p1
    d_lng = math.radians(b_lng - a_lng)
    h = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def assign_streaks(points_by_year, radius_m):
    """기준연도 오름차순으로 각 점을 반경 안의 가장 가까운 기존 장소에 연결한다.

    연결된 장소가 바로 전해에도 나왔으면 연속 연수를 1 늘리고, 아니면 1부터 다시 센다.
    한 장소는 한 해에 한 점에만 연결된다.
    """
    places = []
    for year in sorted(points_by_year):
        used = set()
        for point in points_by_year[year]:
            best, best_distance = None, None
            for index, place in enumerate(places):
                if index in used:
                    continue
                d = distance_m(point["lat"], point["lng"], place["lat"], place["lng"])
                if d <= radius_m and (best_distance is None or d < best_distance):
                    best, best_distance = index, d
            if best is None:
                places.append({"streak": 1, "since": year})
                best = len(places) - 1
            elif places[best]["last_year"] == year - 1:
                places[best]["streak"] += 1
            else:
                places[best]["streak"] = 1
                places[best]["since"] = year
            place = places[best]
            place.update(lat=point["lat"], lng=point["lng"], last_year=year)
            used.add(best)
            point["streak"], point["since"] = place["streak"], place["since"]
    return points_by_year
