import fs from "node:fs";
import assert from "node:assert/strict";

const html = fs.readFileSync(new URL("../travel-selection.html", import.meta.url), "utf8");
const js = fs.readFileSync(new URL("../travel-selection.js", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../travel-selection.css", import.meta.url), "utf8");

for (const id of [
  "travel-departure",
  "travel-start",
  "travel-end",
  "travel-flexibility",
  "travel-adults",
  "travel-children",
  "travel-budget",
  "travel-documents",
  "travel-type",
  "travel-priority",
  "travel-demo-run",
  "travel-demo-results"
]) {
  assert.match(html, new RegExp(`id=["']${id}["']`), `missing control ${id}`);
  assert.match(js, new RegExp(`["']${id}["']`), `JavaScript does not reference ${id}`);
}

for (const primitive of [
  "fetch(",
  "XMLHttpRequest",
  "sendBeacon",
  "WebSocket",
  "localStorage",
  "sessionStorage",
  "document.cookie",
  "mailto:",
  "navigator.clipboard"
]) {
  assert.equal(js.includes(primitive), false, `unexpected side effect primitive: ${primitive}`);
}

assert.match(html, /Данные не отправляются/i);
assert.match(html, /синтетическ/i);
assert.match(js, /Ссылка закрыта production-gate/);
assert.match(css, /focus-visible/);
assert.match(css, /@media/);
assert.equal(/https?:\/\//.test(js), false, "selector JavaScript must not contain external URLs");

console.log("TRAVEL SELECTION SMOKE: PASS");
