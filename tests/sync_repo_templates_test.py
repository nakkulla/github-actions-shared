#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sync_repo_templates as sync


class SyncRepoTemplatesTest(unittest.TestCase):
    def test_load_profile_uses_json_and_resolves_include_dirs(self):
        profile = sync.load_profile(ROOT, "agent-workflow")
        self.assertEqual(profile["name"], "agent-workflow")
        includes = sync.profile_include_dirs(ROOT, profile)
        self.assertTrue(includes)
        for include in includes:
            self.assertTrue(include.is_dir(), include)

    def test_render_profile_layers_later_files_over_earlier_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first" / ".gemini"
            second = root / "second" / ".gemini"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "styleguide.md").write_text("first\n", encoding="utf-8")
            (second / "styleguide.md").write_text("second\n", encoding="utf-8")
            rendered = sync.render_includes(root, [root / "first", root / "second"])
            self.assertEqual(rendered[Path(".gemini/styleguide.md")], "second\n")

    def test_rejects_rendered_paths_outside_allowed_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            include = root / "bad"
            include.mkdir()
            (include / "README.md").write_text("bad\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                sync.render_includes(root, [include])

    def test_plan_first_sync_add_adopt_and_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".gemini").mkdir()
            (repo / ".gemini" / "same.md").write_text("same\n", encoding="utf-8")
            (repo / ".gemini" / "different.md").write_text("old\n", encoding="utf-8")
            rendered = {
                Path(".gemini/new.md"): "new\n",
                Path(".gemini/same.md"): "same\n",
                Path(".gemini/different.md"): "new\n",
            }
            plan = sync.plan_changes(repo, rendered, manifest=None, adopt_collisions=False)
            self.assertEqual(plan[Path(".gemini/new.md")].action, "add")
            self.assertEqual(plan[Path(".gemini/same.md")].action, "adopt_unchanged")
            self.assertEqual(plan[Path(".gemini/different.md")].action, "collision")
            self.assertTrue(plan.has_blocking_collisions())

    def test_dry_run_does_not_treat_collisions_as_exit_failures(self):
        plan = sync.ChangePlan({
            Path(".github/workflows/pr-ci.yml"): sync.Change(
                action="collision",
                path=Path(".github/workflows/pr-ci.yml"),
                old_sha="old",
                new_sha="new",
            )
        })
        self.assertFalse(sync.plan_blocks_run(plan, dry_run=True))
        self.assertTrue(sync.plan_blocks_run(plan, dry_run=False))

    def test_write_manifest_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sync.write_manifest(
                repo,
                source="nakkulla/github-actions-shared",
                profile="agent-workflow",
                source_ref="abc123",
                managed_files=[Path(".gemini/styleguide.md"), Path(".github/workflows/pr-ci.yml")],
            )
            manifest = json.loads((repo / ".github" / "shared-template-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["managed_files"], [".gemini/styleguide.md", ".github/workflows/pr-ci.yml"])


if __name__ == "__main__":
    unittest.main()
