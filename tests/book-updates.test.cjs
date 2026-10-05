const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = new vm.Script(fs.readFileSync(path.join(__dirname,
  "../docs/assets/javascripts/book-updates.js"), "utf8"));

function run(hash = "", options = {}) {
  const ids = ["book-updates", "book-update-result", "book-update-title",
    "book-update-message", "book-copy-version"];
  const elements = Object.fromEntries(ids.map(id => [id, {
    dataset: {}, textContent: "Static fallback", hidden: false,
    set innerHTML(_) { assert.fail("Version text must never be interpreted as HTML"); }
  }]));
  elements["book-updates"].dataset = {
    catalogAvailable: options.available === false ? "false" : "true",
    versions: options.json === undefined
      ? JSON.stringify(options.versions || ["v1.10.0", "v1.9.0", "v1.0.0"])
      : options.json
  };
  if (options.omit) { delete elements[options.omit]; }
  const events = {};
  const location = { hash };
  const context = {
    URLSearchParams,
    document: { getElementById: id => elements[id] || null },
    window: { location, addEventListener: (name, callback) => { events[name] = callback; } },
    fetch: () => assert.fail("The comparison must not send a network request")
  };
  script.runInNewContext(context);
  return {
    elements, events,
    get state() { return elements["book-update-result"].dataset.state; },
    get title() { return elements["book-update-title"].textContent; },
    get message() { return elements["book-update-message"].textContent; },
    get copy() { return elements["book-copy-version"]; },
    changeHash: value => { location.hash = value; events.hashchange(); }
  };
}

test("recognizes the current published version with either supported prefix", () => {
  for (const value of ["v1.10.0", "1.10.0", "v1%2E10%2E0"]) {
    const page = run("#v=" + value);
    assert.equal(page.state, "current");
    assert.match(page.title, /ultima versione consigliata/);
    assert.equal(page.copy.textContent, "La tua copia: v1.10.0.");
    assert.equal(page.copy.hidden, false);
  }
});

test("known older copies point to the latest stable version, not a lexical maximum", () => {
  const page = run("#v=v1.9.0");
  assert.equal(page.state, "outdated");
  assert.match(page.message, /v1\.10\.0/);
});

test("unpublished version numbers are never classified as current or previous", () => {
  for (const value of ["v0.9.9", "v1.8.0", "v2.0.0", "v99999999999999999999.0.0"]) {
    const page = run("#v=" + value);
    assert.equal(page.state, "unknown");
    assert.match(page.message, /Non possiamo confermare/);
  }
});

test("empty catalog and unavailable metadata do not claim that a copy is up to date", () => {
  for (const hash of ["", "#v=v0.9.9", "#v=invalid"]) {
    assert.equal(run(hash, { versions: [] }).state, "unpublished");
    assert.equal(run(hash, { available: false }).state, "unavailable");
  }
});

test("corrupt or noncanonical catalog metadata fails closed", () => {
  for (const json of ["not json", "null", "{}", '[null]', '[12]',
    '["1.0.0"]', '["v1.00.0"]', '["v1.0.0\\n"]', '["v1.0.0", "v1.0.0"]',
    '["lavorazione-123-1"]', '["v1.0.0-rc.1"]']) {
    assert.equal(run("#v=v1.0.0", { json }).state, "unavailable", json);
  }
});

test("a link without a version invites a manual comparison", () => {
  for (const hash of ["", "#", "#unrelated-heading", "#other=value"]) {
    const page = run(hash);
    assert.equal(page.state, "missing");
    assert.equal(page.copy.hidden, true);
    assert.match(page.message, /confronta il numero/);
  }
});

test("invalid, ambiguous and draft identifiers are unrecognized and not echoed", () => {
  const invalid = ["#v=", "#v=v1.10.0&v=v1.0.0", "#v=v1.10.0&v=v1.10.0",
    "#v=v1.10", "#v=v01.10.0", "#v=v1.010.0", "#v=v1.10.00", "#v=V1.10.0",
    "#v=v1.10.0%0A", "#v=%20v1.10.0", "#v=v1.10.0+", "#v=%E0%A4%A",
    "#v=in%20lavorazione%20abcdef012345", "#v=lavorazione-123-1", "#v=v1.10.0-rc.1",
    "#v=" + "1".repeat(600), "#v=" + encodeURIComponent('<img src=x onerror="alert(1)">')];
  for (const hash of invalid) {
    const page = run(hash);
    assert.equal(page.state, "unknown", hash);
    assert.equal(page.copy.hidden, true, hash);
    assert.equal(page.copy.textContent, "", hash);
  }
});

test("changing the fragment refreshes the result without reloading", () => {
  const page = run("#v=v1.10.0");
  page.changeHash("#v=v1.0.0");
  assert.equal(page.state, "outdated");
  page.changeHash("#v=invalid");
  assert.equal(page.state, "unknown");
  assert.equal(page.copy.hidden, true);
  page.changeHash("");
  assert.equal(page.state, "missing");
});

test("the script is inert outside the updates page or when its markup is incomplete", () => {
  for (const omit of ["book-updates", "book-update-title"]) {
    const page = run("#v=v1.10.0", { omit });
    assert.deepEqual(page.events, {});
  }
});
