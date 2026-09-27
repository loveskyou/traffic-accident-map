import { KAKAO_JS_KEY } from "./config.js";
import { loadKakao, createMap } from "./mapAdapter.js";
import { getMeta, getTypes, getRegions, getPoints, getPolygons } from "./data.js";
import { createState } from "./state.js";
import { activeTypeIds, filterPoints, pointsNear, inBounds, detailHtml, createLatest } from "./logic.js";
import {
  showMapError, showFooter, setupControls, markTypeError, showDetail, showChooser,
  setupDetailClose, setupSearch, setupRegions,
} from "./ui.js";

const POLYGON_LEVEL = 5;
const NEAR_METERS = 30;

async function main() {
  const [meta, types, regions] = await Promise.all([getMeta(), getTypes(), getRegions()]);
  const typeById = Object.fromEntries(types.map((t) => [t.id, t]));
  const state = createState({ year: Math.max(...meta.years), enabled: new Set(["lg"]), streakOnly: false });
  showFooter(meta);
  setupControls({ types, years: meta.years, state });
  setupDetailClose();

  let kakao;
  try {
    kakao = await loadKakao(KAKAO_JS_KEY);
  } catch {
    showMapError();
    return;
  }
  const map = createMap(kakao, document.getElementById("map"));
  setupSearch(map);
  setupRegions(map, regions);

  let visible = [];
  const pointsTurn = createLatest();
  const polygonsTurn = createLatest();

  const openPoint = (point) => {
    const year = state.get().year;
    const near = pointsNear(visible, point.lat, point.lng, NEAR_METERS);
    if (near.length > 1) {
      showChooser(near, typeById, (picked) => showDetail(detailHtml(picked, typeById[picked.t], year)));
    } else {
      showDetail(detailHtml(point, typeById[point.t], year));
    }
  };

  async function renderPolygons() {
    const turn = polygonsTurn.next();
    if (map.getLevel() > POLYGON_LEVEL) {
      map.showPolygons([]);
      return;
    }
    const { year } = state.get();
    const bounds = map.getBounds();
    const inView = visible.filter((p) => inBounds(p, bounds));
    const files = new Map();
    for (const p of inView) {
      const key = `${p.t}|${p.sd}`;
      if (!files.has(key)) files.set(key, getPolygons(year, p.t, p.sd).catch(() => ({})));
    }
    const loaded = new Map();
    for (const [key, promise] of files) loaded.set(key, await promise);
    if (!polygonsTurn.isCurrent(turn)) return;
    map.showPolygons(inView.flatMap((p) => {
      const coords = loaded.get(`${p.t}|${p.sd}`)?.[p.id];
      return coords ? [{ coords, color: typeById[p.t].color }] : [];
    }));
  }

  async function renderPoints() {
    const turn = pointsTurn.next();
    const { year, enabled, streakOnly } = state.get();
    const lists = await Promise.all(activeTypeIds(enabled, types, year).map(async (id) => {
      try {
        const points = await getPoints(year, id);
        markTypeError(id, false);
        return points.map((p) => ({ ...p, t: id }));
      } catch {
        markTypeError(id, true);
        return [];
      }
    }));
    if (!pointsTurn.isCurrent(turn)) return;
    visible = filterPoints(lists.flat(), { streakOnly });
    map.showPoints(visible, (p) => typeById[p.t].color, openPoint);
    document.getElementById("detail").hidden = true;
    await renderPolygons();
  }

  state.subscribe(renderPoints);
  map.onIdle(renderPolygons);
  await renderPoints();
}

main().catch((error) => {
  console.error(error);
  showMapError("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.");
});
