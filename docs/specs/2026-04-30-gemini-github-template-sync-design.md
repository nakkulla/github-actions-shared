# Gemini and GitHub Template Sync Design

## Context

`nakkulla/github-actions-shared` currently owns reusable GitHub Actions workflows, starting with `.github/workflows/reusable-pr-ci.yml`. The next goal is to make repository-level GitHub and Gemini Code Assist configuration consistent across repositories owned by `nakkulla`.

Gemini Code Assist reads `.gemini/config.yaml` and `.gemini/styleguide.md` from each repository root. GitHub also reads repository-local `.github/` files such as workflows, pull request templates, issue templates, and Dependabot configuration. A shared source repository can provide canonical templates, but each consumer repository still needs the rendered files present locally.

## Goals

- Store canonical `.gemini/` templates in `github-actions-shared`.
- Store canonical `.github/` templates in `github-actions-shared`.
- Support repository profiles so different repository types can share defaults while adding focused overrides.
- Provide a deterministic sync tool that can scan all repositories owned by `nakkulla` and directly push template updates.
- Provide drift detection so template divergence is visible before and after sync.
- Protect existing repository-specific GitHub configuration from accidental deletion or overwrite.

## Non-goals

- Do not modify `pr-review-v4`; existing GitHub review thread collection already sees Gemini Code Assist review threads.
- Do not rely on Gemini Code Assist reading templates from `github-actions-shared` directly; rendered files must exist in each target repository.
- Do not create or move release tags as part of this work.
- Do not manage account-wide community health defaults that belong in `nakkulla/.github` unless explicitly included in a repository-local template profile later.
- Do not delete unmanaged `.github/` files in consumer repositories.

## Proposed repository layout

```text
github-actions-shared/
  templates/
    gemini/
      default/
        .gemini/
          config.yaml
          styleguide.md
      agent-workflow/
        .gemini/
          config.yaml
          styleguide.md
    github/
      default/
        .github/
          pull_request_template.md
          dependabot.yml
          workflows/
            pr-ci.yml
      agent-workflow/
        .github/
          workflows/
            pr-ci.yml

  profiles/
    default.json
    agent-workflow.json

  scripts/
    sync_repo_templates.py

  tests/
    template_contract_test.sh
    sync_repo_templates_test.py
```

The exact initial template set may be smaller than the layout above, but the directory structure should support both Gemini and GitHub templates from the start.

## Profile format and runtime dependencies

Profiles declare which template directories are layered together for a repository class. Profile files are JSON, not YAML, so the sync tool can stay Python-stdlib-only in this small repository. If a later implementation wants YAML, it must first add an explicit dependency source such as `pyproject.toml` plus deterministic install and test commands.

Example:

```json
{
  "name": "agent-workflow",
  "include": [
    "templates/gemini/default",
    "templates/gemini/agent-workflow",
    "templates/github/default",
    "templates/github/agent-workflow"
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

Layering order is deterministic: later includes override earlier includes when they render the same target path.

## Managed file manifest

Each synced repository should receive a manifest such as:

```json
{
  "source": "nakkulla/github-actions-shared",
  "profile": "agent-workflow",
  "source_ref": "<commit-sha>",
  "managed_files": [
    ".gemini/config.yaml",
    ".gemini/styleguide.md",
    ".github/workflows/pr-ci.yml",
    ".github/pull_request_template.md"
  ]
}
```

Suggested path:

```text
.github/shared-template-manifest.json
```

The sync tool may overwrite files listed in the manifest. It must not delete or overwrite unmanaged files unless the user explicitly adds those files to the profile or the manifest.

## First-sync adoption and collision handling

The first sync for a repository with no manifest must be conservative:

1. Render the selected profile into a temporary tree.
2. For each rendered target path:
   - if the target path does not exist, mark it as `add`;
   - if the target path exists with identical content, mark it as `adopt_unchanged`;
   - if the target path exists with different content, mark it as `collision`;
   - if the target path exists and is outside the allowed path roots, fail the run.
3. In `--dry-run`, report all adds, unchanged adoptions, and collisions.
4. In `--apply`, write adds and adopt identical existing files into the manifest.
5. In `--apply`, do not overwrite collisions unless the user passes an explicit adoption flag such as `--adopt-collisions`.
6. When `--adopt-collisions` is used, include the old file path and blob SHA in the report before overwriting it.
7. Never delete unmanaged files during first sync.

For repositories that already have a manifest, only paths listed in `managed_files` are automatically overwriteable. New template paths are treated like first-sync paths: add when absent, adopt when identical, and report as collision when different.

## Sync tool behavior

`scripts/sync_repo_templates.py` should support:

```bash
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --dry-run
python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --apply
```

Required behavior:

1. Resolve the target repository list from GitHub using `gh`.
2. Exclude archived repositories, forks, and the source repository by default.
3. Clone or update each target repository in a temporary workspace outside the source repository tree.
4. Read an optional repository-local override file, for example `.github/shared-template.json`.
5. Render profile templates into the target repository.
6. Compare rendered content with the current working tree.
7. In `--dry-run`, print a per-repository diff summary and make no remote changes.
8. In `--apply`, create a backup branch before pushing to the configured target branch.
9. Commit only template-managed changes.
10. Push directly to the target branch when all safety checks pass.
11. Report repositories skipped, changed, unchanged, failed, and backed up.

## Repository-local override

Consumer repositories may opt out of specific managed paths or add profile-specific notes:

```json
{
  "profile": "agent-workflow",
  "exclude_files": [".github/dependabot.yml"],
  "extra_ignore_patterns": ["vendor/**"]
}
```

Overrides should be intentionally narrow. They should not change global safety defaults such as unmanaged-file deletion protection.

## Gemini template baseline

The initial Gemini template should include:

- `.gemini/config.yaml` with review enabled, `MEDIUM` severity threshold, bounded maximum comments, draft PR review disabled by default, and ignore patterns for generated or local environment paths.
- `.gemini/styleguide.md` with common review priorities and profile-specific guidance.

For agent/workflow repositories, the style guide should emphasize:

- workflow contract correctness
- installer and runtime safety
- review and merge automation truthfulness
- shell/Git/data-loss risks
- minimal targeted changes over broad refactors

## GitHub template baseline

The initial `.github/` template should include a conservative subset of files that are safe across most repositories:

- pull request template
- consumer PR CI wrapper workflow
- optional Dependabot configuration only if the profile explicitly includes it

The consumer wrapper target, for example `.github/workflows/pr-ci.yml`, is distinct from this repository's reusable workflow source `.github/workflows/reusable-pr-ci.yml`. The wrapper should call the reusable workflow rather than rename or replace the shared workflow source.

Even though the user wants full `.github` synchronization, the implementation should treat full `.github` as a managed namespace rather than a delete-and-replace directory. Existing unmanaged files remain intact until explicitly adopted into the manifest.

## Safety model

Direct push is allowed, but only with guardrails:

- default dry-run mode
- explicit `--apply` required for writes
- clean temporary worktree required before rendering
- path allowlist limited to `.gemini/**`, `.github/**`, and the manifest
- no deletion of unmanaged files
- backup branch before direct push
- per-repository commit with a consistent Korean commit message
- final report that includes pushed refs and backup refs

If a target repository has branch protection that rejects direct push, the tool should report it as `push_rejected` and leave the local temporary checkout for inspection or cleanup according to a documented flag.

## Verification

Local verification should include:

- `bash tests/reusable_pr_ci_contract_test.sh`
- `bash tests/template_contract_test.sh`
- `python3 tests/sync_repo_templates_test.py`
- `python3 scripts/sync_repo_templates.py --profile agent-workflow --owner nakkulla --dry-run --limit 1` using a safe read-only path when credentials are available

The contract tests should verify:

- required template files exist
- profile include paths exist
- profile and repository override JSON parse with Python stdlib `json`
- rendered paths stay under `.gemini/`, `.github/`, or the manifest path
- manifest generation is deterministic
- first-sync collision handling blocks overwrites by default
- unmanaged file deletion is blocked
- dry-run does not mutate target repositories

## Rollout plan

1. Add template directories, initial profiles, sync script skeleton, and contract tests.
2. Run local contract tests.
3. Run owner-wide dry-run and review the report.
4. Apply to one low-risk repository first.
5. Verify the target repository diff and CI.
6. Apply to the remaining repositories in batches.
7. Keep `pr-review-v4` unchanged unless future evidence shows Gemini threads are not being collected or classified correctly.

## Acceptance criteria

- `github-actions-shared` contains canonical `.gemini/` and `.github/` templates.
- At least one profile can render the initial template set.
- The sync tool supports dry-run and direct-push apply modes.
- Direct-push mode creates a backup branch before updating a target branch.
- The sync tool never deletes unmanaged `.github/` or `.gemini/` files.
- Contract tests cover template existence, profile resolution, manifest behavior, and dry-run safety.
- README documents how to run dry-run and apply sync.
