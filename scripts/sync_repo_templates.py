#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
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

    def has_working_tree_changes(self) -> bool:
        return any(change.action in {"add", "update"} for change in self.values())

    def has_manifest_adoptions(self) -> bool:
        return any(change.action == "adopt_unchanged" for change in self.values())


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
        if change.action not in {"add", "update"}:
            continue
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
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


def clone_command(repo: str, target: Path) -> list[str]:
    return [
        "gh", "repo", "clone", repo, str(target), "--",
        "--quiet", "--filter=blob:none", "--sparse", "--depth", "1", "--single-branch",
    ]


def clone_repo(repo: str, workspace: Path) -> Path:
    target = workspace / repo.split("/", 1)[1]
    if target.exists():
        shutil.rmtree(target)
    run(clone_command(repo, target))
    run(["git", "sparse-checkout", "set", ".github", ".gemini"], cwd=target)
    return target


def checkout_branch(repo_dir: Path, branch: str) -> None:
    run(["git", "fetch", "origin", branch, "--quiet"], cwd=repo_dir)
    run(["git", "checkout", branch], cwd=repo_dir)
    status = run(["git", "status", "--porcelain"], cwd=repo_dir).stdout.strip()
    if status:
        raise RuntimeError(f"target worktree is dirty: {repo_dir}")


def create_backup_branch(repo_dir: Path, branch: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = f"template-sync-backup/{branch}-{stamp}"
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


def plan_blocks_run(plan: ChangePlan, dry_run: bool) -> bool:
    return False if dry_run else plan.has_blocking_collisions()


def stage_managed_files(repo_dir: Path, rendered: dict[Path, str]) -> None:
    paths = [rel.as_posix() for rel in sorted(rendered)]
    paths.append(MANIFEST_PATH.as_posix())
    run(["git", "add", "--", *paths], cwd=repo_dir)


def has_staged_changes(repo_dir: Path) -> bool:
    return run(["git", "diff", "--cached", "--quiet"], cwd=repo_dir, check=False).returncode != 0


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
            if not can_apply:
                print("  BLOCKED: collisions require --adopt-collisions")
                if plan_blocks_run(plan, dry_run=args.dry_run):
                    failed += 1
                    continue
            if args.dry_run:
                if plan.has_working_tree_changes() or plan.has_manifest_adoptions() or plan.has_blocking_collisions():
                    changed += 1
                continue
            backup = create_backup_branch(repo_dir, branch)
            stage_managed_files(repo_dir, rendered)
            if not has_staged_changes(repo_dir):
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
