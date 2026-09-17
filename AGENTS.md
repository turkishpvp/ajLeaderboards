# AGENTS.md

## Repo

- Project: `ajLeaderboards`
- Type: shared plugin repo

## Default workflow

1. Read repo structure before editing.
2. Prefer smallest working diff.
3. Reuse existing patterns, utilities, and config style.
4. Run the smallest relevant verification after edits.
5. If user wants publish, commit and push only after verification.

## Headroom

Use Headroom for long sessions and large repo/tool output.

- Preferred start: `headroom wrap codex`
- If this repo has repo-local Headroom scripts, prefer them over generic commands.
- Keep repo state inspectable:
  - check logs
  - check memory usage
  - compact context when conversation gets long

Use SharedContext-style handoffs for long investigations:

- `caveman` label for terse compressed handoff
- `ponytail` label for stripped implementation handoff
- `codex` label for normal handoff

## Caveman

Use only when brevity is the goal.

- Good for short summaries
- Good for compact handoff notes
- Do not keep always-on if it hurts clarity

## Ponytail

Use when simplifying code or avoiding over-engineering.

- Prefer deletion over abstraction
- Prefer stdlib over new dependency
- Prefer one shared fix over many caller-side patches

Do not force Ponytail on every task. Use it when simplification is the point.

## Token discipline

- Read targeted files, not whole repo, unless necessary
- Prefer `rg` and focused file reads
- Avoid huge log dumps
- Summarize command output instead of replaying it
- Keep tool output bounded
- Compact long sessions before big refactors

## Java plugin workflow

For code changes in this repo:

1. Inspect `src`, build file, and plugin descriptors first
2. Trace affected command, listener, service, or config path end to end
3. Fix root cause in shared path when possible
4. Run the smallest relevant verification:
   - Gradle: relevant task if Gradle exists
   - Maven: relevant task if Maven exists
   - otherwise static inspection plus compile command if available

## Config changes

Before editing config-driven behavior:

1. Find the owning config file
2. Read nearby related configs
3. Change the minimum set of keys
4. State whether restart or reload is required

## Publish gate

If user asks for shipped work or Trello-style test-ready flow:

1. Implement fix
2. Verify locally as far as repo allows
3. Commit with short English message
4. Push current working branch
5. Report what changed and what remains to verify


## Trello MCP

This repo has a project-scoped Trello MCP server in `.codex/config.toml`.

Rules:

- Do not try to run `trello_*` names as shell commands.
- Use Trello MCP tools instead.

Available tools:

- `trello_whoami`
- `trello_list_boards`
- `trello_get_board`
- `trello_list_lists`
- `trello_get_list`
- `trello_create_list`
- `trello_update_list`
- `trello_list_cards`
- `trello_search_cards`
- `trello_get_card`
- `trello_create_card`
- `trello_update_card`
- `trello_list_card_comments`
- `trello_add_card_comment`
- `trello_get_card_activity`

Preferred flow:

1. Use `trello_whoami` to validate auth if needed.
2. Use `trello_list_boards` before asking for board id.
3. Use `trello_list_lists(board_id=...)` before asking for list id.
4. Use `trello_list_cards(list_id=...)` to read cards.
5. Use `trello_create_card(...)` or `trello_update_card(...)` for changes.

If Trello credentials are missing or invalid, say that the Trello MCP server is configured but authentication needs to be fixed.
