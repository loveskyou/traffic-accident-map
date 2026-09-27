export function createState(initial) {
  let current = { ...initial };
  const listeners = new Set();
  return {
    get: () => current,
    set(patch) {
      current = { ...current, ...patch };
      listeners.forEach((fn) => fn(current));
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
