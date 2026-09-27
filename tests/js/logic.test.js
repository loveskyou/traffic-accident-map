import { test } from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml, periodLabel, activeTypeIds, filterPoints, distanceM, pointsNear, inBounds, detailHtml, createLatest, detailAllHtml, ALL,
} from "../../site/js/logic.js";

const LG = { id: "lg", name: "일반 (시군구별 상위 3곳)", short: "일반", color: "#E4572E", period: "annual", criteria: "기준 <문장>", years: [2024, 2025] };
const PED = { id: "pedestrian", name: "보행자", short: "보행자", color: "#6A4C93", period: "rolling3", criteria: "보행자 기준", years: [2025] };
const FRZ = { id: "freezing", name: "결빙", short: "결빙", color: "#4CC9F0", period: "rolling5", criteria: "결빙 기준", years: [2025] };
const P = { id: "lg-2025-1", n: "서울 <강남> \"역\" & 부근", lat: 37.5, lng: 127.03, sd: 11, c: 12, k: 13, d: 1, s: 3, l: 9, w: 0, streak: 3, since: 2023 };

test("escapeHtml", () => {
  assert.equal(escapeHtml(`<a href="x">&'`), "&lt;a href=&quot;x&quot;&gt;&amp;&#39;");
  assert.equal(escapeHtml(null), "");
});

test("periodLabel", () => {
  assert.equal(periodLabel(LG, 2025), "2025년 1년간");
  assert.equal(periodLabel(PED, 2025), "2023~2025년 3년간");
  assert.equal(periodLabel(FRZ, 2025), "2021~2025년 겨울철(11~3월)");
});

test("activeTypeIds skips types without that year", () => {
  assert.deepEqual(activeTypeIds(new Set(["lg", "pedestrian"]), [LG, PED, FRZ], 2024), ["lg"]);
  assert.deepEqual(activeTypeIds(new Set(["lg", "pedestrian"]), [LG, PED, FRZ], 2025), ["lg", "pedestrian"]);
});

test("filterPoints streakOnly", () => {
  const pts = [{ streak: 1 }, { streak: 2 }, {}];
  assert.equal(filterPoints(pts, { streakOnly: false }).length, 3);
  assert.deepEqual(filterPoints(pts, { streakOnly: true }), [{ streak: 2 }]);
});

test("distanceM about 100m", () => {
  const d = distanceM(37.5, 127.0, 37.5009, 127.0);
  assert.ok(d > 95 && d < 105);
});

test("pointsNear and inBounds", () => {
  const a = { lat: 37.5, lng: 127.0 }, b = { lat: 37.5001, lng: 127.0 }, c = { lat: 37.6, lng: 127.0 };
  assert.deepEqual(pointsNear([a, b, c], 37.5, 127.0, 30), [a, b]);
  const box = { south: 37.4, west: 126.9, north: 37.55, east: 127.1 };
  assert.equal(inBounds(a, box), true);
  assert.equal(inBounds(c, box), false);
});

test("detailHtml escapes and shows counts, period, streak", () => {
  const html = detailHtml(P, LG, 2025);
  assert.ok(html.includes("서울 &lt;강남&gt; &quot;역&quot; &amp; 부근"));
  assert.ok(!html.includes("<강남>"));
  assert.ok(html.includes("12건") && html.includes("1명") && html.includes("3명") && html.includes("9명"));
  assert.ok(html.includes("2025년 1년간"));
  assert.ok(html.includes("3년 연속 다발지역 (2023~2025)"));
  assert.ok(html.includes("선정 기준: 기준 &lt;문장&gt;"));
  assert.ok(html.includes("https://map.kakao.com/link/map/"));
});

test("detailHtml hides streak below 2 and for rolling types", () => {
  assert.ok(!detailHtml({ ...P, streak: 1 }, LG, 2025).includes("연속 다발지역"));
  const { streak, since, ...rolling } = P;
  const html = detailHtml(rolling, PED, 2025);
  assert.ok(!html.includes("연속 다발지역"));
  assert.ok(html.includes("2023~2025년 3년간"));
});

test("createLatest: only the newest ticket is current", () => {
  const latest = createLatest();
  const a = latest.next();
  const b = latest.next();
  assert.equal(latest.isCurrent(a), false);
  assert.equal(latest.isCurrent(b), true);
});

const MERGED = {
  id: "lg-all-4", n: "모란 <삼거리>", lat: 37.43, lng: 127.13, sd: 41, c: 86, years: [2021, 2022, 2023, 2025],
  recs: [[2025, 86, 110, 0, 11, 100, 10], [2023, 70, 90, 1, 5, 80, 4], [2022, 60, 70, 0, 3, 60, 2], [2021, 50, 60, 0, 2, 50, 1]],
  py: 2025, pid: "lg-2025-9", streak: 3,
};

test("activeTypeIds for all years: any type with some year", () => {
  const none = { ...FRZ, id: "x", years: [] };
  assert.deepEqual(activeTypeIds(new Set(["lg", "pedestrian", "x"]), [LG, PED, none], ALL), ["lg", "pedestrian"]);
});

test("filterPoints multiYearOnly keeps places seen 2+ years", () => {
  const pts = [{ years: [2021] }, { years: [2021, 2025] }];
  assert.deepEqual(filterPoints(pts, { multiYearOnly: true }), [{ years: [2021, 2025] }]);
});

test("detailAllHtml lists years and a row per year, escaped", () => {
  const html = detailAllHtml(MERGED, LG);
  assert.ok(html.includes("모란 &lt;삼거리&gt;") && !html.includes("<삼거리>"));
  assert.ok(html.includes("다발지역이었던 해: 2021·2022·2023·2025 (4번)"));
  assert.ok(html.includes("최장 3년 연속"));
  assert.ok(html.includes("<td>2025</td><td>86</td>") && html.includes("<td>2021</td><td>50</td>"));
  assert.ok(html.includes("선정 기준: 기준 &lt;문장&gt;"));
  assert.ok(html.includes("https://map.kakao.com/link/map/"));
});

test("detailAllHtml explains rolling totals and hides streak", () => {
  const html = detailAllHtml({ ...MERGED, streak: undefined, years: [2025], recs: [[2025, 9, 9, 0, 1, 8, 0]] }, PED);
  assert.ok(html.includes("각 해의 숫자는 그 해까지 3년간 집계"));
  assert.ok(!html.includes("연속"));
});
