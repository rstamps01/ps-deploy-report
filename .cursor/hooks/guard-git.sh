#!/bin/bash
# beforeShellExecution guardrail for `git commit` / `git push` (agent commands).
#
#   BLOCK on: version-sync mismatch; secrets in staged changes (gitleaks if
#             installed, else a private-key fallback scan).
#   ASK on:   direct commit/push to main/master; new files landing outside the
#             repo-structure-17 standard.
#
# Fails OPEN (allow) on any internal error so it never wedges the agent.
# Real commits are additionally guarded by .pre-commit-config.yaml.
set -uo pipefail

allow() { echo '{"permission":"allow"}'; exit 0; }

input=$(cat 2>/dev/null) || allow
command=$(printf '%s' "$input" | jq -r '.command // empty' 2>/dev/null) || allow

# Only act on git commit / git push.
printf '%s' "$command" | grep -Eq '(^|[^[:alnum:]_])git[[:space:]]+(commit|push)' || allow

root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
cd "$root" 2>/dev/null || allow

blocks=""
warns=""

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    warns="${warns}- Direct git commit/push on '$branch' — changes should flow through 'develop' (change-control-07).\n"
fi

# Version-sync (block on mismatch) — only for commits.
if printf '%s' "$command" | grep -Eq 'git[[:space:]]+commit' && [ -f scripts/check-version-sync.sh ]; then
    if ! bash scripts/check-version-sync.sh >/dev/null 2>&1; then
        blocks="${blocks}- Version strings are out of sync (scripts/check-version-sync.sh failed). Reconcile every version location to src/app.py APP_VERSION.\n"
    fi
fi

# Secrets.
if command -v gitleaks >/dev/null 2>&1; then
    if ! gitleaks protect --staged --no-banner >/dev/null 2>&1; then
        blocks="${blocks}- gitleaks detected potential secrets in staged changes. Remove them before committing.\n"
    fi
elif git diff --cached -U0 2>/dev/null | grep -Eq 'BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY'; then
    blocks="${blocks}- A private key appears in staged changes. Remove it before committing.\n"
fi

# Structure warn: newly added files outside the repo-structure-17 standard.
while IFS=$'\t' read -r status path; do
    [ "$status" = "A" ] || continue
    case "$path" in
        docs/releases/*) : ;;
        RELEASE_NOTES_v*.md|*/RELEASE_NOTES_v*.md)
            warns="${warns}- New release note '$path' should live under docs/releases/ (repo-structure-17).\n" ;;
        */*) : ;;  # non-root, non-release-note: fine
        README.md|CHANGELOG.md|AGENTS.md|requirements*.txt|pyproject.toml|Makefile|LICENSE*|.*|*.cfg|*.toml|*.ini) : ;;
        *)
            warns="${warns}- New top-level file '$path' — repo root should hold only config + entry docs (repo-structure-17). Consider a subdirectory.\n" ;;
    esac
done < <(git diff --cached --name-status 2>/dev/null)

if [ -n "$blocks" ]; then
    msg=$(printf "Blocked by pipeline guardrail:\n%b" "$blocks")
    jq -n --arg m "$msg" '{permission:"deny", user_message:$m, agent_message:$m}'
    exit 0
fi
if [ -n "$warns" ]; then
    msg=$(printf "Pipeline guardrail warning:\n%bProceed anyway?" "$warns")
    jq -n --arg m "$msg" '{permission:"ask", user_message:$m, agent_message:$m}'
    exit 0
fi
allow
