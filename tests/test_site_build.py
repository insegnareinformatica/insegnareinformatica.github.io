from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

import yaml
from mkdocs.structure.files import File

from test_book import book, release, site_check


ROOT = Path(__file__).resolve().parents[1]


class ArticleLinks(HTMLParser):
    """Locate links by heading position, independently of editorial wording."""

    def __init__(self, html):
        super().__init__()
        self.in_article = False
        self.section = 0
        self.subsection = 0
        self.links = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.in_article = True
        if not self.in_article:
            return
        if tag == "h2":
            self.section += 1
            self.subsection = 0
        elif tag == "h3":
            self.subsection += 1
        elif tag == "a":
            self.links.append((dict(attrs), (self.section, self.subsection)))

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_article = False

    def handle_data(self, data):
        if self.in_article:
            self.text.append(data)


class RedirectTargets(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.targets = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("http-equiv") == "refresh":
            self.targets["refresh"] = attrs.get("content")
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.targets["canonical"] = attrs.get("href")
        elif tag == "a":
            self.targets["fallback"] = attrs.get("href")


class SiteBuildTests(unittest.TestCase):
    def build(self, root, catalog=None, counter="", home_markdown=None):
        for directory in ("docs", "hooks", "overrides"):
            shutil.copytree(ROOT / directory, root / directory)
        shutil.copyfile(ROOT / "mkdocs.yml", root / "mkdocs.yml")
        if home_markdown is not None:
            (root / "docs/index.md").write_text(home_markdown)
        if catalog is not None:
            (root / ".cache").mkdir()
            (root / ".cache/book-releases.json").write_text(json.dumps(catalog))
        result = subprocess.run(
            [sys.executable, "-m", "mkdocs", "build", "--strict"],
            cwd=root, env=dict(os.environ, HOME_COUNTER_URL=counter),
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        site_check.check(root / "site")
        return (root / "site/index.html").read_text()

    def test_default_build_has_no_book_download_links_or_counter(self):
        config = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=yaml.BaseLoader)
        pending_message = config["extra"].get("book_pending_message", "disponibile prossimamente")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root)
            self.assertIn(pending_message, " ".join(ArticleLinks(home).text))
            self.assertNotIn("Versione in lavorazione", home)
            self.assertNotIn("/releases/download/", home)
            self.assertNotIn('id="home-views"', home)
            self.assertNotIn("home-counter.js", home)
            self.assertFalse((root / "site/pdf").exists())

    def test_error_page_has_an_absolute_home_link_without_error_code_or_counter(self):
        config = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=yaml.BaseLoader)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build(root, counter="https://lodi.ml/insegnareinformatica/counter.php")
            html = (root / "site/404.html").read_text()
            content = ArticleLinks(html)
            self.assertTrue(content.text)
            self.assertNotRegex(" ".join(content.text), r"\b404\b")
            self.assertTrue(any(
                attrs.get("href") == config["site_url"]
                and "md-button" in attrs.get("class", "").split()
                for attrs, _ in content.links
            ), "The home button must work even from a nested missing URL")
            self.assertNotIn("home-counter.js", html)
            self.assertNotIn('id="home-views"', html)

    def test_configured_external_redirects_preserve_urls_without_home_counter(self):
        config = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=yaml.BaseLoader)
        redirects = next((plugin["redirects"].get("redirect_maps", {})
                          for plugin in config["plugins"] if "redirects" in plugin), {})
        directory_urls = config.get("use_directory_urls", "true").lower() == "true"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build(root, counter="https://lodi.ml/insegnareinformatica/counter.php")
            search = json.loads((root / "site/search/search_index.json").read_text())
            for source, target in redirects.items():
                if urlparse(target).scheme not in ("http", "https"):
                    continue
                with self.subTest(source=source, target=target):
                    page = File(source, "", "", directory_urls)
                    redirect = (root / "site" / page.dest_path).read_text()
                    self.assertEqual(RedirectTargets(redirect).targets, {
                        "refresh": "0; url=" + target,
                        "canonical": target,
                        "fallback": target,
                    })
                    self.assertNotIn("home-counter.js", redirect)
                    self.assertNotIn('id="home-views"', redirect)
                    self.assertFalse(any(entry["location"].startswith(page.url)
                                         for entry in search["docs"]))

    def assert_home_resources(self, home):
        links = ArticleLinks(home).links
        videos = [(attrs, position) for attrs, position in links
                  if "video-link" in attrs.get("class", "").split()]
        self.assertEqual(len(videos), 1, "Keep one external video preview")
        attrs, (section, subsection) = videos[0]
        playlist = urlparse(attrs["href"])
        self.assertEqual(playlist.scheme, "https")
        self.assertIn(playlist.hostname, ("youtube.com", "www.youtube.com"))
        self.assertEqual(playlist.path, "/playlist")
        self.assertTrue(parse_qs(playlist.query).get("list"))
        self.assertGreater(section, 0)
        self.assertGreater(subsection, 0, "Give the video its own subsection")
        self.assertTrue(any(
            other_section == section and other_subsection > 0
            and other_subsection != subsection
            and urlparse(other.get("href", "")).scheme == "https"
            for other, (other_section, other_subsection) in links
        ), "Keep the other teaching resources in a separate subsection")
        self.assertTrue(any(
            urlparse(attrs.get("href", "")).scheme == "mailto"
            and urlparse(attrs["href"]).path
            for attrs, _ in links
        ), "Keep an email contact")
        self.assertNotIn(":material-play-circle:", home)
        self.assertNotIn("<iframe", home)
        self.assertNotIn("BOOK_DOWNLOADS", home)

    def test_home_includes_resources_and_contacts_without_removed_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root)
            self.assert_home_resources(home)
            search = json.loads((root / "site/search/search_index.json").read_text())
            for page in ("risorse", "contatti"):
                self.assertFalse((root / "site" / page).exists())
                self.assertNotIn('href="' + page + '/"', home)
                self.assertFalse(any(entry["location"].startswith(page + "/")
                                     for entry in search["docs"]))

    def test_editorial_changes_do_not_break_resource_checks(self):
        markdown = """# Una guida per la scuola

<!-- BOOK_DOWNLOADS -->

## Approfondimenti

### Lezioni registrate

[Apri il corso](https://www.youtube.com/playlist?list=PLalternate){ .video-link }

### Altri percorsi

[Materiali aggiornati](https://example.org/materiali.pdf?download=1#page=3)

## Scrivici

[Contatto aggiornato](mailto:docenti@example.org)
"""
        with tempfile.TemporaryDirectory() as directory:
            home = self.build(Path(directory), home_markdown=markdown)
            self.assert_home_resources(home)

    def test_resource_checks_reject_merged_subsections(self):
        home = """<article><h2>Risorse</h2><h3>Video e materiali</h3>
<a class="video-link" href="https://www.youtube.com/playlist?list=PLexample">Video</a>
<a href="https://example.org/materiali/">Materiali</a>
<a href="mailto:docenti@example.org">Contatto</a></article>"""
        with self.assertRaisesRegex(AssertionError, "separate subsection"):
            self.assert_home_resources(home)

    def test_published_fixture_has_downloads_and_home_only_counter(self):
        data = book.catalog([
            release("v1.0.0", 12), release("v1.1.0", 20),
            release("lavorazione-123-1", 8, prerelease=True),
        ])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root, data, "https://lodi.ml/insegnareinformatica/counter.php")
            self.assertIn("40 download complessivi", home)
            self.assertIn("/releases/download/v1.1.0/", home)
            self.assertIn("/releases/download/lavorazione-123-1/", home)
            self.assertIn("Versioni consigliate precedenti", home)
            self.assertEqual(home.count('id="home-views"'), 1)
            self.assertEqual(home.count("home-counter.js"), 1)
            counter_position = home.index('id="home-views"')
            self.assertLess(home.index('<footer class="md-footer">'), counter_position)
            self.assertGreater(home.index("</footer>"), counter_position)
            self.assertLess(home.index("</article>"), counter_position)
            for page in ("contenuti",):
                html = (root / "site" / page / "index.html").read_text()
                self.assertNotIn('id="home-views"', html)
                self.assertNotIn("home-counter.js", html)

    def test_superseded_working_pdf_is_hidden_in_built_home_but_still_counted(self):
        data = book.catalog([
            release("v1.0.0", 12, target_commitish="a" * 40),
            release("v1.0.1", 20, target_commitish="b" * 40),
            release("lavorazione-123-1", 8, prerelease=True, target_commitish="b" * 40),
        ])
        with tempfile.TemporaryDirectory() as directory:
            home = self.build(Path(directory), data)
            self.assertIn("40 download complessivi", home)
            self.assertIn("/releases/download/v1.0.1/", home)
            self.assertIn("/releases/download/v1.0.0/", home)
            self.assertNotIn("Versione in lavorazione", home)
            self.assertNotIn("/releases/download/lavorazione-123-1/", home)
        self.assertEqual(len(data["working"]), 1)


if __name__ == "__main__":
    unittest.main()
