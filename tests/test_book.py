import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


book = module("book", "scripts/book.py")
downloads = module("downloads", "hooks/book_downloads.py")
site_check = module("site_check", "scripts/check_site.py")


def release(tag="v1.0.0", count=15, **kwargs):
    return dict({
        "tag_name": tag, "draft": False, "prerelease": False,
        "published_at": "2026-09-26T12:00:00Z",
        "assets": [{"name": book.ASSET_NAME, "state": "uploaded",
                    "size": 100, "download_count": count}],
    }, **kwargs)


class PublicationTests(unittest.TestCase):
    def env(self, **overrides):
        return dict({
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main", "BOOK_MODE": "verifica",
            "GITHUB_REPOSITORY": book.REPOSITORY, "GITHUB_SHA": "a" * 40,
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
        }, **overrides)

    def test_manual_verification_requires_no_publication_approval(self):
        self.assertEqual(book.publication_plan(self.env())["mode"], "verifica")

    def test_auto_publication_is_disabled_by_default(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            book.publication_plan(self.env(GITHUB_EVENT_NAME="push"))

    def test_auto_publication_requires_exact_enable_value(self):
        for value in ("", "false", "True", "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                book.publication_plan(self.env(GITHUB_EVENT_NAME="push",
                                               BOOK_PUBLICATION_ENABLED=value))
        self.assertEqual(book.publication_plan(self.env(
            GITHUB_EVENT_NAME="push", BOOK_PUBLICATION_ENABLED="true"))["mode"], "in-lavorazione")

    def test_stable_requires_both_gate_and_explicit_confirmation(self):
        env = self.env(BOOK_MODE="consigliata", BOOK_VERSION="1.0.0",
                       BOOK_PUBLICATION_ENABLED="true")
        with self.assertRaisesRegex(ValueError, "confirmation"):
            book.publication_plan(env)
        env["CONFIRM_PUBLICATION"] = "true"
        self.assertEqual(book.publication_plan(env)["version"], "v1.0.0")

    def test_invalid_versions_and_other_branches_are_rejected(self):
        for version in ("", "1.0", "1.01.0", "1.0.0\ninjection", "1.0.0;touch x"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                book.publication_plan(self.env(BOOK_MODE="consigliata", BOOK_VERSION=version,
                                               BOOK_PUBLICATION_ENABLED="true",
                                               CONFIRM_PUBLICATION="true"))
        with self.assertRaises(ValueError):
            book.publication_plan(self.env(GITHUB_REF="refs/heads/preview"))

    def test_verification_can_never_call_publication_api(self):
        with patch.dict(os.environ, self.env(), clear=True), patch.object(book, "api") as api:
            with self.assertRaises(ValueError):
                book.publish()
            api.assert_not_called()

    def test_failed_upload_keeps_release_unpublished(self):
        env = self.env(BOOK_MODE="consigliata", BOOK_VERSION="1.0.0",
                       BOOK_PUBLICATION_ENABLED="true", CONFIRM_PUBLICATION="true")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dist").mkdir()
            (root / "dist" / book.ASSET_NAME).write_bytes(b"%PDF-test fixture")
            def response(path, **kwargs):
                if path.startswith("/git/ref/tags/"):
                    raise HTTPError(path, 404, "Not found", None, None)
                if path == "/releases":
                    return {"id": 123}
                if "/assets?" in path:
                    return {"state": "starter", "size": 0}
                self.fail("Unexpected publication step: " + path)
            with patch.object(book, "ROOT", root), patch.dict(os.environ, env, clear=True), \
                 patch.object(book, "all_releases", return_value=[]), \
                 patch.object(book, "api", side_effect=response) as api:
                with self.assertRaisesRegex(ValueError, "draft"):
                    book.publish()
                self.assertFalse(any(call.kwargs.get("method") == "PATCH"
                                     for call in api.call_args_list))

    def test_stale_working_build_is_not_published(self):
        env = self.env(GITHUB_EVENT_NAME="push", BOOK_PUBLICATION_ENABLED="true")
        with patch.dict(os.environ, env, clear=True), \
             patch.object(book, "api", return_value={"object": {"sha": "b" * 40}}) as api:
            book.publish()
            api.assert_called_once_with("/git/ref/heads/main")


class CatalogTests(unittest.TestCase):
    def test_only_ready_public_book_pdfs_are_counted(self):
        releases = [
            release(), release("v2.0.0", 999, draft=True),
            release("v3.0.0", 999, prerelease=True),
            release("other", 999), release("v4.0.0", 999, assets=[]),
            release("lavorazione-123-1", 7, prerelease=True),
        ]
        result = book.catalog(releases)
        self.assertEqual(result["total_downloads"], 22)
        self.assertEqual(len(result["stable"]), 1)
        self.assertEqual(len(result["working"]), 1)

    def test_old_working_builds_keep_their_counts(self):
        result = book.catalog([
            release("v1.0.0", 8), release("v1.1.0", 10),
            release("lavorazione-100-1", 3, prerelease=True,
                    published_at="2026-09-25T12:00:00Z"),
            release("lavorazione-200-1", 5, prerelease=True),
        ])
        self.assertEqual(result["stable"][0]["version"], "v1.1.0")
        self.assertEqual(result["working"][0]["version"], "lavorazione-200-1")
        self.assertEqual(result["total_downloads"], 26)

    def test_missing_release_is_not_a_zero_download_link(self):
        rendered = downloads.render(book.catalog([]))
        self.assertEqual(rendered.count("disponibile prossimamente"), 2)
        self.assertNotIn("<a ", rendered)
        self.assertNotIn("0 download", rendered)

    def test_archived_versions_and_counts_are_rendered(self):
        rendered = downloads.render(book.catalog([release("v1.0.0", 3), release("v1.1.0", 7)]))
        self.assertIn("Versioni consigliate precedenti", rendered)
        self.assertIn("10 download complessivi", rendered)
        self.assertIn("/releases/download/v1.1.0/", rendered)
        self.assertNotIn("<script", rendered)

    def test_catalog_rejects_bad_counts_and_links(self):
        data = release()
        data["assets"][0]["download_count"] = -1
        with self.assertRaises(ValueError):
            book.catalog([data])
        entry = book.catalog([release()])["stable"][0]
        entry["url"] = "https://example.com/private.pdf"
        with self.assertRaises(ValueError):
            downloads.link(entry, "Download")

    def test_pagination_collects_all_versions(self):
        with patch.object(book, "api", side_effect=[[release()] * 100, [release("v2.0.0")]]) as api:
            self.assertEqual(len(book.all_releases()), 101)
            self.assertEqual(api.call_count, 2)


class ArtifactTests(unittest.TestCase):
    def test_private_files_cannot_enter_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("index.html", "contenuti/index.html"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("<html></html>")
            site_check.check(root)
            (root / "book.pdf").write_bytes(b"%PDF-private")
            with self.assertRaises(ValueError):
                site_check.check(root)

    def test_external_scripts_and_fonts_are_rejected(self):
        for html in ('<script src="https://tracker.test/js"></script>',
                     '<link rel="stylesheet" href="https://fonts.test/font.css">',
                     '<iframe src="https://video.test/"></iframe>'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                site_check.PageCheck().feed(html)


if __name__ == "__main__":
    unittest.main()
