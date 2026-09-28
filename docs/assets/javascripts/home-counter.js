(function () {
  "use strict";

  var element = document.getElementById("home-views");
  var hosts = ["informaticainclasse.it", "insegnareinformatica.github.io"];
  var isHome = window.location.pathname === "/" ||
    window.location.pathname === "/index.html";
  if (!element || !isHome || hosts.indexOf(window.location.hostname) === -1) {
    return;
  }

  var endpoint = element.dataset.counterUrl;
  if (endpoint !== "https://lodi.ml/insegnareinformatica/counter.php") {
    return;
  }

  async function countHomeView() {
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 5000);
    try {
      var response = await fetch(endpoint, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        referrerPolicy: "no-referrer",
        cache: "no-store",
        signal: controller.signal
      });
      if (!response.ok) { throw new Error("Counter unavailable"); }
      var data = await response.json();
      if (!Number.isSafeInteger(data.value) || data.value < 0) {
        throw new Error("Invalid count");
      }
      element.textContent = data.value.toLocaleString("it-IT") +
        (data.value === 1 ? " visualizzazione" : " visualizzazioni");
      element.hidden = false;
    } catch (_) {
      // Il contatore non deve ostacolare la lettura se il server non risponde.
      element.hidden = true;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  countHomeView();
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) { countHomeView(); }
  });
}());
