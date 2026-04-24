# github-actions-shared Bootstrap Design

`nakkulla/github-actions-shared` owns reusable GitHub Actions workflow source files for future consumer repositories.

## Scope

- Own `.github/workflows/reusable-pr-ci.yml`.
- Preserve the `workflow_call` contract.
- Provide local contract verification before `@v1` promotion.

## Non-goals

- Do not migrate consumers in this repository bootstrap.
- Do not own account-wide community health defaults; those belong in `nakkulla/.github`.

## Acceptance

- `bash tests/reusable_pr_ci_contract_test.sh` passes.
- README documents future `@v1` usage and promotion criteria.
