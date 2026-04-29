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
