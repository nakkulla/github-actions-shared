# github-actions-shared

Shared reusable GitHub Actions workflows for repositories owned by `nakkulla`.

## Current workflows

- `.github/workflows/reusable-pr-ci.yml` — baseline PR CI workflow intended for future use as:

  ```yaml
  jobs:
    baseline:
      uses: nakkulla/github-actions-shared/.github/workflows/reusable-pr-ci.yml@v1
  ```


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

## Release policy

Do not create or move the `v1` tag until:

1. `bash tests/reusable_pr_ci_contract_test.sh` passes locally.
2. The repository's GitHub Actions smoke run is green.
3. The caller/cutover plan in `dotfiles` explicitly moves consumer wrappers from `nakkulla/dotfiles@main` to `nakkulla/github-actions-shared@v1`.

Until then, existing dotfiles consumers should keep using the Phase 1 compatibility path.
