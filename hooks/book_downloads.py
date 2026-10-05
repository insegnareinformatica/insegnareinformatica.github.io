"""Render public release metadata into the home and book updates pages."""

from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from mkdocs.utils import get_relative_url


ROOT = Path(__file__).resolve().parents[1]
STABLE_VERSION = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def date_label(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y")


def number(value):
    if type(value) is not int or value < 0:
        raise ValueError("Invalid download count")
    return format(value, ",").replace(",", ".")


def link(entry, label, css_class=None):
    url = entry["url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(
        "/insegnareinformatica/insegnareinformatica.github.io/releases/download/"
    ):
        raise ValueError("Unexpected download URL")
    classes = ' class="' + escape(css_class, quote=True) + '"' if css_class else ""
    return '<a href="' + escape(url, quote=True) + '"' + classes + '>' + escape(label) + "</a>"


def render(data, pending_message="disponibile prossimamente"):
    stable, working = data.get("stable", []), data.get("working", [])
    rows = ['<ul class="book-downloads">']
    for label, entries in (("Versione consigliata", stable), ("Versione in lavorazione", working)):
        if entries is working and stable and data.get("working_superseded") is True:
            continue
        if not entries:
            if entries is stable:
                rows.append("<li><strong>" + label + "</strong> — " + escape(pending_message) + "</li>")
            continue
        entry = entries[0]
        details = ("Versione " + escape(entry["version"].removeprefix("v")) + " · ") if entries is stable else ""
        details += date_label(entry["published_at"]) + " · " + number(entry["downloads"]) + " download"
        rows.append("<li>" + link(entry, label + " — scarica il PDF") +
                    "<small>" + details + "</small></li>")
    rows.append("</ul>")
    if stable or working:
        rows.append("<p><small>" + number(data["total_downloads"]) +
                    " download complessivi delle versioni pubblicate. Conteggi aggiornati al " +
                    date_label(data["updated_at"]) + ".</small></p>")
    if len(stable) > 1:
        rows.append("<details><summary>Versioni consigliate precedenti</summary><ul>")
        for entry in stable[1:]:
            rows.append("<li>" + link(entry, "Versione " + entry["version"].removeprefix("v")) +
                        " · " + date_label(entry["published_at"]) + " · " +
                        number(entry["downloads"]) + " download</li>")
        rows.append("</ul></details>")
    return "\n".join(rows)


def render_updates(data, catalog_available=True):
    stable = sorted(
        (entry for entry in data.get("stable", [])
         if STABLE_VERSION.fullmatch(entry["version"])),
        key=lambda entry: tuple(map(int, STABLE_VERSION.fullmatch(entry["version"]).groups())),
        reverse=True,
    ) if catalog_available else []
    versions = escape(json.dumps([entry["version"] for entry in stable]), quote=True)
    available = "true" if catalog_available else "false"
    if not catalog_available:
        title = "Informazioni temporaneamente non disponibili"
        message = "Riprova più tardi per verificare se sono disponibili aggiornamenti della guida."
    elif not stable:
        title = "Nessuna versione consigliata disponibile"
        message = ("Al momento non è disponibile una versione consigliata con cui confrontare "
                   "la tua copia. Riprova dopo la pubblicazione della guida.")
    else:
        title = "Verifica la versione della tua guida"
        message = ("Confronta il numero di versione riportato nel tuo PDF con quello "
                   "dell'ultima versione consigliata, indicato qui sotto.")
    rows = [
        '<section id="book-updates" class="book-updates" data-versions="' + versions +
        '" data-catalog-available="' + available + '">',
        '<div id="book-update-result" class="book-update-result" role="status" '
        'aria-live="polite" aria-atomic="true">',
        '<h2 id="book-update-title">' + escape(title) + '</h2>',
        '<p id="book-update-message">' + escape(message) + '</p>',
        '<p id="book-copy-version" hidden></p>',
        '</div>',
    ]
    if stable:
        latest = stable[0]
        rows.extend([
            '<h2>Ultima versione consigliata</h2>',
            '<p><strong>Versione ' + escape(latest["version"].removeprefix("v")) +
            '</strong> · ' + date_label(latest["published_at"]) + '</p>',
            '<p>' + link(latest, "Scarica la versione consigliata",
                         css_class="md-button md-button--primary") + '</p>',
            '<noscript><p>Per verificare gli aggiornamenti, confronta manualmente il numero '
            'di versione nel tuo PDF con quello indicato in questa pagina.</p></noscript>',
        ])
        if data.get("updated_at"):
            rows.append('<p><small>Informazioni aggiornate al ' + date_label(data["updated_at"]) +
                        '.</small></p>')
    rows.append('</section>')
    return "\n".join(rows)


def on_page_markdown(markdown, page, config, files):
    source = page.file.src_uri
    if source not in ("index.md", "aggiornamenti.md"):
        return markdown
    path = ROOT / ".cache/book-releases.json"
    catalog_available = path.exists()
    data = json.loads(path.read_text()) if catalog_available else {}
    if source == "aggiornamenti.md":
        if markdown.count("<!-- BOOK_UPDATES -->") != 1:
            raise ValueError("The updates page needs exactly one book updates marker")
        script = get_relative_url("assets/javascripts/book-updates.js", page.url)
        content = render_updates(data, catalog_available)
        content += '\n<script src="' + escape(script, quote=True) + '" defer></script>'
        return markdown.replace("<!-- BOOK_UPDATES -->", content)
    if markdown.count("<!-- BOOK_DOWNLOADS -->") != 1:
        raise ValueError("The home page needs exactly one book downloads marker")
    pending_message = config.get("extra", {}).get("book_pending_message", "disponibile prossimamente")
    return markdown.replace("<!-- BOOK_DOWNLOADS -->", render(data, pending_message))
