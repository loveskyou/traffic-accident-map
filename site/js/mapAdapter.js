// 카카오맵과 대화하는 코드는 이 파일에만 둔다. 다른 지도로 바꿀 때 이 파일만 교체한다.
const SDK_URL = "https://dapi.kakao.com/v2/maps/sdk.js";

export function loadKakao(appKey, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("카카오맵 로드 시간 초과")), timeoutMs);
    const script = document.createElement("script");
    script.src = `${SDK_URL}?appkey=${encodeURIComponent(appKey)}&autoload=false&libraries=services,clusterer`;
    script.onerror = () => {
      clearTimeout(timer);
      reject(new Error("카카오맵 스크립트 로드 실패"));
    };
    script.onload = () => {
      if (!window.kakao || !window.kakao.maps) {
        clearTimeout(timer);
        reject(new Error("카카오맵 초기화 실패"));
        return;
      }
      window.kakao.maps.load(() => {
        clearTimeout(timer);
        resolve(window.kakao);
      });
    };
    document.head.appendChild(script);
  });
}

function circleImage(kakao, color, ring) {
  const size = ring ? 22 : 16;
  const half = size / 2;
  const stroke = ring ? 3 : 1.5;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><circle cx="${half}" cy="${half}" r="${half - stroke}" fill="${color}" fill-opacity="0.9" stroke="${ring ? "#111111" : "#ffffff"}" stroke-width="${stroke}"/></svg>`;
  return new kakao.maps.MarkerImage(
    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    new kakao.maps.Size(size, size),
    { offset: new kakao.maps.Point(half, half) },
  );
}

export function createMap(kakao, el) {
  const map = new kakao.maps.Map(el, { center: new kakao.maps.LatLng(36.35, 127.85), level: 13 });
  const clusterer = new kakao.maps.MarkerClusterer({ map, averageCenter: true, minLevel: 7 });
  const places = new kakao.maps.services.Places();
  const geocoder = new kakao.maps.services.Geocoder();
  const images = new Map();
  let polygons = [];

  const imageFor = (color, ring) => {
    const key = `${color}|${ring}`;
    if (!images.has(key)) images.set(key, circleImage(kakao, color, ring));
    return images.get(key);
  };

  return {
    showPoints(points, colorOf, onClick) {
      clusterer.clear();
      const markers = points.map((p) => {
        const marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(p.lat, p.lng),
          image: imageFor(colorOf(p), (p.streak ?? 0) >= 2),
          title: p.n,
        });
        kakao.maps.event.addListener(marker, "click", () => onClick(p));
        return marker;
      });
      clusterer.addMarkers(markers);
    },
    showPolygons(shapes) {
      polygons.forEach((polygon) => polygon.setMap(null));
      polygons = shapes.map(({ coords, color }) => new kakao.maps.Polygon({
        map,
        path: coords[0].map(([lng, lat]) => new kakao.maps.LatLng(lat, lng)),
        strokeWeight: 1, strokeColor: color, strokeOpacity: 0.8, fillColor: color, fillOpacity: 0.25,
      }));
    },
    getLevel: () => map.getLevel(),
    getBounds() {
      const bounds = map.getBounds();
      const sw = bounds.getSouthWest();
      const ne = bounds.getNorthEast();
      return { south: sw.getLat(), west: sw.getLng(), north: ne.getLat(), east: ne.getLng() };
    },
    onIdle(callback) {
      kakao.maps.event.addListener(map, "idle", callback);
    },
    moveTo(lat, lng, level) {
      map.setLevel(level);
      map.setCenter(new kakao.maps.LatLng(lat, lng));
    },
    searchPlaces(query) {
      return new Promise((resolve, reject) => {
        places.keywordSearch(query, (data, status) => {
          const Status = kakao.maps.services.Status;
          if (status === Status.OK) {
            resolve(data.slice(0, 10).map((d) => ({
              name: d.place_name, address: d.road_address_name || d.address_name, lat: Number(d.y), lng: Number(d.x),
            })));
          } else if (status === Status.ZERO_RESULT) {
            resolve([]);
          } else {
            reject(new Error("장소 검색 오류"));
          }
        });
      });
    },
    geocode(address) {
      return new Promise((resolve) => {
        geocoder.addressSearch(address, (data, status) => {
          const ok = status === kakao.maps.services.Status.OK && data[0];
          resolve(ok ? { lat: Number(data[0].y), lng: Number(data[0].x) } : null);
        });
      });
    },
  };
}
