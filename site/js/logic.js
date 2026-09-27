// 화면·지도와 무관한 계산만 둔다. node --test로 시험한다.

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

export function periodLabel(type, year) {
  if (type.period === "annual") return `${year}년 1년간`;
  if (type.period === "rolling3") return `${year - 2}~${year}년 3년간`;
  return `${year - 4}~${year}년 겨울철(11~3월)`;
}

export function activeTypeIds(enabled, types, year) {
  return types.filter((t) => enabled.has(t.id) && t.years.includes(year)).map((t) => t.id);
}

export function filterPoints(points, { streakOnly }) {
  return streakOnly ? points.filter((p) => (p.streak ?? 0) >= 2) : points;
}

export function distanceM(aLat, aLng, bLat, bLng) {
  const rad = (x) => (x * Math.PI) / 180;
  const p1 = rad(aLat), p2 = rad(bLat);
  const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(rad(bLng - aLng) / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

export function pointsNear(points, lat, lng, meters) {
  return points.filter((p) => distanceM(lat, lng, p.lat, p.lng) <= meters);
}

export function inBounds(p, b) {
  return p.lat >= b.south && p.lat <= b.north && p.lng >= b.west && p.lng <= b.east;
}

export function detailHtml(p, type, year) {
  const n = (v) => Number(v) || 0;
  const streak = n(p.streak) >= 2
    ? `<p class="d-streak">${n(p.streak)}년 연속 다발지역 (${n(p.since)}~${year})</p>`
    : "";
  const link = `https://map.kakao.com/link/map/${encodeURIComponent(p.n)},${n(p.lat)},${n(p.lng)}`;
  const count = (label, value, unit) => `<div><dt>${label}</dt><dd>${n(value)}${unit}</dd></div>`;
  return `<h3 class="d-name">${escapeHtml(p.n)}</h3>
<p class="d-type"><span class="dot" style="background:${escapeHtml(type.color)}"></span>${escapeHtml(type.name)} · ${periodLabel(type, year)}</p>
${streak}<dl class="d-counts">${count("사고", p.c, "건")}${count("사망", p.d, "명")}${count("중상", p.s, "명")}${count("경상", p.l, "명")}${count("부상신고", p.w, "명")}</dl>
<p class="d-criteria">선정 기준: ${escapeHtml(type.criteria)}</p>
<a class="d-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">카카오맵에서 보기</a>`;
}

// 늦게 끝난 이전 요청이 최신 화면을 덮어쓰지 않도록 번호표를 나눠 준다.
export function createLatest() {
  let current = 0;
  return {
    next: () => ++current,
    isCurrent: (ticket) => ticket === current,
  };
}
