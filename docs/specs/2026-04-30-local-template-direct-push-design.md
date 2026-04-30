# Local Template Direct-Push Sync Design

## Context

`nakkulla/github-actions-shared` owns shared Gemini Code Assist and GitHub repository templates. The existing sync tool can render templates from a profile and currently supports owner-wide repository discovery through GitHub. That remote-wide mode is too broad for day-to-day template rollout because it can touch repositories that are not present in the user's local working set.

The desired workflow is to use `github-actions-shared` as the canonical template source while making it easy to apply those templates to selected local repositories under `~/GitHub` or `~/Documents/GitHub`. Direct push is acceptable, but the default operating model must be local-checkout scoped, explicit, and collision-safe.

## Goals

- Make it easy to apply `github-actions-shared` templates to local repositories.
- Support direct-push application for local checkouts after safety checks pass.
- Prefer local workspace discovery over owner-wide remote discovery.
- Keep dry-run/drift reporting as the first-class preview path.
- Preserve existing repository-specific files unless they are explicitly managed by the shared template manifest.
- Align canonical templates with the intended sources:
  - `dotfiles` for reusable workflow behavior.
  - `nakkulla/.github` for account/community pull request template defaults.
  - `github-actions-shared` for the distribution-ready consumer wrapper and Gemini defaults.

## Non-goals

- Do not reintroduce broad owner-wide apply as the recommended path.
- Do not force-push or rewrite repository history.
- Do not overwrite conflicting existing files by default.
- Do not delete unmanaged `.github/` or `.gemini/` files.
- Do not change `pr-review-v4`; GitHub review thread collection already sees Gemini Code Assist comments.
- Do not create or move release tags as part of this work.

## Proposed CLI behavior

### Dry-run local workspace

```bash
python3 scripts/sync_repo_templates.py \
  --profile agent-workflow \
  --workspace ~/GitHub \
  --dry-run
```

The command scans immediate child directories of the workspace, keeps only Git repositories, resolves each repository's `origin`, and previews template drift for repositories whose `origin` maps to `nakkulla/<repo>`.

### Apply local workspace

```bash
python3 scripts/sync_repo_templates.py \
  --profile agent-workflow \
  --workspace ~/GitHub \
  --apply
```

The command applies only to local repositories that pass all safety checks. It commits and pushes template changes to each repository's configured target branch.

### Apply one local repository

```bash
python3 scripts/sync_repo_templates.py \
  --profile agent-workflow \
  --repo ~/GitHub/some-repo \
  --apply
```

`--repo` remains repeatable. Each value is classified before execution:

- Existing filesystem paths, including paths expanded from `~`, are treated as local checkouts.
- Bare relative names without a slash, such as `some-repo`, are invalid; local checkout inputs should be explicit paths such as `./some-repo`, `../some-repo`, `~/GitHub/some-repo`, or an absolute path.
- Path-like values that do not exist are invalid, not remote repository identifiers. Path-like means an absolute path, a value beginning with `~`, `./`, or `../`, or a value with more than one `/` separator after shell expansion.
- Values matching exactly `owner/name` with one slash and not path-like are treated as remote repository identifiers for backward compatibility. For a local checkout under a child directory named `owner/name`, callers must use `./owner/name` or an absolute path.
- Mixed local-path and remote-identifier `--repo` values are invalid in one invocation.

Selection modes are mutually exclusive:

- `--workspace <path>` selects local child repositories.
- `--repo <path> [--repo <path> ...]` selects one or more local checkouts.
- `--repo owner/name [--repo owner/name ...]` selects explicit remote repositories for compatibility.
- `--owner <owner>` selects remote repositories and is retained as an advanced compatibility mode.

The tool must reject combinations that mix selection modes, such as `--workspace` with `--owner`, or `--workspace` with `--repo`. Documentation should recommend local `--workspace` and local path `--repo` modes for direct-push use. Examples such as `~/GitHub/missing-repo`, `./missing-repo`, or bare `missing-repo` must fail fast instead of being interpreted as remote repositories.

## Repository selection

Local workspace discovery should:

1. Expand `~` and resolve the workspace path.
2. Inspect direct child directories only.
3. Keep directories where `git -C <path> rev-parse --is-inside-work-tree` succeeds.
4. Resolve `origin` with `git -C <path> remote get-url origin`.
5. Normalize common GitHub URL forms to `owner/repo`:
   - `git@github.com:owner/repo.git`
   - `https://github.com/owner/repo.git`
   - `ssh://git@github.com/owner/repo.git`
6. Include repositories whose owner matches the profile `repo_selection.owner`, unless explicit local repo paths were supplied.
7. Exclude the `repo_selection.exclude` list.

Skipped workspace entries are reported with concise reasons in dry-run and apply output, for example `not a git repository`, `no origin`, `non-GitHub origin`, or `owner mismatch`. Skipped ineligible workspace entries do not make the command fail. Eligible repositories that fail safety checks during `--apply` do make the command fail.

Multi-repository apply uses continue-on-error semantics: the tool attempts every eligible repository, records each result, keeps any successful commits and pushes, and does not attempt rollback for earlier successes. The final summary must include skipped, unchanged, pushed, blocked, and failed counts. The final exit code is non-zero when any eligible repository is blocked or failed.

## Branch and apply safety checks

Local direct-push mode must avoid surprising branch switches. For every local repository, `--apply` must verify:

1. The worktree is clean before any fetch or template write, including untracked files that overlap managed paths.
2. The current branch equals the profile target branch, defaulting to `main`.
3. `git fetch origin <branch>` succeeds.
4. `origin/<branch>` exists.
5. `HEAD` exactly equals `origin/<branch>` after fetch. Ahead, behind, or diverged branches are blocked.
6. If the profile target branch differs from the repository's GitHub default branch, the tool still uses the profile branch but reports the mismatch in dry-run output.
7. Multiple Git worktrees are allowed only when the selected local checkout itself is on the target branch and clean. The tool must not try to check out or move a branch that is currently checked out elsewhere.
8. No conflicting existing file is overwritten unless `--adopt-collisions` is explicit.
9. Unmanaged `.github/` and `.gemini/` files are preserved.
10. A backup branch is created before committing when the profile requests `create_backup_branch`.
11. The staged file list contains only managed template paths.
12. Push uses normal `git push origin <branch>`.

The tool must not use force push. If push fails after a local commit is created, it should report the repo, return non-zero, and leave the local commit in that checkout for manual recovery. Dry-run must never write files, create commits, create backup branches, or push.

## Managed file behavior

The shared manifest remains the source of truth for which files are managed by the template sync. The tool may:

- Add missing files rendered by the current profile.
- Adopt unchanged existing files into the manifest when their content exactly matches the rendered template.
- Update files that are already listed in the previous manifest.
- Prune files only when both conditions are true:
  1. The file is listed in the previous manifest's `managed_files`.
  2. The file is no longer rendered by the current profile.

First-run repositories without a manifest must not prune anything. The tool must not delete files that are outside the previous manifest, even if they live under `.github/` or `.gemini/`.

## Template source alignment

Before recommending local rollout, the canonical template content should be checked against its intended baseline:

- `.github/workflows/reusable-pr-ci.yml` should continue matching the reusable workflow source currently used by `dotfiles`, unless there is an explicit design to diverge.
- `templates/github/default/.github/pull_request_template.md` should intentionally match or minimally normalize `nakkulla/.github/.github/PULL_REQUEST_TEMPLATE.md`.
- `templates/github/default/.github/workflows/pr-ci.yml` should remain a minimal consumer wrapper that calls `nakkulla/github-actions-shared/.github/workflows/reusable-pr-ci.yml`.
- Gemini templates should remain canonical in `github-actions-shared`, with review guidance focused on correctness, verification, security, CI/release safety, and low-noise comments.

This alignment should be documented so future template changes are made in the right source repository.

## Testing

Add or update tests for:

- GitHub remote URL normalization.
- Local workspace repository discovery.
- Owner/exclude filtering.
- Path-based `--repo` selection.
- Dirty worktree blocking before apply.
- Staged-file allowlist enforcement.
- Dry-run output for skipped local directories.
- Existing remote-target behavior if it remains supported.
- Selection-mode validation for invalid `--workspace` / `--owner` / `--repo` combinations.
- Invalid missing path-like `--repo` values such as `~/GitHub/missing-repo` and `./missing-repo`.
- Explicit skip reasons without non-zero exit for ineligible workspace entries.
- Collision blocking text and non-zero exit for blocked apply runs.
- No writes, commits, backup branches, or pushes during dry-run.
- Branch safety blocking when the local checkout is not exactly on the up-to-date target branch.
- Multi-repository apply continue-on-error behavior and final non-zero exit when any eligible repository is blocked or failed.

Existing contract tests should continue to pass:

```bash
bash tests/reusable_pr_ci_contract_test.sh
bash tests/template_contract_test.sh
python3 tests/sync_repo_templates_test.py
```

## Rollout

1. Implement local workspace discovery and path-based repo selection.
2. Update README to recommend local dry-run first and local direct-push apply second.
3. Keep owner-wide direct-push documented as discouraged or advanced-only if retained.
4. Verify on one selected local repository before any workspace-wide apply.
5. Use workspace-wide apply only after dry-run output is reviewed.

## Acceptance criteria

- A user can dry-run template drift for local repositories under `~/GitHub`.
- A user can direct-push template changes to a single local checkout with `--repo <path> --apply`.
- A user can direct-push template changes to all eligible local checkouts in a workspace with `--workspace <path> --apply`.
- The tool blocks dirty, divergent, wrong-branch, conflicting, or non-matching repositories before making changes.
- The tool reports explicit skip and block reasons with deterministic exit status: dry-run succeeds unless invocation/profile loading fails; apply attempts all eligible repositories and fails at the end when any eligible repository cannot be safely applied.
- The tool never force-pushes and never deletes unmanaged files.
- README presents local-checkout direct push as the recommended simple workflow.
