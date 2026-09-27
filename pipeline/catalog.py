"""도로교통공단 교통사고정보개방시스템 다발지역 유형 10종의 고정 정보."""

BASE_URL = "https://opendata.koroad.or.kr/data/rest/frequentzone/"
YEARS = [2021, 2022, 2023, 2024, 2025]

TYPES = [
    {
        "id": "lg", "name": "일반 (시군구별 상위 3곳)", "short": "일반", "path": "lg",
        "period": "annual", "radius_m": 150, "color": "#E4572E",
        "criteria": "1년간 발생한 전체 교통사고 가운데 반경 150m 안에서 3건 이상 발생한 지점 중 시군구별 상위 3곳",
        "year_codes": {2021: "2022046", 2022: "2023026", 2023: "2024056", 2024: "2025119", 2025: "2026134"},
    },
    {
        "id": "pedestrian", "name": "보행자", "short": "보행자", "path": "pedstrians",
        "period": "rolling3", "radius_m": 100, "color": "#6A4C93",
        "criteria": "최근 3년간 보행자 사망·중상 사고가 반경 100m 안에서 7건 이상 발생한 곳",
        "year_codes": {2021: "2022040", 2022: "2023060", 2023: "2024051", 2024: "2025083", 2025: "2026122"},
    },
    {
        "id": "child", "name": "보행어린이", "short": "보행어린이", "path": "child",
        "period": "annual", "radius_m": 200, "color": "#F4A259",
        "criteria": "1년간 12세 이하 어린이 보행자 사고가 반경 200m 안에서 3건 이상(사망사고 포함 시 2건 이상) 발생한 곳",
        "year_codes": {2021: "2022084", 2022: "2023011", 2023: "2024042", 2024: "2025108", 2025: "2026124"},
    },
    {
        "id": "oldman", "name": "보행노인", "short": "보행노인", "path": "oldman",
        "period": "rolling3", "radius_m": 100, "color": "#2A9D8F",
        "criteria": "최근 3년간 65세 이상 보행노인 사망·중상 사고가 반경 100m 안에서 5건 이상 발생한 곳",
        "year_codes": {2021: "2022042", 2022: "2023057", 2023: "2024044", 2024: "2025076", 2025: "2026121"},
    },
    {
        "id": "bicycle", "name": "자전거", "short": "자전거", "path": "bicycle",
        "period": "annual", "radius_m": 100, "color": "#1D70B8",
        "criteria": "1년간 자전거가 관련된 사고가 반경 100m 안에서 4건 이상(사망사고 포함 시 3건 이상) 발생한 곳. 2021년 자료는 반경 200m 기준",
        "year_codes": {2021: "2022083", 2022: "2023016", 2023: "2024046", 2024: "2025081", 2025: "2026114"},
    },
    {
        "id": "motorcycle", "name": "이륜차", "short": "이륜차", "path": "motorcycle",
        "period": "rolling3", "radius_m": 100, "color": "#8C564B",
        "criteria": "최근 3년간 이륜차(원동기장치자전거·사륜ATV 포함) 사망·중상 사고가 반경 100m 안에서 4건 이상 발생한 곳",
        "year_codes": {2021: "2022032", 2022: "2023017", 2023: "2024047", 2024: "2025091", 2025: "2026113"},
    },
    {
        "id": "schoolzone", "name": "어린이보호구역 내 어린이", "short": "스쿨존", "path": "schoolzone/child",
        "period": "annual", "radius_m": 300, "color": "#E9C46A",
        "criteria": "1년간 어린이보호구역에서 12세 이하 어린이 사고가 반경 300m 안에서 2건 이상 발생했거나 사망사고가 난 곳",
        "year_codes": {2021: "2022038", 2022: "2023010", 2023: "2024041", 2024: "2025066", 2025: "2026076"},
    },
    {
        "id": "drunk", "name": "음주운전", "short": "음주운전", "path": "drunk",
        "period": "rolling3", "radius_m": 100, "color": "#C1121F",
        "criteria": "최근 3년간 음주운전 사망·중상 사고가 반경 100m 안에서 3건 이상 발생한 곳",
        "year_codes": {2021: "2022051", 2022: "2023018", 2023: "2024049", 2024: "2025085", 2025: "2026116"},
    },
    {
        "id": "truck", "name": "화물차", "short": "화물차", "path": "truck",
        "period": "rolling3", "radius_m": 100, "color": "#4A4E69",
        "criteria": "최근 3년간 화물차 사망·중상 사고가 반경 100m 안에서 4건 이상 발생한 곳",
        "year_codes": {2021: "2022048", 2022: "2023054", 2023: "2024048", 2024: "2025089", 2025: "2026135"},
    },
    {
        "id": "freezing", "name": "결빙", "short": "결빙", "path": "freezing",
        "period": "rolling5", "radius_m": 200, "color": "#4CC9F0",
        "criteria": "최근 5년간 11~3월 서리·결빙 노면 사고가 반경 200m 안에서 3건 이상(사망사고 포함 시 2건 이상) 발생한 곳",
        "year_codes": {2021: "2022082", 2022: "2023071", 2023: "2024055", 2024: "2025113", 2025: "2026125"},
    },
]

TYPES_BY_ID = {t["id"]: t for t in TYPES}
PUBLIC_FIELDS = ("id", "name", "short", "color", "period", "radius_m", "criteria")


def endpoint(type_id):
    return BASE_URL + TYPES_BY_ID[type_id]["path"]


def year_code(type_id, year):
    return TYPES_BY_ID[type_id]["year_codes"][year]


def period_label(type_id, year):
    period = TYPES_BY_ID[type_id]["period"]
    if period == "annual":
        return f"{year}년 1년간"
    if period == "rolling3":
        return f"{year - 2}~{year}년 3년간"
    return f"{year - 4}~{year}년 겨울철(11~3월)"


def public_types():
    return [{**{k: t[k] for k in PUBLIC_FIELDS}, "years": list(YEARS)} for t in TYPES]
