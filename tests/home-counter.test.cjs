const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../docs/assets/javascripts/home-counter.js"), "utf8");
const endpoint = "https://lodi.ml/insegnareinformatica/counter.php";

async function run({ path = "/", host = "informaticainclasse.it", url = endpoint,
  data = { value: 815 }, failed = false } = {}) {
  const element = { dataset: { counterUrl: url }, hidden: true };
  const calls = [];
  const listeners = {};
  const context = {
    document: { getElementById: () => element },
    window: {
      location: { pathname: path, hostname: host },
      setTimeout: () => 1, clearTimeout: () => {},
      addEventListener: (name, listener) => { listeners[name] = listener; }
    },
    AbortController,
    fetch: async (...args) => {
      calls.push(args);
      if (failed) { throw new Error("offline"); }
      return { ok: true, json: async () => data };
    }
  };
  vm.runInNewContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  return { element, calls, listeners };
}

test("home makes one request, without credentials or referrer", async () => {
  const { element, calls, listeners } = await run();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], endpoint);
  assert.equal(calls[0][1].credentials, "omit");
  assert.equal(calls[0][1].referrerPolicy, "no-referrer");
  assert.equal(calls[0][1].cache, "no-store");
  assert.equal(element.textContent, "815 visualizzazioni della home");
  assert.equal(element.hidden, false);
  listeners.pageshow({ persisted: false });
  assert.equal(calls.length, 1);
});

test("other pages and local previews never increment the real counter", async () => {
  for (const path of ["/risorse/", "/contenuti/", "/contatti/"]) {
    assert.equal((await run({ path })).calls.length, 0);
  }
  for (const host of ["localhost", "127.0.0.1", "untrusted.test"]) {
    assert.equal((await run({ host })).calls.length, 0);
  }
  assert.equal((await run({ url: "" })).calls.length, 0);
  assert.equal((await run({ url: "https://other.test/count" })).calls.length, 0);
});

test("restoring the home from browser history counts a new opening", async () => {
  const { calls, listeners } = await run();
  listeners.pageshow({ persisted: true });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.length, 2);
});

test("unavailable or invalid counters stay hidden, without fake totals", async () => {
  assert.equal((await run({ failed: true })).element.hidden, true);
  for (const value of [-1, "815", null, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
    assert.equal((await run({ data: { value } })).element.hidden, true);
  }
  assert.equal((await run({ data: { value: 1 } })).element.textContent, "1 visualizzazione della home");
});
