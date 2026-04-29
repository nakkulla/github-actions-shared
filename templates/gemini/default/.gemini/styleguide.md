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
