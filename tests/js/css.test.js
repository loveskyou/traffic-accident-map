import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(process.env.CSS_FILE || new URL("../../site/css/style.css", import.meta.url), "utf8");

test("every dvh size has a vh fallback just before it (older mobile browsers)", () => {
  const uses = [...css.matchAll(/((?:max-)?height):\s*(\d+)dvh/g)];
  assert.ok(uses.length > 0);
  for (const [, prop, n] of uses) {
    assert.ok(css.includes(`${prop}: ${n}vh; ${prop}: ${n}dvh`), `${prop}: ${n}dvh has no vh fallback`);
  }
});
