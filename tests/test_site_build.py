import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_book import book, release, site_check


ROOT = Path(__file__).resolve().parents[1]


class SiteBuildTests(unittest.TestCase):
    def build(self, root, catalog=None, counter=""):
        for directory in ("docs", "hooks", "overrides"):
            shutil.copytree(ROOT / directory, root / directory)
        shutil.copyfile(ROOT / "mkdocs.yml", root / "mkdocs.yml")
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

    def test_default_build_has_no_pdf_links_or_counter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root)
            self.assertEqual(home.count("disponibile prossimamente"), 2)
            self.assertNotIn("/releases/download/", home)
            self.assertNotIn('id="home-views"', home)
            self.assertNotIn("home-counter.js", home)
            self.assertFalse((root / "site/pdf").exists())

    def test_home_includes_resources_and_contacts_without_removed_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = self.build(root)
            self.assertIn('href="https://lodi.ml/infonin/"', home)
            self.assertIn('href="mailto:michael.lodi@unibo.it"', home)
            self.assertIn('href="https://www.youtube.com/playlist?list=PLKu-4ZHSUrc_LzPgufMbVN_hYd86JkSK1"', home)
            self.assertIn("Ulteriori risorse", home)
            self.assertIn("Autori, licenza e contatti", home)
            self.assertIn('class="video-link"', home)
            self.assertIn("Guarda la playlist su YouTube", home)
            self.assertNotIn(":material-play-circle:", home)
            self.assertNotIn("<iframe", home)
            self.assertNotIn("BOOK_DOWNLOADS", home)
            search = json.loads((root / "site/search/search_index.json").read_text())
            for page in ("risorse", "contatti"):
                self.assertFalse((root / "site" / page).exists())
                self.assertNotIn('href="' + page + '/"', home)
                self.assertFalse(any(entry["location"].startswith(page + "/")
                                     for entry in search["docs"]))

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
            for page in ("contenuti",):
                html = (root / "site" / page / "index.html").read_text()
                self.assertNotIn('id="home-views"', html)
                self.assertNotIn("home-counter.js", html)


if __name__ == "__main__":
    unittest.main()
