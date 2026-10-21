# Should this skill become a mod?

Contents: the core question · three tests · comparison · alternatives · costs · worked verdicts ·
what to ask the user

## The core question

If Claude reading these instructions *when it judges them relevant* is enough, it is a skill and
should stay one. A mod is justified only when the behaviour has to happen **at a moment Claude does
not control**, or needs a **face** outside the chat, or has to **intercept** something. Everything
else is cheaper, safer and more portable as a skill.

## Three tests

1. **Moment test.** Can you complete "when ___ happens, do ___" with an event Claude Code actually
   fires? Candidates: a Bash command about to run (`tool.call`), a file edited (`tool.call` on
   Edit/Write), a prompt submitted (`prompt.submit`), a skill expanded (`skill.prompt`), a turn
   finished (`turn.complete`), a session starting (`session.start`), context usage changing
   (`session.measure`), a conversation about to be compacted (`session.compact`). If you cannot name
   the event, there is no mod.
2. **Reliability test.** Would it matter if Claude simply did not load the skill this time? If the
   answer is "no, it would reach for it anyway", the skill's description is doing its job; improve it
   with `tune-skill`. If the answer is "yes, a missed run is costly" (pre-release checks, secret
   scans, handoffs), a trigger earns its place.
3. **Face test.** Does the person need to see or press something outside the chat: a pane, a band
   above the prompt, a status line, a toast, a slash command that runs code without a model turn?
   Skills cannot draw. Mods can.

Zero passes: **KEEP_SKILL**. A moment but plenty of real instruction: **HYBRID**. A face, or a moment
with almost no instruction behind it: **MOD_FIRST**.

## What each mechanism is for

| | Mod | Settings hook | Skill | MCP server |
| --- | --- | --- | --- | --- |
| What it is | Functions in a plugin that run inside Claude Code | A shell command, HTTP call or prompt run on a lifecycle event | A `SKILL.md` Claude reads | A process that gives Claude tools |
| Can change | Tool calls, prompts, commands, turns, what is drawn | Whether a call or prompt goes ahead, its arguments and result | What Claude knows and does | Which tools Claude has |
| Can draw | Yes | No | No | No |
| Written in | JavaScript or TypeScript | A script plus a settings entry | Markdown | Any language |
| Pick it when | You want a pane, band, command or to rewrite an event | You already have a script that should block or log an event | You keep pasting the same instructions | Claude must reach an outside system |

A plugin can hold all four, so a mod can ship beside the skill it triggers.

## Alternatives that often beat a mod

- A fixed script that must run on an event, with no UI: a **settings hook**. It runs outside Claude
  Code's process and is easier to audit.
- A rule that should always apply: **CLAUDE.md**. No trigger needed.
- Reaching GitHub, a database or an API: an **MCP server**.
- Enforcement across a team: **permission rules or managed settings**, not a mod that reads
  command text.
- A skill that is simply not firing: fix its description with **tune-skill**.

## Costs a mod carries

- **Unsandboxed.** It runs as the user: it can read files and environment variables (which can hold
  API keys), start processes and make network requests if it calls those APIs. Sandboxing covers the
  Bash commands Claude runs, not a process a mod starts. Every `$` call is something the installer
  must be willing to read. This is why the generated mods call only `$.ui.*` and
  `$.command.register`.
- **Moving API.** Events and methods can change between releases. Record the tested version, and
  prefer the type files for the installed build over any written reference.
- **Surfaces differ.** See "Honest limits" in `SKILL.md`.
- **Admin control.** Organisations can stop user-installed mods from loading; a mod must degrade
  gracefully, and the skill inside the plugin still works.
- **A mod cannot change the permission prompt.** It can approve or deny tool calls through hooks,
  which is exactly the power to avoid using on a user's behalf.

## Worked verdicts

**`wordsmith`** (write in a clear, warm voice; style guide, examples, workflow). No moment, no face:
all guidance. **KEEP_SKILL.** If it is not triggering when someone drafts an email, fix the
description. A mod would add risk and nothing else.

**`release-gate`** (run a checklist before pushing, deploying or publishing; also on "ship it").
A moment (a ship command), a reliability problem (a skipped gate is costly), real instruction (the
checklist). **HYBRID.** Mod: hold a ship command until the skill has run since the last edit; one line
of context when the prompt says "ship it". Skill: unchanged, bundled.

**`context-guardian`** (a live panel of context usage; warn before compaction; hand off). A face and
moments (`session.measure`, `session.compact`) with almost no instruction text behind them.
**MOD_FIRST.** Hand-written; the nearest sample is Anthropic's `token-weather`.

## What to ask the user

At most one question, and only when the answer changes the build. Good ones: "Which commands count
as shipping here: only `git push`, or deploys too?" or "Should it block, or only remind?". If a
sensible default exists, take it and say so. Never ask whether to proceed.
