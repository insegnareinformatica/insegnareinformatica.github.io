"""Link checks use synthetic books in temporary directories, never guide sources."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aggiorna-link.py"
spec = importlib.util.spec_from_file_location("book_links", SCRIPT)
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)

ALPHA = "https://example.test/a"
BETA = "https://example.test/b"
REDIRECTS = {"alpha": ALPHA, "beta": BETA}


class BookLinksTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="book-links-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.book = self.base / "book"
        self.book.mkdir()
        self.registry = self.base / "mkdocs.yml"
        self.write_registry()

    def write_registry(self, maps=None, extra=""):
        maps = REDIRECTS if maps is None else maps
        content = "plugins:\n  - redirects:\n      redirect_maps:\n"
        content += "".join(f"        '{alias}.md': '{target}'\n"
                           for alias, target in maps.items())
        self.registry.write_text(content + extra, encoding="utf-8")

    def make_book(self, source="main.tex"):
        (self.book / source).write_text(
            "\\input{cap1}\n\\input{sitografia.tex}\n", encoding="utf-8")
        (self.book / "cap1.tex").write_text(
            "\\linkbreve{alpha}\n", encoding="utf-8")
        self.write_bib(f"url = {{{ALPHA}}}, usera = {{alpha}}")

    def write_bib(self, fields):
        (self.book / "references.bib").write_text(
            "@online{fixture, title = {Synthetic resource}, " + fields + "}\n",
            encoding="utf-8")

    def cli(self, *args, script=SCRIPT, cwd=None):
        return subprocess.run(
            [sys.executable, str(script), "--root", str(self.book),
             "--redirects", str(self.registry), *args],
            cwd=cwd or self.base, text=True, capture_output=True, timeout=20)

    def snapshot(self):
        return {path.relative_to(self.base).as_posix(): path.read_bytes()
                for path in self.base.rglob("*") if path.is_file()}

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mkdocs_tags_outside_redirects_are_not_executed(self):
        marker = self.base / "tag-was-executed"
        self.write_registry(extra=(
            "site_name: !ENV [SITE_NAME, Synthetic]\n"
            "markdown_extensions:\n"
            "  - pymdownx.superfences:\n"
            "      custom_fences:\n"
            "        - name: synthetic\n"
            "          format: !!python/name:missing_module.missing_function\n"
            "extra: !!python/object/apply:builtins.open\n"
            f"  - '{marker}'\n"
            "  - w\n"))
        self.assertEqual(links.load_redirects(self.registry), REDIRECTS)
        self.assertFalse(marker.exists())

    def test_redirect_plugin_mapping_form_is_supported(self):
        self.registry.write_text(
            "plugins:\n  search: {}\n  redirects:\n    redirect_maps:\n"
            f"      alpha.md: '{ALPHA}'\n", encoding="utf-8")
        self.assertEqual(links.load_redirects(self.registry), {"alpha": ALPHA})

    def test_invalid_redirects_are_rejected(self):
        prefix = "plugins:\n  - redirects:\n      redirect_maps:\n"
        cases = {
            "duplicate_yaml_key": f"        alpha.md: '{ALPHA}'\n        alpha.md: '{BETA}'\n",
            "case_collision": f"        alpha.md: '{ALPHA}'\n        Alpha.md: '{BETA}'\n",
            "duplicate_target": f"        alpha.md: '{ALPHA}'\n        beta.md: '{ALPHA}'\n",
            "relative_url": "        alpha.md: '/local/page'\n",
            "non_http_url": "        alpha.md: 'ftp://example.test/file'\n",
            "invalid_slug": f"        nested/alpha.md: '{ALPHA}'\n",
            "tagged_destination": "        alpha.md: !ENV [RESOURCE_URL, fallback]\n",
            "empty_map": "        {}\n",
        }
        for name, maps in cases.items():
            with self.subTest(name=name):
                self.registry.write_text(prefix + maps, encoding="utf-8")
                with self.assertRaises(links.Invalid):
                    links.load_redirects(self.registry)
        self.write_registry()
        with self.registry.open("a", encoding="utf-8") as stream:
            stream.write("plugins: []\n")
        with self.assertRaises(links.Invalid):
            links.load_redirects(self.registry)

    def test_bibliography_alias_and_original_url_must_agree(self):
        self.make_book()
        cases = {
            "missing_usera": f"url = {{{ALPHA}}}",
            "unknown_usera": f"url = {{{ALPHA}}}, usera = {{missing}}",
            "wrong_usera": f"url = {{{ALPHA}}}, usera = {{beta}}",
            "unregistered_destination": "url = {https://example.test/unlisted}, usera = {alpha}",
            "missing_url": "usera = {alpha}",
            "invalid_url": "url = {mailto:synthetic@example.test}",
        }
        for name, fields in cases.items():
            with self.subTest(name=name):
                self.write_bib(fields)
                errors = links.validate_sources(self.book, REDIRECTS)
                self.assertTrue(errors)
                self.assertTrue(any("references.bib" in error for error in errors))
        self.write_bib("url = {https://example.test/unlisted}")
        self.assertEqual(links.validate_sources(self.book, REDIRECTS), [])

    def test_percent_encoded_bib_url_is_not_a_comment(self):
        target = "https://example.test/a%20b?q=x&lang=it#part"
        self.make_book()
        self.write_bib(f"url = {{{target}}}, usera = {{alpha}}")
        self.assertEqual(links.validate_sources(self.book, {"alpha": target}), [])
        self.write_bib("url = {https://example.test/a%20other}, usera = {alpha}")
        self.assertTrue(links.validate_sources(self.book, {"alpha": target}))

    def test_unknown_alias_in_included_file_and_chapter_is_reported(self):
        self.make_book()
        (self.book / "nested").mkdir()
        (self.book / "cap1.tex").write_text(
            "\\input{nested/exercise}\n", encoding="utf-8")
        (self.book / "nested" / "exercise.tex").write_text(
            "Synthetic exercise.\n\\hrefbreve{missing}{Resource}\n", encoding="utf-8")
        (self.book / "cap9.tex").write_text(
            "\\linkbreve{alsoMissing}\n", encoding="utf-8")
        errors = links.validate_sources(self.book, REDIRECTS)
        self.assertTrue(any("nested/exercise.tex:2:" in error and "missing" in error
                            for error in errors), errors)
        self.assertTrue(any("cap9.tex" in error and "alsoMissing" in error
                            for error in errors), errors)

    def test_missing_and_external_inputs_fail(self):
        self.make_book()
        (self.book / "main.tex").write_text("\\input{absent}\n", encoding="utf-8")
        with self.assertRaises(OSError):
            links.source_paths(self.book)
        (self.base / "outside.tex").write_text("Outside fixture.\n", encoding="utf-8")
        (self.book / "main.tex").write_text("\\input{../outside}\n", encoding="utf-8")
        with self.assertRaises(links.Invalid):
            links.source_paths(self.book)

    def test_original_macros_accept_escaped_urls_but_labels_cannot_hide_urls(self):
        self.make_book()
        (self.book / "cap1.tex").write_text(
            r"\urloriginale{https://example.test/a\_b?q=one\&x=two\#part\%20end}" "\n"
            r"\hreforiginale{https://example.test/other}{A synthetic label}" "\n"
            r"% \linkbreve{missing} https://comment.example.test/" "\n",
            encoding="utf-8")
        self.assertEqual(links.validate_sources(self.book, REDIRECTS), [])
        for text in (
                r"\hreforiginale{https://example.test/valid}{https://example.test/hidden}",
                r"\urloriginale{file:///private/example}",
                r"\url{https://example.test/legacy}"):
            with self.subTest(text=text):
                (self.book / "cap1.tex").write_text(text + "\n", encoding="utf-8")
                self.assertTrue(links.validate_sources(self.book, REDIRECTS))

    def test_renderer_preserves_targets_and_is_independent_of_map_order(self):
        target = "https://example.test/a%20b?q=one&x=two#part"
        forward = {"beta": BETA, "alpha": target}
        rendered = links.render(forward)
        self.assertEqual(rendered, links.render(dict(reversed(list(forward.items())))))
        self.assertLess(rendered.index(r"\linkbreve{alpha}"),
                        rendered.index(r"\linkbreve{beta}"))
        self.assertIn(r"\url{https://example.test/a\%20b?q=one&x=two\#part}", rendered)
        self.assertIn(r"\appto\UrlNoBreaks{\do\:}", rendered)
        self.assertNotIn(r"\input{sitografia-elenco", rendered)

    def test_generate_changes_only_sitography_and_check_never_writes(self):
        self.make_book()
        before = self.snapshot()
        self.assert_success(self.cli())
        output = self.book / "sitografia.tex"
        self.assertEqual(output.read_text(encoding="utf-8"), links.render(REDIRECTS))
        after = self.snapshot()
        self.assertEqual({name: value for name, value in after.items()
                          if name != "book/sitografia.tex"}, before)
        self.assert_success(self.cli("--check"))
        self.assertEqual(self.snapshot(), after)
        output.write_text("Stale generated fixture.\n", encoding="utf-8")
        stale = self.snapshot()
        self.assert_failure(self.cli("--check"))
        self.assertEqual(self.snapshot(), stale)
        output.unlink()
        missing = self.snapshot()
        self.assert_failure(self.cli("--check"))
        self.assertEqual(self.snapshot(), missing)

    def test_invalid_sources_cannot_overwrite_existing_sitography(self):
        self.make_book()
        (self.book / "sitografia.tex").write_text("Existing fixture.\n", encoding="utf-8")
        (self.book / "cap1.tex").write_text("\\linkbreve{missing}\n", encoding="utf-8")
        before = self.snapshot()
        self.assert_failure(self.cli())
        self.assertEqual(self.snapshot(), before)

    def test_missing_book_is_skipped_only_with_explicit_option(self):
        (self.book / "README.md").write_text("Book not supplied.\n", encoding="utf-8")
        before = self.snapshot()
        self.assert_failure(self.cli())
        self.assert_success(self.cli("--allow-missing-book", "--check"))
        self.assertEqual(self.snapshot(), before)
        (self.book / "README.md").unlink()
        self.book.rmdir()
        self.assert_success(self.cli("--allow-missing-book"))
        self.assertFalse(self.book.exists())

    def test_invalid_registry_fails_even_when_book_is_absent(self):
        self.registry.write_text(
            "plugins:\n  - redirects:\n      redirect_maps:\n"
            "        alpha.md: 'not-an-absolute-url'\n", encoding="utf-8")
        before = self.snapshot()
        self.assert_failure(self.cli("--allow-missing-book"))
        self.assertEqual(self.snapshot(), before)

    def test_partial_book_cannot_be_silently_skipped(self):
        for relative in ("cap1.tex", "references.bib", "nested/module.tex", "sitografia.tex"):
            with self.subTest(relative=relative):
                path = self.book / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Partial synthetic source.\n", encoding="utf-8")
                before = self.snapshot()
                self.assert_failure(self.cli("--allow-missing-book", "--check"))
                self.assertEqual(self.snapshot(), before)
                path.unlink()

    def test_custom_entrypoint_is_used_by_api_and_cli(self):
        self.make_book(source="volume.tex")
        (self.book / "main.tex").write_text("\\linkbreve{mustNotBeRead}\n", encoding="utf-8")
        paths = links.source_paths(self.book, source="volume.tex")
        self.assertIn(self.book / "volume.tex", paths)
        self.assertNotIn(self.book / "main.tex", paths)
        self.assertEqual(links.validate_sources(self.book, REDIRECTS, source="volume.tex"), [])
        self.assert_success(self.cli("--source", "volume.tex"))
        self.assert_success(self.cli("--source", "volume.tex", "--check"))
        self.assert_failure(self.cli("--source", "missing.tex", "--allow-missing-book"))

    def test_default_paths_are_site_book_and_mkdocs_from_any_working_directory(self):
        site = self.base / "synthetic-site"
        scripts = site / "scripts"
        scripts.mkdir(parents=True)
        copied_script = scripts / SCRIPT.name
        shutil.copyfile(SCRIPT, copied_script)
        shutil.copyfile(self.registry, site / "mkdocs.yml")
        self.make_book()
        shutil.copytree(self.book, site / "book")
        result = subprocess.run(
            [sys.executable, str(copied_script)], cwd=self.base,
            text=True, capture_output=True, timeout=20)
        self.assert_success(result)
        self.assertEqual((site / "book" / "sitografia.tex").read_text(encoding="utf-8"),
                         links.render(REDIRECTS))
        self.assertFalse((self.book / "sitografia.tex").exists())


if __name__ == "__main__":
    unittest.main()
