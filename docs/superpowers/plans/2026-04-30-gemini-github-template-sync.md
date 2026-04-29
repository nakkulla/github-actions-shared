# Gemini GitHub Template Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build canonical Gemini/GitHub templates and a guarded direct-push sync tool for repositories owned by `nakkulla`.

**Architecture:** Keep all template source in `github-actions-shared`, render profiles from stdlib-only JSON configuration, and sync target repositories through a safety-first CLI that defaults to dry-run. Direct push is supported only after deterministic collision checks, manifest generation, and backup branch creation.

**Tech Stack:** Bash, Python 3 standard library (`argparse`, `json`, `pathlib`, `subprocess`, `tempfile`, `unittest`), GitHub CLI (`gh`), Git.

---

## Source Spec

- `docs/specs/2026-04-30-gemini-github-template-sync-design.md`

## File Structure

- Create `templates/gemini/default/.gemini/config.yaml` — shared Gemini Code Assist behavior defaults.
- Create `templates/gemini/default/.gemini/styleguide.md` — general review guidance for all repositories.
- Create `templates/gemini/agent-workflow/.gemini/styleguide.md` — agent/workflow-specific styleguide overlay.
- Create `templates/github/default/.github/pull_request_template.md` — shared PR template.
- Create `templates/github/default/.github/workflows/pr-ci.yml` — consumer wrapper that calls the shared reusable PR CI workflow.
- Create `profiles/agent-workflow.json` — profile that layers the initial Gemini/GitHub templates.
- Create `scripts/sync_repo_templates.py` — stdlib-only sync CLI, rendering engine, manifest logic, collision handling, dry-run, and direct-push apply.
- Create `tests/template_contract_test.sh` — shell contract checks for template/profile presence and workflow naming.
- Create `tests/sync_repo_templates_test.py` — Python unittest coverage for rendering, manifest, collision, and dry-run safety behavior.
- Modify `README.md` — document templates, dry-run, apply, direct-push safety, and rollout workflow.

## Task 1: Add canonical templates and profile

**Files:**
- Create: `templates/gemini/default/.gemini/config.yaml`
- Create: `templates/gemini/default/.gemini/styleguide.md`
- Create: `templates/gemini/agent-workflow/.gemini/styleguide.md`
- Create: `templates/github/default/.github/pull_request_template.md`
- Create: `templates/github/default/.github/workflows/pr-ci.yml`
- Create: `profiles/agent-workflow.json`
- Test later: `tests/template_contract_test.sh`

- [ ] **Step 1: Create Gemini default config**

Create `templates/gemini/default/.gemini/config.yaml`:

```yaml
have_fun: false

memory_config:
  disabled: false

code_review:
  disable: false
  comment_severity_threshold: MEDIUM
  max_review_comments: 20
  pull_request_opened:
    help: false
    summary: true
    code_review: true
    include_drafts: false

ignore_patterns:
  - "tmp/**"
  - "logs/**"
  - ".worktrees/**"
  - ".venv/**"
  - "node_modules/**"
  - "**/__pycache__/**"
  - "**/.pytest_cache/**"
```

- [ ] **Step 2: Create default Gemini styleguide**

Create `templates/gemini/default/.gemini/styleguide.md`:

```md
# Gemini Code Assist Review Guide

Review repositories for concrete correctness, safety, maintainability, and verification risks.

## Review priorities

Focus on issues that can cause real failures:

1. Bugs, regressions, or broken public behavior.
2. Missing verification for meaningful behavior changes.
3. Security, secret exposure, data-loss, or unsafe automation risks.
4. Incorrect CI, release, or repository maintenance behavior.
5. Documentation that contradicts executable behavior.

## What to comment on

Leave comments for:

- Concrete bugs or likely regressions.
- Missing or misleading tests and verification.
- Unsafe shell, Git, filesystem, credential, or network behavior.
- Incorrect GitHub Actions syntax, permissions, or trigger behavior.
- Changes that claim success without current evidence.

## What not to comment on

Avoid comments for:

- Personal style preferences.
- Formatting-only concerns when the file is internally consistent.
- Broad refactors unrelated to the pull request intent.
- Generated, temporary, cache, log, or local environment files.
- Requests for abstractions when direct code solves the current requirement.

## Severity guidance

Use high severity for runtime-breaking behavior, security/data-loss risk, broken CI/release automation, or misleading success claims.

Use medium severity for missing verification, ambiguous behavior that is likely to cause mistakes, and common edge cases.

Use low severity sparingly. Prefer no comment over low-value comments.
```

- [ ] **Step 3: Create agent-workflow Gemini styleguide overlay**

Create `templates/gemini/agent-workflow/.gemini/styleguide.md`:

```md
# Gemini Code Assist Review Guide

Review this repository as an AI tooling, workflow, and automation repository.

## Review priorities

Focus on issues that can cause real workflow failures:

1. Incorrect or unsafe agent instructions.
2. Broken install scripts, generated instruction output, hooks, or symlink/copy behavior.
3. Changes that mutate live runtime directories from a worktree.
4. Missing or incorrect verification steps for changed scripts, skills, rules, workflows, or installers.
5. Regressions in Beads, PR review, skill, Codex, Claude, or GitHub Actions workflow contracts.
6. Security or data-loss risks, especially shell scripts, Git operations, secrets, credentials, and destructive commands.

## Repository-specific rules

- Prefer minimal, targeted changes that preserve existing conventions.
- Treat `.github/`, `.gemini/`, `shared/`, `codex/`, `claude/`, `shell/`, `scripts/`, and install scripts as high-impact areas when present.
- Do not suggest editing generated installed files under `~/.codex`, `~/.claude`, or `~/.config`; source files in the repository are the source of truth.
- Do not suggest running install scripts from a git worktree against live user configuration.
- For docs-only changes, avoid demanding runtime install verification unless the docs affect install/runtime behavior.

## What to comment on

Leave comments for:

- Bugs, contradictions, or stale workflow guarantees.
- Missing verification when a changed file clearly needs it.
- Incorrect path assumptions, especially skill-relative paths, workflow paths, and install target paths.
- Unsafe shell behavior, unquoted variables, destructive Git commands, or accidental broad file operations.
- Review/merge automation that could claim success without current-run evidence.

## What not to comment on

Avoid comments for personal preferences, pure formatting, unrelated architecture suggestions, generated files, and abstraction requests that are not needed for the pull request.
```

- [ ] **Step 4: Create shared PR template**

Create `templates/github/default/.github/pull_request_template.md`:

```md
## Summary
- 

## Verification
- 

## Notes
- 
```

- [ ] **Step 5: Create consumer PR CI wrapper**

Create `templates/github/default/.github/workflows/pr-ci.yml`:

```yaml
name: PR CI

on:
  pull_request:
  workflow_dispatch:

jobs:
  baseline:
    uses: nakkulla/github-actions-shared/.github/workflows/reusable-pr-ci.yml@main
```

Use `@main` until the repository release policy allows moving consumers to `@v1`.

- [ ] **Step 6: Create initial profile JSON**

Create `profiles/agent-workflow.json`:

```json
{
  "name": "agent-workflow",
  "include": [
    "templates/gemini/default",
    "templates/gemini/agent-workflow",
    "templates/github/default"
  ],
  "repo_selection": {
    "owner": "nakkulla",
    "exclude": ["github-actions-shared"]
  },
  "sync": {
    "mode": "direct-push",
    "branch": "main",
    "commit_message": "chore: shared github/gemini templates 동기화"
  },
  "safety": {
    "require_clean_worktree": true,
    "create_backup_branch": true,
    "never_delete_unmanaged_files": true,
    "only_prune_managed_files": true
  }
}
```

- [ ] **Step 7: Commit template/profile changes**

Run:

```bash
git add templates profiles
git commit -m "Gemini GitHub 공유 템플릿 추가"
```

Expected: commit succeeds with only `templates/**` and `profiles/**` staged.

## Task 2: Add template contract test

**Files:**
- Create: `tests/template_contract_test.sh`

- [ ] **Step 1: Create shell contract test**

Create `tests/template_contract_test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "templates/gemini/default/.gemini/config.yaml"
  "templates/gemini/default/.gemini/styleguide.md"
  "templates/gemini/agent-workflow/.gemini/styleguide.md"
  "templates/github/default/.github/pull_request_template.md"
  "templates/github/default/.github/workflows/pr-ci.yml"
  "profiles/agent-workflow.json"
)

for path in "${required_files[@]}"; do
  test -f "$path"
done

python3 - <<'PY'
import json
from pathlib import Path
profile = json.loads(Path('profiles/agent-workflow.json').read_text(encoding='utf-8'))
assert profile['name'] == 'agent-workflow'
for include in profile['include']:
    assert Path(include).is_dir(), include
assert profile['sync']['mode'] == 'direct-push'
assert profile['sync']['branch'] == 'main'
PY

grep -q '^name: PR CI$' templates/github/default/.github/workflows/pr-ci.yml
grep -q 'nakkulla/github-actions-shared/.github/workflows/reusable-pr-ci.yml@main' templates/github/default/.github/workflows/pr-ci.yml
grep -q 'comment_severity_threshold: MEDIUM' templates/gemini/default/.gemini/config.yaml
grep -q 'max_review_comments: 20' templates/gemini/default/.gemini/config.yaml

echo 'PASS: template contract'
```

- [ ] **Step 2: Make test executable**

Run:

```bash
chmod +x tests/template_contract_test.sh
```

- [ ] **Step 3: Run contract test**

Run:

```bash
bash tests/template_contract_test.sh
```

Expected output includes:

```text
PASS: template contract
```

- [ ] **Step 4: Commit contract test**

Run:

```bash
git add tests/template_contract_test.sh
git commit -m "공유 템플릿 계약 테스트 추가"
```

Expected: commit succeeds with only `tests/template_contract_test.sh` staged.

## Task 3: Add stdlib-only sync tool tests first

**Files:**
- Create: `tests/sync_repo_templates_test.py`
- Create later: `scripts/sync_repo_templates.py`

- [ ] **Step 1: Create failing unit tests**

Create `tests/sync_repo_templates_test.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail before implementation**

Run:

```bash
python3 tests/sync_repo_templates_test.py
```

Expected: FAIL or ERROR because `scripts/sync_repo_templates.py` does not exist yet.

- [ ] **Step 3: Commit failing tests**

Run:

```bash
git add tests/sync_repo_templates_test.py
git commit -m "템플릿 동기화 도구 테스트 추가"
```

Expected: commit succeeds with only `tests/sync_repo_templates_test.py` staged.

## Task 4: Implement sync rendering, manifest, and dry-run logic

**Files:**
- Create: `scripts/sync_repo_templates.py`
- Modify: `tests/sync_repo_templates_test.py` only if a test import path mistake is discovered

- [ ] **Step 1: Create sync tool module and CLI**

Create `scripts/sync_repo_templates.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED_ROOTS = (".gemini", ".github")
MANIFEST_PATH = Path(".github/shared-template-manifest.json")
SOURCE_REPO = "nakkulla/github-actions-shared"


@dataclasses.dataclass(frozen=True)
class Change:
    action: str
    path: Path
    old_sha: str | None = None
    new_sha: str | None = None


class ChangePlan(dict):
    def has_blocking_collisions(self) -> bool:
        return any(change.action == "collision" for change in self.values())


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_profile(root: Path, name: str) -> dict:
    profile_path = root / "profiles" / f"{name}.json"
    with profile_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def profile_include_dirs(root: Path, profile: dict) -> list[Path]:
    dirs = []
    for raw in profile.get("include", []):
        path = root / raw
        if not path.is_dir():
            raise FileNotFoundError(f"profile include not found: {raw}")
        dirs.append(path)
    return dirs


def is_allowed_render_path(path: Path) -> bool:
    parts = path.parts
    if not parts:
        return False
    return parts[0] in ALLOWED_ROOTS


def render_includes(root: Path, include_dirs: list[Path]) -> dict[Path, str]:
    rendered: dict[Path, str] = {}
    for include in include_dirs:
        for file_path in sorted(p for p in include.rglob("*") if p.is_file()):
            rel = file_path.relative_to(include)
            if not is_allowed_render_path(rel):
                raise ValueError(f"rendered path outside allowed roots: {rel}")
            rendered[rel] = file_path.read_text(encoding="utf-8")
    return rendered


def load_manifest(repo: Path) -> dict | None:
    path = repo / MANIFEST_PATH
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def managed_paths(manifest: dict | None) -> set[str]:
    if not manifest:
        return set()
    return set(manifest.get("managed_files", []))


def plan_changes(repo: Path, rendered: dict[Path, str], manifest: dict | None, adopt_collisions: bool) -> ChangePlan:
    plan = ChangePlan()
    managed = managed_paths(manifest)
    for rel, new_text in sorted(rendered.items(), key=lambda item: str(item[0])):
        target = repo / rel
        new_sha = sha_text(new_text)
        rel_str = rel.as_posix()
        if not target.exists():
            action = "add"
            old_sha = None
        else:
            old_sha = sha_file(target)
            if target.read_text(encoding="utf-8") == new_text:
                action = "unchanged_managed" if rel_str in managed else "adopt_unchanged"
            elif rel_str in managed or adopt_collisions:
                action = "update"
            else:
                action = "collision"
        plan[rel] = Change(action=action, path=rel, old_sha=old_sha, new_sha=new_sha)
    return plan


def write_rendered(repo: Path, rendered: dict[Path, str], plan: ChangePlan) -> None:
    for rel, change in plan.items():
        if change.action not in {"add", "adopt_unchanged", "unchanged_managed", "update"}:
            continue
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if change.action in {"add", "update"}:
            target.write_text(rendered[rel], encoding="utf-8")


def write_manifest(repo: Path, source: str, profile: str, source_ref: str, managed_files: list[Path]) -> None:
    path = repo / MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source,
        "profile": profile,
        "source_ref": source_ref,
        "managed_files": sorted(p.as_posix() for p in managed_files),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_owner_repos(owner: str) -> list[str]:
    result = run([
        "gh", "repo", "list", owner,
        "--limit", "1000",
        "--json", "nameWithOwner,isArchived,isFork",
    ])
    repos = json.loads(result.stdout)
    return [r["nameWithOwner"] for r in repos if not r.get("isArchived") and not r.get("isFork")]


def clone_repo(repo: str, workspace: Path) -> Path:
    target = workspace / repo.split("/", 1)[1]
    run(["gh", "repo", "clone", repo, str(target), "--", "--quiet"])
    return target


def checkout_branch(repo_dir: Path, branch: str) -> None:
    run(["git", "fetch", "origin", branch, "--quiet"], cwd=repo_dir)
    run(["git", "checkout", branch], cwd=repo_dir)
    status = run(["git", "status", "--porcelain"], cwd=repo_dir).stdout.strip()
    if status:
        raise RuntimeError(f"target worktree is dirty: {repo_dir}")


def create_backup_branch(repo_dir: Path, branch: str) -> str:
    backup = f"template-sync-backup/{branch}-{run(['date', '+%Y%m%d-%H%M%S']).stdout.strip()}"
    run(["git", "branch", backup], cwd=repo_dir)
    run(["git", "push", "origin", backup], cwd=repo_dir)
    return backup


def apply_repo(repo_dir: Path, profile_name: str, source_ref: str, rendered: dict[Path, str], adopt_collisions: bool) -> tuple[ChangePlan, bool]:
    manifest = load_manifest(repo_dir)
    plan = plan_changes(repo_dir, rendered, manifest, adopt_collisions=adopt_collisions)
    if plan.has_blocking_collisions():
        return plan, False
    write_rendered(repo_dir, rendered, plan)
    write_manifest(repo_dir, SOURCE_REPO, profile_name, source_ref, list(rendered))
    return plan, True


def print_plan(repo: str, plan: ChangePlan) -> None:
    print(f"repo: {repo}")
    for change in plan.values():
        print(f"  {change.action}: {change.path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync shared Gemini/GitHub templates to repositories.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--owner")
    parser.add_argument("--repo", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--adopt-collisions", action="store_true")
    parser.add_argument("--workspace")
    args = parser.parse_args(argv)

    if args.dry_run == args.apply:
        parser.error("choose exactly one of --dry-run or --apply")

    root = Path(__file__).resolve().parents[1]
    profile = load_profile(root, args.profile)
    owner = args.owner or profile.get("repo_selection", {}).get("owner")
    exclude = set(profile.get("repo_selection", {}).get("exclude", []))
    branch = profile.get("sync", {}).get("branch", "main")
    commit_message = profile.get("sync", {}).get("commit_message", "chore: shared templates 동기화")
    include_dirs = profile_include_dirs(root, profile)
    rendered = render_includes(root, include_dirs)
    source_ref = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()

    repos = list(args.repo)
    if not repos:
        if not owner:
            parser.error("--owner or --repo is required")
        repos = list_owner_repos(owner)
    repos = [repo for repo in repos if repo.split("/", 1)[-1] not in exclude]
    if args.limit:
        repos = repos[: args.limit]

    changed = 0
    failed = 0
    base_workspace = Path(args.workspace) if args.workspace else Path(tempfile.mkdtemp(prefix="template-sync-"))
    base_workspace.mkdir(parents=True, exist_ok=True)

    for repo in repos:
        try:
            repo_dir = clone_repo(repo, base_workspace)
            checkout_branch(repo_dir, branch)
            plan, can_apply = apply_repo(repo_dir, args.profile, source_ref, rendered, args.adopt_collisions)
            print_plan(repo, plan)
            if plan.has_blocking_collisions():
                print(f"  BLOCKED: collisions require --adopt-collisions")
                failed += 1
                continue
            if args.dry_run:
                if any(change.action in {"add", "update", "adopt_unchanged"} for change in plan.values()):
                    changed += 1
                continue
            backup = create_backup_branch(repo_dir, branch)
            run(["git", "add", ".gemini", ".github"], cwd=repo_dir)
            if not run(["git", "diff", "--cached", "--quiet"], cwd=repo_dir, check=False).returncode:
                print(f"  unchanged after render; backup={backup}")
                continue
            run(["git", "commit", "-m", commit_message], cwd=repo_dir)
            run(["git", "push", "origin", branch], cwd=repo_dir)
            print(f"  pushed: {branch}; backup={backup}")
            changed += 1
        except Exception as exc:
            failed += 1
            print(f"repo: {repo}\n  ERROR: {exc}", file=sys.stderr)
    print(f"summary: repos={len(repos)} changed_or_pending={changed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Make script executable**

Run:

```bash
chmod +x scripts/sync_repo_templates.py
```

- [ ] **Step 3: Run unit tests**

Run:

```bash
python3 tests/sync_repo_templates_test.py
```

Expected output includes:

```text
OK
```

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add scripts/sync_repo_templates.py tests/sync_repo_templates_test.py
git commit -m "템플릿 동기화 도구 구현"
```

Expected: commit succeeds with only sync tool and test paths staged.

## Task 5: Document usage and run local verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with template sync docs**

Add this section after `Current workflows`:

```md
## Shared repository templates

This repository also owns canonical Gemini Code Assist and GitHub repository templates.

Current profile:

- `profiles/agent-workflow.json` — syncs `.gemini/` defaults and a conservative `.github/` baseline for agent/workflow repositories.

Dry-run owner-wide sync:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --dry-run
```

Apply owner-wide direct-push sync:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --apply
```

Safety rules:

- The sync tool defaults to dry-run unless `--apply` is supplied.
- Direct-push apply creates a backup branch before updating a target branch.
- First sync adopts identical existing files, adds missing files, and blocks conflicting existing files unless `--adopt-collisions` is explicit.
- Unmanaged `.github/` and `.gemini/` files are not deleted.
- The consumer wrapper `.github/workflows/pr-ci.yml` calls this repository's reusable workflow `.github/workflows/reusable-pr-ci.yml`.
```

- [ ] **Step 2: Run all local checks**

Run:

```bash
bash tests/reusable_pr_ci_contract_test.sh
bash tests/template_contract_test.sh
python3 tests/sync_repo_templates_test.py
```

Expected:

```text
PASS: reusable pr ci contract
PASS: template contract
OK
```

- [ ] **Step 3: Run limited dry-run**

Run:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --dry-run --limit 1
```

Expected: prints one repository report and no remote pushes.

- [ ] **Step 4: Commit README update**

Run:

```bash
git add README.md
git commit -m "템플릿 동기화 사용법 문서화"
```

Expected: commit succeeds with only `README.md` staged.

## Task 6: Owner-wide direct push rollout

**Files:**
- No source file changes expected unless a safety issue is found.

- [ ] **Step 1: Run owner-wide dry-run**

Run:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --dry-run
```

Expected: report lists target repositories, changes, and any collisions. If collisions appear, stop and inspect. Do not use `--adopt-collisions` without user approval for the specific repos and files.

- [ ] **Step 2: Run owner-wide direct-push apply**

Only run this step if dry-run shows no blocking collisions or all collision adoptions were explicitly approved.

Run:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --apply
```

Expected: each changed repository reports a backup branch and pushed target branch. Repositories with branch protection or push rejection are reported as failures and not silently ignored.

- [ ] **Step 3: Verify source repository status**

Run:

```bash
git status --short --branch
git log --oneline -5
```

Expected: source repository is clean and local `main` is ahead only by intentional commits if not pushed yet.

- [ ] **Step 4: Push source repository**

Run:

```bash
git push origin main
```

Expected: source repository pushes successfully.

## Task 7: Final evidence

**Files:**
- No source file changes expected.

- [ ] **Step 1: Collect final verification evidence**

Run:

```bash
bash tests/reusable_pr_ci_contract_test.sh
bash tests/template_contract_test.sh
python3 tests/sync_repo_templates_test.py
git status --short --branch
```

Expected: all tests pass and source repo is clean.

- [ ] **Step 2: Summarize rollout**

Final response must include:

- source repo commit SHA
- local verification commands and results
- owner-wide dry-run result summary
- owner-wide apply result summary
- any skipped or failed repositories
- backup branch pattern used
- confirmation that unmanaged files were not deleted

## Self-Review

- Spec coverage: templates, JSON profiles, manifest, first-sync collision policy, direct-push apply, backup branches, no unmanaged deletion, README docs, and verification are covered.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: test names match functions defined in `scripts/sync_repo_templates.py`; manifest path matches the spec.
- Skill routing: not skill-related; no skill artifacts are created or modified.
