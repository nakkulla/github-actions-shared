# Gemini Code Assist Review Guide

Review this repository as an AI tooling, workflow, and automation repository.

## Review priorities

Focus on issues that can cause real workflow failures:

1. Incorrect or unsafe agent instructions.
2. Broken install scripts, generated instruction output, hooks, or symlink/copy behavior.
3. Changes that mutate live runtime directories from a worktree.
4. Missing or incorrect verification steps for changed scripts, skills, rules, workflows, or installers.
5. Regressions in Beads, PR review, skill, Codex, Claude, or GitHub Actions workflow contracts.
6. Security or data-loss risks, especially shell scripts, Git operations, secrets, credentials, and destructive commands.

## Repository-specific rules

- Prefer minimal, targeted changes that preserve existing conventions.
- Treat `.github/`, `.gemini/`, `shared/`, `codex/`, `claude/`, `shell/`, `scripts/`, and install scripts as high-impact areas when present.
- Do not suggest editing generated installed files under `~/.codex`, `~/.claude`, or `~/.config`; source files in the repository are the source of truth.
- Do not suggest running install scripts from a git worktree against live user configuration.
- For docs-only changes, avoid demanding runtime install verification unless the docs affect install/runtime behavior.

## What to comment on

Leave comments for:

- Bugs, contradictions, or stale workflow guarantees.
- Missing verification when a changed file clearly needs it.
- Incorrect path assumptions, especially skill-relative paths, workflow paths, and install target paths.
- Unsafe shell behavior, unquoted variables, destructive Git commands, or accidental broad file operations.
- Review/merge automation that could claim success without current-run evidence.

## What not to comment on

Avoid comments for personal preferences, pure formatting, unrelated architecture suggestions, generated files, and abstraction requests that are not needed for the pull request.
