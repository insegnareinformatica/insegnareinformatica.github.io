"""Verify the public updates page using synthetic releases and temporary builds."""

from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_book import book, downloads, release
import test_site_build


class UpdatesContent(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = {}
        self.links = []
        self.scripts = []
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if "id" in attrs:
            self.ids[attrs["id"]] = (tag, attrs)
        if tag == "a":
            self.links.append(attrs)
        elif tag == "script":
            self.scripts.append(attrs)


class UpdatesRenderingTests(unittest.TestCase):
    def test_stable_versions_use_numeric_order_and_never_include_working_releases(self):
        data = book.catalog([
            release("v1.2.0"), release("v1.10.0"), release("v2.0.0"),
            release("lavorazione-123-1", prerelease=True),
        ])
        data["stable"].reverse()
        # Even a misplaced non-stable entry cannot become a recommended PDF.
        data["stable"].extend(data["working"])
        rendered = downloads.render_updates(data)
        content = UpdatesContent(rendered)
        tag, attrs = content.ids["book-updates"]
        self.assertEqual(tag, "section")
        self.assertEqual(attrs["class"], "book-updates")
        self.assertEqual(attrs["data-catalog-available"], "true")
        self.assertEqual(json.loads(attrs["data-versions"]), ["v2.0.0", "v1.10.0", "v1.2.0"])
        self.assertIn('&quot;v2.0.0&quot;', rendered)
        self.assertNotIn("lavorazione", rendered)
        self.assertNotIn("total_downloads", rendered)
        self.assertEqual(len(content.links), 1)
        self.assertEqual(content.links[0]["href"], data["stable"][2]["url"])
        self.assertEqual(content.links[0]["class"], "md-button md-button--primary")
        self.assertIn("26/09/2026", rendered)
        self.assertIn("noscript", content.tags)
        self.assertIn("confronta manualmente", rendered)

    def test_result_is_an_accessible_status_and_copy_version_starts_hidden(self):
        content = UpdatesContent(downloads.render_updates(book.catalog([release()])))
        tag, result = content.ids["book-update-result"]
        self.assertEqual(tag, "div")
        self.assertEqual(result["class"], "book-update-result")
        self.assertEqual(result["role"], "status")
        self.assertEqual(result["aria-live"], "polite")
        self.assertEqual(result["aria-atomic"], "true")
        self.assertEqual(content.ids["book-update-title"][0], "h2")
        self.assertEqual(content.ids["book-update-message"][0], "p")
        self.assertEqual(content.ids["book-copy-version"][0], "p")
        self.assertIn("hidden", content.ids["book-copy-version"][1])

    def test_unavailable_catalog_and_empty_catalog_have_distinct_fallbacks(self):
        for available, data, message in (
            (False, {}, "Informazioni temporaneamente non disponibili"),
            (True, book.catalog([]), "Nessuna versione consigliata disponibile"),
            (True, book.catalog([release("lavorazione-123-1", prerelease=True)]),
             "Nessuna versione consigliata disponibile"),
        ):
            with self.subTest(available=available, data=data):
                rendered = downloads.render_updates(data, available)
                content = UpdatesContent(rendered)
                attrs = content.ids["book-updates"][1]
                self.assertEqual(attrs["data-catalog-available"], str(available).lower())
                self.assertEqual(json.loads(attrs["data-versions"]), [])
                self.assertIn(message, rendered)
                self.assertEqual(content.links, [])
                self.assertNotIn("/releases/download/", rendered)
                self.assertNotIn("noscript", content.tags)

    def test_download_link_is_validated_and_escaped(self):
        data = book.catalog([release()])
        entry = data["stable"][0]
        url = entry["url"] + '?name="<example>"&download=1'
        entry["url"] = url
        rendered = downloads.render_updates(data)
        self.assertEqual(UpdatesContent(rendered).links[0]["href"], url)
        self.assertIn('&quot;&lt;example&gt;&quot;&amp;download=1', rendered)
        self.assertNotIn("<example>", rendered)
        for url in ("javascript:alert(1)", "https://example.test/guide.pdf",
                    "https://github.com/other/repository/releases/download/v1.0.0/guide.pdf"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Unexpected download URL"):
                entry["url"] = url
                downloads.render_updates(data)

    def test_link_label_and_optional_class_cannot_insert_markup(self):
        entry = book.catalog([release()])["stable"][0]
        rendered = downloads.link(entry, '<Download & "PDF">', 'button" onclick="bad')
        content = UpdatesContent(rendered)
        self.assertEqual(content.tags, ["a"])
        self.assertNotIn("onclick", content.links[0])
        self.assertEqual(content.links[0]["class"], 'button" onclick="bad')
        self.assertIn('&lt;Download &amp; &quot;PDF&quot;&gt;', rendered)

    def page(self, source="aggiornamenti.md", url="aggiornamenti/"):
        return SimpleNamespace(file=SimpleNamespace(src_uri=source), url=url)

    def test_hook_reads_cache_and_adds_only_page_relative_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(downloads, "ROOT", root):
                missing = downloads.on_page_markdown("<!-- BOOK_UPDATES -->", self.page(), {}, [])
                self.assertEqual(UpdatesContent(missing).ids["book-updates"][1]["data-catalog-available"],
                                 "false")
                (root / ".cache").mkdir()
                (root / ".cache/book-releases.json").write_text(json.dumps(book.catalog([release()])))
                for url, script in (("aggiornamenti/", "../assets/javascripts/book-updates.js"),
                                    ("aggiornamenti.html", "assets/javascripts/book-updates.js")):
                    with self.subTest(url=url):
                        rendered = downloads.on_page_markdown("<!-- BOOK_UPDATES -->", self.page(url=url), {}, [])
                        content = UpdatesContent(rendered)
                        self.assertEqual(content.ids["book-updates"][1]["data-catalog-available"], "true")
                        self.assertEqual(content.scripts, [{"src": script, "defer": None}])
                        self.assertNotIn("BOOK_UPDATES", rendered)
                home = downloads.on_page_markdown("<!-- BOOK_DOWNLOADS -->",
                                                  self.page("index.md", ""), {}, [])
                self.assertEqual(home, downloads.render(book.catalog([release()])))
                self.assertNotIn("book-updates.js", home)
                other = downloads.on_page_markdown("Unchanged", self.page("contenuti.md"), {}, [])
                self.assertEqual(other, "Unchanged")

    def test_updates_page_requires_exactly_one_marker(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(downloads, "ROOT", Path(directory)):
            for markdown in ("No marker", "<!-- BOOK_UPDATES -->\n<!-- BOOK_UPDATES -->"):
                with self.subTest(markdown=markdown), self.assertRaisesRegex(ValueError, "exactly one"):
                    downloads.on_page_markdown(markdown, self.page(), {}, [])


class UpdatesBuildTests(unittest.TestCase):
    def build(self, root, catalog=None):
        return test_site_build.SiteBuildTests.build(self, root, catalog=catalog)

    def test_default_build_has_useful_unavailable_fallback_and_page_only_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root)
            updates = (root / "site/aggiornamenti/index.html").read_text()
            content = UpdatesContent(updates)
            self.assertEqual(content.ids["book-updates"][1]["data-catalog-available"], "false")
            self.assertIn("Informazioni temporaneamente non disponibili", updates)
            self.assertNotIn("/releases/download/", updates)
            self.assertEqual(updates.count("book-updates.js"), 1)
            self.assertTrue((root / "site/assets/javascripts/book-updates.js").is_file())
            self.assertNotIn("book-updates.js", home)
            self.assertNotIn("book-updates.js", (root / "site/contenuti/index.html").read_text())

    def test_fixture_build_recommends_only_latest_stable_and_preserves_home(self):
        data = book.catalog([
            release("v1.2.0"), release("v1.10.0"),
            release("lavorazione-123-1", prerelease=True),
        ])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root, data)
            updates = (root / "site/aggiornamenti/index.html").read_text()
            content = UpdatesContent(updates)
            self.assertEqual(json.loads(content.ids["book-updates"][1]["data-versions"]),
                             ["v1.10.0", "v1.2.0"])
            download_links = [attrs for attrs in content.links
                              if "/releases/download/" in attrs.get("href", "")]
            self.assertEqual(len(download_links), 1)
            self.assertEqual(download_links[0]["href"], data["stable"][0]["url"])
            self.assertNotIn("lavorazione-123-1", updates)
            self.assertIn("Versione 1.10.0", updates)
            self.assertIn("confronta manualmente", updates)
            self.assertIn("/releases/download/lavorazione-123-1/", home)
            self.assertIn("/releases/download/v1.2.0/", home)


if __name__ == "__main__":
    unittest.main()
