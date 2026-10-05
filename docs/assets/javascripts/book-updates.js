(function () {
  "use strict";

  var section = document.getElementById("book-updates");
  if (!section) { return; }
  var result = document.getElementById("book-update-result");
  var title = document.getElementById("book-update-title");
  var message = document.getElementById("book-update-message");
  var copy = document.getElementById("book-copy-version");
  if (!result || !title || !message || !copy) { return; }

  var versionPattern = /^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;
  var versions = [];
  var available = section.dataset.catalogAvailable === "true";
  try {
    versions = JSON.parse(section.dataset.versions);
    if (!Array.isArray(versions) || !versions.every(function (version) {
      return typeof version === "string" && version.length <= 128 &&
        version.trim() === version && version.charAt(0) === "v" && versionPattern.test(version);
    }) || new Set(versions).size !== versions.length) {
      throw new Error("Invalid release catalog");
    }
  } catch (_) {
    available = false;
  }

  function readVersion(hash) {
    if (hash.length > 512) { return { invalid: true }; }
    var parameters = new URLSearchParams(hash.replace(/^#/, ""));
    var values = parameters.getAll("v");
    if (values.length === 0) { return {}; }
    if (values.length !== 1 || values[0].length > 128 ||
        values[0].trim() !== values[0] || !versionPattern.test(values[0])) {
      return { invalid: true };
    }
    return { version: "v" + values[0].replace(/^v/, "") };
  }

  function show(state, heading, description) {
    result.dataset.state = state;
    title.textContent = heading;
    message.textContent = description;
  }

  function update() {
    var incoming = readVersion(window.location.hash);
    var version = incoming.version;
    copy.hidden = !version;
    copy.textContent = version ? "La tua copia: " + version + "." : "";

    if (!available) {
      show("unavailable", "Verifica temporaneamente non disponibile",
        "Non è possibile verificare la tua copia in questo momento. Riprova più tardi.");
    } else if (versions.length === 0) {
      show("unpublished", "Nessuna versione consigliata disponibile",
        "Al momento non è disponibile una versione consigliata con cui confrontare la tua copia. Riprova dopo la pubblicazione della guida.");
    } else if (version === versions[0]) {
      show("current", "Hai l'ultima versione consigliata",
        "La tua copia corrisponde alla versione consigliata più recente della guida.");
    } else if (version && versions.indexOf(version) !== -1) {
      show("outdated", "È disponibile una versione più recente",
        "La tua copia è una versione consigliata precedente. Puoi scaricare qui sotto la versione " + versions[0] + ".");
    } else if (version || incoming.invalid) {
      show("unknown", "Versione non riconosciuta",
        "Il collegamento non identifica una versione consigliata pubblicata: potrebbe provenire da una bozza. Non possiamo confermare che la tua copia sia aggiornata. Puoi confrontarla con la versione indicata qui sotto.");
    } else {
      show("missing", "Confronta la tua copia",
        "Apri questa pagina dal pulsante nel PDF per verificare automaticamente la tua copia, oppure confronta il numero riportato nel documento con quello indicato qui sotto.");
    }
  }

  update();
  window.addEventListener("hashchange", update);
}());
