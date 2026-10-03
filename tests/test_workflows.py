from pathlib import Path
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

    def test_book_workflow_tracks_redirect_and_generator_changes(self):
        publish = self.workflow("publish-book.yml")
        self.assertEqual(publish["on"]["push"]["branches"], ["main"])
        self.assertTrue({"book/**", "config/book.json", "scripts/book.py",
                         "scripts/aggiorna-link.py", "mkdocs.yml", "requirements.txt",
                         ".github/workflows/publish-book.yml"}
                        .issubset(publish["on"]["push"]["paths"]))

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
