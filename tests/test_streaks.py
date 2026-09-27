from pipeline.streaks import assign_streaks, distance_m


def pt(lat, lng):
    return {"lat": lat, "lng": lng}


def test_distance_about_100m():
    assert 95 < distance_m(37.5, 127.0, 37.5009, 127.0) < 105


def test_consecutive_years_count_up():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.5003, 127.0)], 2023: [pt(37.5, 127.0003)]}
    assign_streaks(data, 150)
    assert [(p["streak"], p["since"]) for y in (2021, 2022, 2023) for p in data[y]] == [(1, 2021), (2, 2021), (3, 2021)]


def test_gap_resets_streak():
    data = {2021: [pt(37.5, 127.0)], 2022: [], 2023: [pt(37.5, 127.0)]}
    assign_streaks(data, 150)
    assert (data[2023][0]["streak"], data[2023][0]["since"]) == (1, 2023)


def test_far_points_are_different_places():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.51, 127.0)]}
    assign_streaks(data, 150)
    assert data[2022][0]["streak"] == 1


def test_one_place_links_once_per_year():
    data = {2021: [pt(37.5, 127.0)], 2022: [pt(37.5, 127.0), pt(37.5002, 127.0)]}
    assign_streaks(data, 150)
    assert sorted(p["streak"] for p in data[2022]) == [1, 2]


def test_nearest_place_wins():
    data = {2021: [pt(37.5, 127.0), pt(37.5012, 127.0)], 2022: [pt(37.5010, 127.0)]}
    assign_streaks(data, 150)
    assert data[2022][0]["streak"] == 2
    assert data[2022][0]["since"] == 2021


def test_same_place_gets_same_place_number():
    data = {2021: [pt(37.5, 127.0), pt(37.6, 127.0)], 2022: [pt(37.5003, 127.0)]}
    assign_streaks(data, 150)
    assert data[2022][0]["place"] == data[2021][0]["place"]
    assert data[2021][1]["place"] != data[2021][0]["place"]
