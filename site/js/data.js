const cache = new Map();

export function loadJSON(path) {
  if (!cache.has(path)) {
    const promise = fetch(path)
      .then((res) => {
        if (!res.ok) throw new Error(`${path} ${res.status}`);
        return res.json();
      })
      .catch((error) => {
        cache.delete(path);
        throw error;
      });
    cache.set(path, promise);
  }
  return cache.get(path);
}

export const getMeta = () => loadJSON("data/meta.json");
export const getTypes = () => loadJSON("data/types.json");
export const getRegions = () => loadJSON("data/regions.json");
export const getPoints = (year, typeId) => loadJSON(`data/${year}/${typeId}.json`);
export const getPolygons = (year, typeId, sido) => loadJSON(`data/${year}/${typeId}/${sido}.json`);
