#!/usr/bin/env bash
# Create GitHub milestones (M0–M5), track labels, and one issue per task in
# docs/03-development/tasks.md, assigned to the task owner.
#
# Usage:  scripts/create-issues.sh [--dry-run]
#   --dry-run  print the gh commands without calling GitHub
# Needs: gh (authenticated, run inside the repo), awk.
# Safe to re-run: existing milestones, labels and issues (matched by task ID) are skipped.
set -euo pipefail

# Replace with real GitHub usernames before running for real.
RAMIL_GH="<ramil-gh>"
CARLO_GH="<carlo-gh>"
CLIFF_GH="<cliff-gh>"
PATRICK_GH="<patrick-gh>"

DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

cd "$(git rev-parse --show-toplevel)"
TASKS=docs/03-development/tasks.md
[[ -f "$TASKS" ]] || { echo "Missing $TASKS" >&2; exit 1; }

if [[ $DRY == 0 ]]; then
  for u in "$RAMIL_GH" "$CARLO_GH" "$CLIFF_GH" "$PATRICK_GH"; do
    [[ "$u" == *"<"* ]] && { echo "Edit the *_GH placeholders at the top of $0 first." >&2; exit 1; }
  done
  command -v gh >/dev/null || { echo "gh CLI not found" >&2; exit 1; }
fi

run() {
  if [[ $DRY == 1 ]]; then printf '%q ' "$@"; echo; else "$@"; fi
}

owner_gh() {
  case "$1" in
    Carlo) echo "$CARLO_GH" ;; Cliff) echo "$CLIFF_GH" ;; Patrick) echo "$PATRICK_GH" ;;
    *) echo "Unknown owner '$1'" >&2; exit 1 ;;
  esac
}
owner_label() {
  case "$1" in
    Carlo) echo "track:client" ;; Cliff) echo "track:gameplay" ;; Patrick) echo "track:platform" ;;
  esac
}

# --- Parse tasks.md: one record per task, fields separated by \037 -----------------
# milestone | task id | title | owner | body (newlines encoded as \n)
parse() {
  awk '
    function flush() { if (id != "") printf "%s\037%s\037%s\037%s\037%s\n", ms, id, title, owner, body; id = "" }
    /^## M[0-9]/ { flush(); ms = substr($0, 4); next }
    /^## / { flush(); ms = ""; next }
    ms != "" && /^- \[[ x]\] \*\*T-/ {
      flush()
      line = $0
      s = index(line, "**") + 2
      rest = substr(line, s)
      head = substr(rest, 1, index(rest, "**") - 1)
      sub(/\.$/, "", head)
      id = head; sub(/ .*/, "", id)
      title = head
      owner = ""
      if (match(line, /Owner: [A-Za-z]+/)) owner = substr(line, RSTART + 7, RLENGTH - 7)
      body = line
      next
    }
    id != "" && /^  / { body = body "\\n" $0; next }
    id != "" && /^$/ { next }
    { flush() }
    END { flush() }
  ' "$TASKS"
}

RECORDS="$(parse)"
[[ -n "$RECORDS" ]] || { echo "No tasks parsed from $TASKS" >&2; exit 1; }

# --- Milestones ----------------------------------------------------------------
existing_ms=""
[[ $DRY == 0 ]] && existing_ms="$(gh api 'repos/{owner}/{repo}/milestones?state=all&per_page=100' --paginate -q '.[].title')"
while IFS= read -r ms; do
  [[ -z "$ms" ]] && continue
  if grep -qxF "$ms" <<<"$existing_ms"; then echo "skip milestone: $ms"; continue; fi
  run gh api 'repos/{owner}/{repo}/milestones' -f "title=$ms" --silent
done < <(cut -d $'\037' -f1 <<<"$RECORDS" | awk '!seen[$0]++')

# --- Labels ----------------------------------------------------------------------
run gh label create "track:client"   --color 1D76DB --description "Game client (Carlo)"    --force
run gh label create "track:gameplay" --color 0E8A16 --description "Sim and screens (Cliff)" --force
run gh label create "track:platform" --color 5319E7 --description "Platform (Patrick)"     --force
run gh label create "spec-change"    --color FBCA04 --description "Change to docs/ specs"  --force

# --- Issues ----------------------------------------------------------------------
existing_issues=""
[[ $DRY == 0 ]] && existing_issues="$(gh issue list --state all --limit 1000 --json title -q '.[].title')"
count=0
while IFS=$'\037' read -r ms id title owner body; do
  if [[ -z "$owner" ]]; then echo "WARN: $id has no Owner, skipped" >&2; continue; fi
  if grep -q "^$id " <<<"$existing_issues"; then echo "skip issue: $id"; continue; fi
  body="${body//\\n/$'\n'}"
  body+=$'\n\n'"Source: \`$TASKS\` · Reviewer: $RAMIL_GH"
  run gh issue create \
    --title "$title" \
    --body "$body" \
    --milestone "$ms" \
    --label "$(owner_label "$owner")" \
    --assignee "$(owner_gh "$owner")"
  count=$((count + 1))
done <<<"$RECORDS"

echo "Done: $count issue(s) $([[ $DRY == 1 ]] && echo 'would be ')created."
