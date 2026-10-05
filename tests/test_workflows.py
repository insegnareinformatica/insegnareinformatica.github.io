from pathlib import Path
import json
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class SiteWorkflowTests(unittest.TestCase):
    def workflow(self, name):
        # BaseLoader preserves GitHub's "on" key instead of treating it as True.
        return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)

    def test_deployment_requires_checks_from_the_same_commit(self):
        deploy = self.workflow("deploy-site.yml")
        self.assertEqual(deploy["on"]["push"]["branches"], ["main"])
        self.assertIn("workflow_dispatch", deploy["on"])
        jobs = deploy["jobs"]
        self.assertEqual(jobs["check"]["uses"], "./.github/workflows/check-site.yml")
        self.assertEqual(jobs["check"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["build"]["needs"], "check")
        self.assertEqual(jobs["deploy"]["needs"], "build")
        for job in jobs.values():
            self.assertNotIn("if", job, "Keep the default success-only dependency gate")
            self.assertNotIn("continue-on-error", job)

    def test_checks_are_reusable_without_duplicate_push_runs(self):
        check = self.workflow("check-site.yml")
        self.assertIn("workflow_call", check["on"])
        self.assertIn("pull_request", check["on"])
        self.assertIn("workflow_dispatch", check["on"])
        self.assertNotIn("push", check["on"])

    def test_link_validation_precedes_site_tests_and_build(self):
        check = self.workflow("check-site.yml")
        steps = check["jobs"]["check"]["steps"]
        runs = [step["run"] for step in steps if "run" in step]
        self.assertLess(runs.index("python -m pip install -r requirements.txt"),
                        runs.index("python scripts/book.py links"))
        self.assertLess(runs.index("python scripts/book.py links"),
                        runs.index("python -m unittest discover -s tests -v"))
        self.assertLess(runs.index("python scripts/book.py links"),
                        runs.index("mkdocs build --strict"))
        link_step = next(step for step in steps
                         if step.get("run") == "python scripts/book.py links")
        self.assertNotIn("if", link_step)
        self.assertNotIn("continue-on-error", link_step)

    def test_book_build_regenerates_links_before_stamp_and_latex(self):
        publish = self.workflow("publish-book.yml")
        steps = publish["jobs"]["build"]["steps"]
        commands = [step.get("run", step.get("uses")) for step in steps]
        links = commands.index("python scripts/book.py links")
        self.assertLess(commands.index("python -m pip install -r requirements.txt"), links)
        self.assertLess(links, commands.index("python scripts/book.py stamp"))
        self.assertLess(links, commands.index("xu-cheng/latex-action@v4"))
        self.assertNotIn("if", steps[links])
        self.assertNotIn("continue-on-error", steps[links])

    def test_book_workflow_only_runs_automatically_for_book_changes(self):
        publish = self.workflow("publish-book.yml")
        self.assertEqual(publish["on"]["push"]["branches"], ["main"])
        self.assertEqual(publish["on"]["push"]["paths"], ["book/**"])
        self.assertEqual(set(publish["on"]), {"push", "workflow_dispatch"})

    def test_removed_releases_refresh_current_site_without_compiling_book(self):
        refresh = self.workflow("refresh-site-on-release.yml")
        self.assertEqual(refresh["on"]["release"]["types"], ["deleted", "unpublished"])
        self.assertEqual(set(refresh["on"]), {"release", "workflow_dispatch"})
        self.assertEqual(refresh["permissions"], {"actions": "write"})
        steps = refresh["jobs"]["refresh"]["steps"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["env"]["GH_TOKEN"], "${{ github.token }}")
        command = steps[0]["run"]
        self.assertIn("gh api --method POST", command)
        self.assertIn("actions/workflows/deploy-site.yml/dispatches", command)
        self.assertIn("-f ref=main", command)
        self.assertNotIn("publish-book", command)

    def test_book_fonts_are_available_from_the_latex_working_directory(self):
        publish = self.workflow("publish-book.yml")
        latex = next(step for step in publish["jobs"]["build"]["steps"]
                     if step.get("uses") == "xu-cheng/latex-action@v4")
        config = json.loads((ROOT / "config/book.json").read_text())
        directory = (ROOT / config["source"]).parent
        fonts = list(directory.glob(latex["with"]["extra_fonts"]))
        self.assertEqual({font.name for font in fonts}, {
            "SourceSansPro-Regular.otf", "SourceSansPro-RegularIt.otf",
            "SourceSansPro-Bold.otf", "SourceSansPro-BoldIt.otf",
        })
        for font in fonts:
            self.assertEqual(font.read_bytes()[:4], b"OTTO")
        self.assertIn("SIL OPEN FONT LICENSE",
                      (fonts[0].parent / "LICENSE.txt").read_text())
        self.assertEqual(latex["with"]["texlive_version"], "2026")

    def test_only_book_source_illustrations_can_be_pdf_files(self):
        cases = {
            "book/img/illustration.pdf": False,
            "book/img/nested/illustration.pdf": False,
            "book/main.pdf": True,
            "book/draft.pdf": True,
            "docs/book.pdf": True,
            "dist/insegnare-informatica.pdf": True,
        }
        for path, ignored in cases.items():
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "--no-index", "-q", path],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertIn(result.returncode, (0, 1), result.stderr)
                self.assertEqual(result.returncode == 0, ignored)

    def test_link_checks_do_not_relax_book_publication_approval(self):
        publish = self.workflow("publish-book.yml")
        self.assertEqual(publish["permissions"], {"contents": "read"})
        self.assertEqual(publish["env"]["BOOK_PUBLICATION_ENABLED"],
                         "${{ vars.BOOK_PUBLICATION_ENABLED }}")
        self.assertEqual(publish["jobs"]["prepare"]["if"],
                         "github.event_name == 'workflow_dispatch' || vars.BOOK_PUBLICATION_ENABLED == 'true'")
        inputs = publish["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["mode"]["default"], "verifica")
        self.assertEqual(inputs["confirm_publication"]["default"], "false")
        self.assertEqual(publish["jobs"]["publish"]["if"],
                         "needs.prepare.outputs.mode != 'verifica'")
        upload = next(step for step in publish["jobs"]["build"]["steps"]
                      if step.get("uses", "").startswith("actions/upload-artifact@"))
        self.assertEqual(upload["if"], "needs.prepare.outputs.mode != 'verifica'")


if __name__ == "__main__":
    unittest.main()
