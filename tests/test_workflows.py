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


if __name__ == "__main__":
    unittest.main()
