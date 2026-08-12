import assert from "node:assert/strict";

class FakeElement {
  constructor() {
    this.hidden = false;
    this.textContent = "";
    this.listeners = new Map();
  }
  addEventListener(name, callback) {
    this.listeners.set(name, callback);
  }
  dispatch(name) {
    this.listeners.get(name)?.({ preventDefault() {} });
  }
  focus() {}
  scrollIntoView() {}
}

class FakeForm extends FakeElement {
  constructor() {
    super();
    this.values = new Map();
  }
  checkValidity() { return true; }
  reportValidity() {}
  reset() { this.values.clear(); }
  querySelector() { return new FakeElement(); }
}

const form = new FakeForm();
const warning = new FakeElement();
warning.hidden = true;
const status = new FakeElement();
const preview = new FakeElement();
preview.hidden = true;
const previewText = new FakeElement();
const clearButton = new FakeElement();
const elements = new Map([
  ["#service-request-form", form],
  ["#emergency-warning", warning],
  ["#form-status", status],
  ["#request-preview", preview],
  ["#request-preview-text", previewText],
  ["#clear-preview", clearButton],
]);

globalThis.document = { querySelector: (selector) => elements.get(selector) ?? null };
globalThis.FormData = class {
  constructor(target) { this.values = target.values; }
  get(name) { return this.values.get(name) ?? null; }
};

await import("../service-network.js");

for (const [key, value] of Object.entries({
  city: "Саратов",
  district: "Ленинский",
  category: "Ремонт котлов",
  equipment: "Бытовой котёл",
  problem: "Котёл показывает ошибку E01 и не запускается",
  urgency: "Сегодня",
  share_mode: "sequential",
  contact: "+79990000000",
})) form.values.set(key, value);
form.dispatch("submit");
assert.equal(preview.hidden, false);
assert.match(previewText.textContent, /Статус: НЕ ОТПРАВЛЕНО/);
assert.doesNotMatch(previewText.textContent, /\+79990000000/);
assert.match(status.textContent, /данные не сохранены/);

form.values.set("problem", "Сильный запах газа и был хлопок");
form.dispatch("submit");
assert.equal(warning.hidden, false);
assert.equal(preview.hidden, true);
assert.match(status.textContent, /аварийных признаков/);

console.log("SERVICE NETWORK JS: PASS (local preview, masked contact, emergency block)");
