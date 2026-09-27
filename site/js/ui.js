import { escapeHtml, ALL } from "./logic.js";

const $ = (id) => document.getElementById(id);

export function showMapError(message = "지도를 불러오지 못했습니다. 잠시 후 다시 시도하세요.") {
  const el = $("map-error");
  el.textContent = message;
  el.hidden = false;
}

export function showFooter(meta) {
  $("updated").textContent = meta.updated;
}

export function setupControls({ types, years, state }) {
  const chips = $("type-chips");
  chips.innerHTML = types.map((t) => `<button type="button" class="chip" id="chip-${escapeHtml(t.id)}" data-id="${escapeHtml(t.id)}" aria-pressed="false"><span class="dot" style="background:${escapeHtml(t.color)}"></span>${escapeHtml(t.short)}<span class="chip-err" hidden> !</span></button>`).join("");
  $("type-list").innerHTML = types.map((t) => `<li><span class="dot" style="background:${escapeHtml(t.color)}"></span><b>${escapeHtml(t.name)}</b><p>${escapeHtml(t.criteria)}</p></li>`).join("");

  const yearSelect = $("year");
  const sorted = [...years].sort((a, b) => a - b);
  yearSelect.innerHTML = `<option value="${ALL}">${sorted[0]}~${sorted[sorted.length - 1]} 전체</option>`
    + [...sorted].reverse().map((y) => `<option value="${y}">${y}년 기준</option>`).join("");

  const sync = (s) => {
    chips.querySelectorAll(".chip").forEach((button) => {
      const type = types.find((t) => t.id === button.dataset.id);
      const available = s.year === ALL ? type.years.length > 0 : type.years.includes(s.year);
      button.disabled = !available;
      button.title = available ? "" : (s.year === ALL ? "자료가 없습니다" : `${s.year}년 자료가 없습니다`);
      button.setAttribute("aria-pressed", String(available && s.enabled.has(button.dataset.id)));
    });
    yearSelect.value = String(s.year);
    $("streak-only").checked = s.streakOnly;
    $("streak-label").textContent = s.year === ALL ? "여러 해 다발만 보기" : "연속 다발만 보기";
  };

  chips.addEventListener("click", (event) => {
    const button = event.target.closest(".chip");
    if (!button || button.disabled) return;
    const next = new Set(state.get().enabled);
    if (next.has(button.dataset.id)) next.delete(button.dataset.id);
    else next.add(button.dataset.id);
    state.set({ enabled: next });
  });
  yearSelect.addEventListener("change", () => state.set({ year: yearSelect.value === ALL ? ALL : Number(yearSelect.value) }));
  $("streak-only").addEventListener("change", (event) => state.set({ streakOnly: event.target.checked }));
  $("sheet-toggle").addEventListener("click", () => {
    const open = document.body.classList.toggle("sheet-open");
    $("sheet-toggle").setAttribute("aria-expanded", String(open));
  });
  state.subscribe(sync);
  sync(state.get());
}

export function markTypeError(id, on) {
  const button = document.getElementById(`chip-${id}`);
  if (button) button.querySelector(".chip-err").hidden = !on;
}

export function showDetail(html) {
  $("detail-body").innerHTML = html;
  $("detail").hidden = false;
}

export function showChooser(points, typeById, pick) {
  $("detail-body").innerHTML = `<p class="muted">이 자리에 다발지역이 ${points.length}곳 있습니다.</p><ul class="d-list">${points.map((p, i) => `<li><button type="button" data-i="${i}"><span class="dot" style="background:${escapeHtml(typeById[p.t].color)}"></span>${escapeHtml(typeById[p.t].short)} · ${escapeHtml(p.n)}</button></li>`).join("")}</ul>`;
  $("detail").hidden = false;
  $("detail-body").querySelectorAll("button[data-i]").forEach((button) => {
    button.addEventListener("click", () => pick(points[Number(button.dataset.i)]));
  });
}

export function setupDetailClose() {
  $("detail-close").addEventListener("click", () => { $("detail").hidden = true; });
}

export function setupSearch(map) {
  const form = $("search-form");
  const input = $("search-input");
  const list = $("search-results");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    list.hidden = false;
    list.innerHTML = `<li class="muted">검색 중…</li>`;
    try {
      const results = await map.searchPlaces(query);
      if (!results.length) {
        list.innerHTML = `<li class="muted">검색 결과가 없습니다. 지역 버튼으로 찾아보세요.</li>`;
        return;
      }
      list.innerHTML = results.map((r, i) => `<li><button type="button" data-i="${i}"><b>${escapeHtml(r.name)}</b><span>${escapeHtml(r.address)}</span></button></li>`).join("");
      list.querySelectorAll("button[data-i]").forEach((button) => {
        button.addEventListener("click", () => {
          const r = results[Number(button.dataset.i)];
          map.moveTo(r.lat, r.lng, 4);
          list.hidden = true;
        });
      });
    } catch {
      list.innerHTML = `<li class="muted">검색하지 못했습니다. 잠시 후 다시 시도하세요.</li>`;
    }
  });
  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) list.hidden = true;
  });
}

export function setupRegions(map, regions) {
  const dialog = $("region-dialog");
  const sido = $("region-sido");
  const gugun = $("region-gugun");
  const message = $("region-msg");
  sido.innerHTML = `<option value="">시도 선택</option>` + regions.map((r, i) => `<option value="${i}">${escapeHtml(r.sido)}</option>`).join("");
  sido.addEventListener("change", () => {
    const region = regions[Number(sido.value)];
    gugun.innerHTML = `<option value="">시군구 선택</option>` + (region && sido.value !== ""
      ? region.gugun.map((g, i) => `<option value="${i}">${escapeHtml(g.name)}</option>`).join("")
      : "");
    gugun.disabled = sido.value === "";
  });
  $("region-open").addEventListener("click", () => {
    message.textContent = "";
    dialog.hidden = false;
    sido.focus();
  });
  $("region-cancel").addEventListener("click", () => { dialog.hidden = true; });
  $("region-go").addEventListener("click", async () => {
    if (sido.value === "" || gugun.value === "") {
      message.textContent = "시도와 시군구를 모두 골라 주세요.";
      return;
    }
    const target = regions[Number(sido.value)].gugun[Number(gugun.value)];
    const position = await map.geocode(target.geo);
    if (!position) {
      message.textContent = "이 지역의 위치를 찾지 못했습니다. 검색창을 이용해 주세요.";
      return;
    }
    map.moveTo(position.lat, position.lng, 7);
    dialog.hidden = true;
  });
}
