#!/usr/bin/env bash
set -euo pipefail

workflow='.github/workflows/reusable-pr-ci.yml'

test -f "$workflow"
grep -q '^name: Reusable PR CI$' "$workflow"
grep -q '^on:$' "$workflow"
grep -q '^  workflow_call:$' "$workflow"
grep -q '^  baseline:$' "$workflow"
grep -q 'uses: actions/checkout@v4' "$workflow"
grep -q 'uses: actions/setup-python@v5' "$workflow"
grep -q "python-version: '3.11'" "$workflow"
grep -q 'reviewdog/action-actionlint@v1' "$workflow"

if command -v actionlint >/dev/null 2>&1; then
  actionlint "$workflow"
else
  echo 'SKIP: actionlint not installed'
fi

echo 'PASS: reusable pr ci contract'
