# github-actions-shared Bootstrap Plan

1. Create `.github/workflows/reusable-pr-ci.yml` from the current dotfiles Phase 1 source.
2. Add `tests/reusable_pr_ci_contract_test.sh`.
3. Run `bash tests/reusable_pr_ci_contract_test.sh`.
4. Commit and push the initial repository.
5. Defer `v1` tag creation until local and GitHub Actions smoke checks are green.
