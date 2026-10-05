"""Keep book sources and executable server files out of the Pages artifact."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class PageCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "iframe":
            raise ValueError("Unexpected embedded third-party content")
        if tag == "script" and attrs.get("src", "").startswith(("http:", "https:", "//")):
            raise ValueError("Unexpected external script")
        if tag == "link" and attrs.get("rel") in ("stylesheet", "preconnect"):
            if attrs.get("href", "").startswith(("http:", "https:", "//")):
                raise ValueError("Unexpected external stylesheet or connection")
        href = attrs.get("href", "")
        target = urlparse(href)
        if target.path.lower().endswith(".pdf"):
            # Linking to teaching resources does not copy their PDFs into Pages.
            if not (target.netloc and target.scheme in ("", "http", "https")):
                raise ValueError("Local PDF link is not allowed in the static site: " + href)


def check(root):
    forbidden = {".pdf", ".tex", ".bib", ".cls", ".sty", ".php", ".docx", ".sh", ".py"}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected symlink in the site: " + str(path))
        if path.is_file() and path.suffix.lower() in forbidden:
            raise ValueError("Private or server file in the site: " + str(path))
        if path.suffix == ".html":
            try:
                PageCheck().feed(path.read_text())
            except ValueError as error:
                raise ValueError(str(path.relative_to(root)) + ": " + str(error)) from error
    for required in ("index.html", "aggiornamenti/index.html"):
        if not (root / required).is_file():
            raise ValueError("Missing page: " + required)


if __name__ == "__main__":
    check(Path("site"))
    print("Pages artifact verified: no book files, PHP or external scripts.")
