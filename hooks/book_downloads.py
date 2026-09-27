"""Render only public release metadata into the existing Markdown home page."""

from datetime import datetime
from html import escape
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def date_label(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y")


def number(value):
    if type(value) is not int or value < 0:
        raise ValueError("Invalid download count")
    return format(value, ",").replace(",", ".")


def link(entry, label):
    url = entry["url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(
        "/insegnareinformatica/insegnareinformatica.github.io/releases/download/"
    ):
        raise ValueError("Unexpected download URL")
    return '<a href="' + escape(url, quote=True) + '">' + escape(label) + "</a>"


def render(data):
    stable, working = data.get("stable", []), data.get("working", [])
    rows = ['<ul class="book-downloads">']
    for label, entries in (("Versione consigliata", stable), ("Versione in lavorazione", working)):
        if not entries:
            rows.append("<li><strong>" + label + "</strong> — disponibile prossimamente</li>")
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


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != "index.md":
        return markdown
    path = ROOT / ".cache/book-releases.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    if markdown.count("<!-- BOOK_DOWNLOADS -->") != 1:
        raise ValueError("The home page needs exactly one book downloads marker")
    return markdown.replace("<!-- BOOK_DOWNLOADS -->", render(data))
