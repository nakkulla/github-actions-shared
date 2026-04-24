# github-actions-shared

Shared reusable GitHub Actions workflows for repositories owned by `nakkulla`.

## Current workflows

- `.github/workflows/reusable-pr-ci.yml` — baseline PR CI workflow intended for future use as:

  ```yaml
  jobs:
    baseline:
      uses: nakkulla/github-actions-shared/.github/workflows/reusable-pr-ci.yml@v1
  ```

## Release policy

Do not create or move the `v1` tag until:

1. `bash tests/reusable_pr_ci_contract_test.sh` passes locally.
2. The repository's GitHub Actions smoke run is green.
3. The caller/cutover plan in `dotfiles` explicitly moves consumer wrappers from `nakkulla/dotfiles@main` to `nakkulla/github-actions-shared@v1`.

Until then, existing dotfiles consumers should keep using the Phase 1 compatibility path.
