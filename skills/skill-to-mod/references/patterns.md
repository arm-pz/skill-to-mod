# Patterns: from a skill's behaviour to a hook

Contents: behaviour-to-hook table · scaffolded patterns · hand-written recipes · sample mods

## Behaviour to hook

| The skill says... | Hook | Typical action | Calls it needs |
| --- | --- | --- | --- |
| "before pushing / deploying / publishing / deleting..." | `tool.call` on `{ tool: 'Bash' }` | `$.ui.ask`, or `{ deny }` with an instruction Claude can act on, or `context` after the result | `$.ui.ask`, `$.ui.toast`, `$.ui.status` |
| "after you edit..." / "whenever files change" | `tool.call` on `{ tool: ['Edit', 'Write'] }`, acting after `await next(e)` | mark state stale, show a status line | `$.ui.status` |
| "when the user says X" / "if they mention Y" | `prompt.submit` | add one line to `context`; never rewrite their text silently | none |
| "run /thing" with no model turn | `command.run` | return `{ text }` | `$.command.register` |
| "at the end of each turn..." | `turn.complete` | return `{ text }` (a line under the answer) | none |
| "when a session starts" | `session.start` | register commands, load saved settings | `$.command.register`, `$.store.get` |
| "when the context fills / before compaction" | `session.measure`, `session.compact` | toast, status line, or `{ skip: reason }` | `$.ui.toast`, optionally `$.session.usage` |
| "show a live panel / status / banner" | `ui.render` on `Pane` or `AbovePrompt`, `$.ui.open`, `$.ui.status` | draw an element tree | `$.ui.*` |
| "ask the model to judge X" | `$.model.complete({ model: 'haiku', prompt, maxTokens })` | check `r.isAnswered` first | `$.model.complete` (spends the user's usage: say so) |
| "keep notes between sessions" | `$.store` | small JSON | `$.store.get`, `$.store.set` |

Anything in the right-hand column beyond `$.ui.*`, `$.command.register` and `$.store` widens the
trust surface. Say so to the user and justify it.

## The three scaffolded patterns

**gate**: `tool.call` (Bash) + `skill.prompt` + optional `tool.call` (Edit/Write).
- `skill.prompt` records which required skills have been expanded.
- An edit, if `staleOnEdit` is on, clears the record: checks go stale.
- A Bash command matching a `match` entry while required skills are outstanding is handled by
  `mode`: `ask` (a question with "Run checks first" / "Ship anyway"; a question nobody answers counts
  as "Run checks first"), `block` (deny with an instruction), `nudge` (run, then add `context`),
  `off`.
- After `maxHolds` holds it lets the command through and shows a toast, so a missing skill can never
  trap a session.
- `.catch` on every hook fails open.

**prime**: `prompt.submit`. When a prompt matches a phrase, one line of `context` tells Claude which
skill applies. With a gate it fires only while checks are outstanding.

**command**: `/name` registered in `session.start`, answered by `command.run`. Shows state;
`off`/`on` snoozes for the session.

Reference implementation with tests: the `ship-sentinel` plugin, which is this scaffold with
several required skills.

## Hand-written recipes

Load `/plugin-authoring` first for the installed version's exact API, then adapt:

- **Context watcher.** `on('session.measure', ...)` reads `e.context` (the window and its fill) and
  calls `$.ui.toast` once when it crosses a threshold; keep a module flag so it fires once. Call
  `$.session.usage()` only if you need more. Nearest sample: Anthropic's `token-weather`.
- **Handoff before compaction.** `session.compact` can return `{ skip: reason }`; `$.session.compact`
  starts one; `$.model.fork({ prompt })` writes a brief from the current conversation, and
  `$.fs.write` stores it. That is three powerful calls (model, file, compaction): state them plainly.
  Existing open-source handoff mods already cover this ground, so check what exists first.
- **Status line.** `$.ui.status(text)` from any hook; `undefined` clears it. Cheapest "face" there is.
- **Band above the prompt.** `on('ui.render', { component: 'AbovePrompt' }, ($, e, next) => tree | next(e))`
  with `const { Box, Text } = $.ui.resolve(e)`; call `$.ui.invalidate('ui.render')` after state changes.
- **Pane.** `$.ui.open({ id, title })` from a command, drawn by `on('ui.render', { component: 'Pane' }, ...)`
  that checks `e.requestId === id`. It resolves `{ isPlaced }`: if a narrow terminal will not place it,
  draw the same content in the band.
- **Hold a command with buttons.** Anthropic's `blast-radius` holds a risky Bash command, opens a
  pane with Proceed / Cancel, and denies on cancel. Note it uses `$.process.run` to measure the
  damage; that is a larger trust surface than the gate pattern.

## Sample mods worth reading

Anthropic's public examples, each a complete plugin with tests:

- `claude-code-playground/claude-code/mods/`: `token-weather` (a forecast of the context window above
  the prompt), `blast-radius` (holds risky commands and shows what they would change),
  `replay-theater` (a `/replay` command that steps through the last turn's edits).
- `claude-code/mods/`: built-in `diff` (a pane with keyboard-bound buttons), `agents-md` (loads
  AGENTS.md, with a `userConfig` option), `sec-default` (a policy guard), `telemetry`.
