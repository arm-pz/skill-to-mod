# Mod contract (verified against Claude Code 2.1.306, October 2026)

Contents: layout · hook shapes · matchers · static-analysis rules · failure behaviour · limits ·
surfaces · state · tests · sources

Mods are young and the API moves. When anything here disagrees with the type files Claude Code
writes into `<mod>/.claude-plugin/types/` (or the built-in `plugin-authoring` skill's types), the
types win.

## Layout

A mod is a plugin with a hooks module. `hooks/hooks.json` naming one code file under `modules` is
what makes it a mod.

```
my-mod/
├── .claude-plugin/plugin.json     required; mods add no required fields
├── hooks/hooks.json               { "modules": ["./register.js"] }   one path, relative to this file
├── hooks/register.js              exports register(on, options); .js .mjs .cjs .jsx .ts .mts .cts .tsx
├── skills/<name>/SKILL.md         optional: a plugin can hold skills, commands, agents and MCP servers too
├── types/index.d.ts               only when using $.state or adding to the API ("types" in plugin.json)
└── tests/*.test.ts                run by `claude plugin test`
```

The module is an ES module whatever its suffix, with no Node or DOM APIs. `userConfig` fields in
`plugin.json` arrive as the second argument to `register`, defaults filled in. A string field
with `options` becomes a picker in the `/config` menu, and users can also set any field with
`/plugin configure <plugin>@<marketplace>`.

## Hooks

`on(event, matcher?, hook)` registers a hook. Every hook is `async ($, e, next) => result`:

- `$` the mods API, every call written in full as `$.namespace.method(...)`.
- `e` the event input, deeply frozen. Change it by passing a copy to `next`.
- `next(e)` runs the hooks after this one, then Claude Code's own behaviour, and resolves to the
  event's result. A hook that returns without calling `next` answers for itself.

Return shapes used by the scaffold:

| Event | Fires when | A hook may return |
| --- | --- | --- |
| `tool.call` | a tool is about to run | `next(e)`; `{ deny: 'reason' }` (Claude reads the reason as the result); `{ result }`; after `await next(e)`, the result with extra `context: [..]` lines (read by Claude after the result, never shown to the user) |
| `skill.prompt` | a skill's text is expanded: typed as `/name`, run by the Skill tool, or preloaded into a subagent | `next(e)`, or `{ text }`. `e.skill` is the name, `plugin:name` for a plugin's skill |
| `prompt.submit` | a prompt is submitted | `next(e)`; `next({ ...e, text })`; `next({ ...e, context: [...(e.context ?? []), line] })`; `{ drop: reason }` |
| `command.run` | a registered `/command` runs | `{ text }`, `{}`, or `next(e)`. Registered in `session.start` with `$.command.register({ name, description, argumentHint?, immediate? })` |
| `session.start` | once per mod before the first prompt and after a reload | `next(e)` |
| `turn.complete` | a turn ended | `next(e)` or `{ text }` (a line under the answer) |
| `session.measure` | after each turn and when usage moves | observe only; `e.context` holds the window fill |
| `session.compact` | before compaction | `{ skip: reason }` or pass through |
| `ui.render` | a render site is about to be drawn | a tree, or `next(e)`; see patterns.md |

`tool.call` carries the tool's arguments as fields of `e` (`e.command` for Bash, `e.file_path` for
Edit/Write). A call's result is `{ result }`, `{ deny }`, or with an error `isError: true`.

## Matchers

The optional second argument filters events by field: a value, an array, or a regular expression
(`{ tool: 'Bash' }`, `{ tool: ['Edit', 'Write'] }`, `{ tool: /^mcp__github__/ }`). Register an event
only once per matcher: two `on('session.start', ...)` calls with no matcher fail to load, so put all
start-up work in one hook.

## Static-analysis rules

`claude plugin validate` reads the source and refuses what it cannot analyse. Follow these:

1. Event names in `on(...)` are string literals, not variables.
2. Write every API call in full (`$.ui.status(...)`). Do not alias `$` or a namespace
   (`const ui = $.ui` fails), destructure it, or index it with a computed name.
3. Passing `$` is only allowed to a function declared at the top level of the same file.
4. Import only your own files by relative path (plus the bare `claude-code` import), with `import`
   declarations at the top. No `require`, no dynamic `import()`.
5. Do not declare a second variable or parameter called `on` inside `register`.
6. Do not nest scopes more than about 2,000 deep (irrelevant in practice).

`validate` prints `hooks:` and `calls:` lines: the events the module hooks and every `$` method it
calls. That is the trust surface. Print it for the user.

## Failure behaviour

A hook that throws, times out or returns the wrong shape does not break the session. If it failed
before calling `next`, Claude Code skips it and the next handler runs; if it failed after `next`
resolved, that result stands. To decide what happens instead, attach `.catch`:

```js
on('tool.call', { tool: 'Bash' }, guard).catch(($, e, next) => next(e))   // fail open
on('tool.call', { tool: 'Bash' }, guard).catch(($, e, next) =>            // fail closed
  next.called ? next(e) : { deny: 'The guard failed, so this command was not run.' })
```

Inside `.catch`, `next.error.kind` is `throw`, `timeout` or `re-entry`. Advisory mods fail open;
only a true guard fails closed, and a guard that can fail closed must be very reliable.

## Limits that bite

- A hook has **10 seconds** of its own time per event (50 ms for `prompt.edit`). Time spent inside
  `$` calls does not count, except `$.clock.sleep`. So `await $.ui.ask(...)` can wait on a person.
- A `.catch` handler has 1 second.
- `$.process.run` defaults to 30 s (max 10 min); `$.http.fetch` 30 s and 4 MiB; `$.fs` 4 MiB a file.
- `$.ui.invalidate('ui.render')` redraws are throttled to about 10 a second.
- Names of commands, tools and panes: letters, digits, `_`, `-`, up to 64 characters. A command may
  not reuse a built-in name.

## Where mods run

| Where | Hooks run | What a mod draws shows |
| --- | --- | --- |
| `claude` in a terminal | yes | yes |
| Desktop app Code tab (not WSL) | yes | yes, except terminal-only elements |
| Desktop app WSL session | no (no plugins) | no |
| VS Code chat panel | yes | extension 2.1.299+ with feature flags fetched |
| `claude -p` and the Agent SDK | yes | no |
| Cloud session | yes, if the plugin reaches it | no |

Mods are on by default from 2.1.287. `--safe-mode` or `"disableAllHooks": true` turns installed mods
off. Organisation managed settings (`allowManagedModsOnly`, `allowManagedHooksOnly`,
`prependPlugins`, `appendPlugins`) can restrict or order them, and a built-in guard
(`sec-default@builtin`) loads first for managed users. A mod cannot change what the permission
prompt shows.

## State

- Module variables: until the module reloads (every file save in development).
- `$.state`: the session, survives reloads, redraws readers. Needs a `types/index.d.ts` contract.
- `$.store`: JSON key-value, shared across sessions on the machine, persists. `get`/`set` are not
  atomic across sessions.

## Tests

Run with `claude plugin test <folder>`; files end `.test.ts`. Import `test`, `expect`, `mock` from
`claude-code/testing`. Each test gets `($, on)`: `$` raises events through your hooks
(`$.tool.call({ tool: 'Bash', command })`, `$.skill.prompt({ skill, text })`,
`$.prompt.submit({ text })`, `$.command.run({ command, args })`), and `on` registers stubs that
stand in for Claude Code beneath the mod.

- Every `$` call the mod makes needs a stub: `on('ui.status', () => ({ value: undefined }))`.
  A missing stub shows as "no implementation for ...".
- A bottom stub for `tool.call` returns `{ result: 'ok' }`. A deny from the mod arrives as
  `{ deny: '...' }`.
- `$.ui.ask` reaches a `tool.call` stub as an `AskUserQuestion` call:
  `({ result: { answers: { [e.questions[0].question]: 'Ship anyway' } } })`.
- Options for `userConfig` come as `test(name, { options: { mode: 'block' } }, body)`.
- Register stubs before the first call on `$`. Each test starts with the module freshly loaded.

## Sources

Mods overview, create, events, API, interface, test and reference pages under
`https://code.claude.com/docs/en/plugins/mods/`, and the type declarations at
`https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts`. Anthropic's own
mods are public in the `mods/` folder of `anthropics/claude-code` and
`claude-code/mods/` of `anthropics/claude-code-playground`.
