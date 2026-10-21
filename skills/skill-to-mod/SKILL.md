---
name: skill-to-mod
description: Decide whether an existing agent skill should become a Claude Code mod (code that runs inside Claude Code on events like tool calls, prompts, turns and compaction), and if it should, convert it into a validated mod plugin that keeps the original skill bundled. Use whenever the user wants to turn a skill into a mod, "mod-ify" a skill, make a skill run automatically before git push or deploys or on every prompt or after edits, give an existing skill a pane, status line, band or slash command, or asks "can this skill be a mod?", "should this be a mod or a skill?", even if they never say "hooks". Needs Claude Code 2.1.287 or later. Not for writing a brand-new mod with no source skill (use plugin-authoring), writing a new skill (use draft-skill), improving a skill's wording or triggering (use tune-skill), or plain skill packaging (use skill-creator).
---

# Skill to Mod

A skill is instructions Claude reads when it decides they are relevant. A mod is code that runs
inside Claude Code and fires on events, such as a tool call about to run, a prompt being
submitted, a turn ending, or the context filling. Turning a skill into a mod therefore means
giving it a **trigger**, and sometimes a **face** (a pane, band, status line or command). It does
not mean rewriting the skill. The output is a plugin that keeps the skill untouched and adds a
thin mod beside it.

Most skills should stay skills. Checking that honestly, before building anything, is the point
of this skill. Mods run unsandboxed with the user's permissions, and they depend on a Claude Code
API that is still changing, so a mod has to earn its place.

## Step 0: Preflight

1. Run `claude --version`. Mods need **2.1.287 or later**. If it is older, stop and tell the user
   to update Claude Code; nothing below works without it.
2. Find the skill: a folder containing `SKILL.md`. If the user pasted the text instead, write it
   to a scratch folder as `SKILL.md` first. Read the whole file, and skim `scripts/` and
   `references/` if present.
3. Read `references/mod-contract.md` before generating anything. It holds the verified file
   layout, hook shapes and the static-analysis rules the validator enforces. If it ever disagrees
   with the type files Claude Code writes for the installed version (`<mod>/.claude-plugin/types/`),
   trust the types.

## Step 1: Check (always, before building)

Run the checker. It reads files only and never executes anything from the skill:

```
python3 scripts/check_skill.py <skill-folder>          # JSON
python3 scripts/check_skill.py <skill-folder> --text   # short summary
```

The output is evidence, not a decision: frontmatter problems, the moments the skill talks about
(before pushing, after edits, when the user says...), interface words, risk words, and a
heuristic verdict. Weigh it against `references/suitability.md`, which has the three tests
(moment, reliability, face) and the alternatives that often beat a mod, then settle on one of:

- **KEEP_SKILL**: nothing happens at a moment, and nothing needs drawing. Stop here. Say why in
  two or three lines, and name what fits better if something does (a settings hook for a fixed
  script, CLAUDE.md for an always-on rule, an MCP server for an outside system). Generate
  nothing. Offer `tune-skill` if the real problem is that the skill triggers badly.
- **HYBRID**: the skill has real instructions *and* a moment worth triggering at. Keep the skill,
  add a thin mod whose only job is to make Claude reach for it at that moment. This is the usual
  good case, and the scaffold in Step 3 covers it.
- **MOD_FIRST**: the behaviour is mostly the moment or the interface, and the skill text is thin.
  The mod is the product. Hand-write it (Step 3, "Beyond the scaffold").

Before building, tell the user the verdict in five lines or fewer: which moment triggers it,
what happens then, and what the mod can reach (its trust cost). Ask at most one question, and
only if the trigger is genuinely ambiguous (for example, which commands count as shipping).
Otherwise decide, and state the assumption you made.

## Step 2: Write the mod spec

Map each behaviour that has a moment onto a hook, using the table in `references/patterns.md`.
For the common case, write a small spec file in the working area (not inside the skill folder);
the format is in `references/mod-spec.md`. These choices are deliberate, and the reasons matter:

- **Smallest reach.** Use no process, network, file, environment or model calls unless the
  behaviour cannot work without them. A mod is code the user must trust, and every call is
  something they have to read. The generated mods call only `$.ui.*` and `$.command.register`.
- **Advisory, fail open.** A mod that reads command text cannot be a security control, so make it
  a reminder: add `.catch` handlers that let the call through, cap how many times it holds, and
  give the user a way to snooze it. A guard that can trap a session gets uninstalled.
- **Never approve on the user's behalf.** Do not hook `tool.check` to return `allow`, and do not
  submit prompts as the user. Those are the powers that make mods dangerous.
- **The skill still does the work.** Do not copy the skill's scripts or logic into the hooks
  module. The mod triggers; the bundled skill acts.
- **Name it `<skill>-mod`.** Names starting with `claude` or containing `anthropic` are refused
  by the validator, and a command named like the skill would collide with its own `/<skill>`.

## Step 3: Scaffold

```
python3 scripts/scaffold_mod.py --skill <skill-folder> --spec <spec.json> --out <new-plugin-folder>
```

It copies the skill unchanged into `skills/<name>/` and writes `.claude-plugin/plugin.json`,
`hooks/hooks.json`, `hooks/register.js`, `tests/<plugin>.test.ts` and a `README.md`. It never
writes into the source skill, and it refuses a non-empty output folder without `--force`. The
generated `register.js` is plain JavaScript: read it, and edit it when the spec cannot say what
the skill needs. Keep the output next to the user's other plugins (for example a `mods/` folder
beside `skills/`), so one marketplace repo can list both.

**Beyond the scaffold.** The generator covers trigger-style mods: gate, prime, command. For a
pane, a band, a status line that draws, model calls, a context watcher or a compaction handoff,
write `hooks/register.js` by hand. Load the built-in `plugin-authoring` skill (`/plugin-authoring`)
for the exact API of the installed version, and start from the closest sample in
`references/patterns.md`. If that skill is not installed, use `references/mod-contract.md` and
the type files in `<mod>/.claude-plugin/types/` once the mod has loaded once, and say in the
hand-over that the API was not checked against the installed version. Reuse the scaffold's plugin layout and tests, and keep to the same
reach rules as above.

## Step 4: Verify (do not claim done without it)

```
python3 scripts/verify_mod.py <plugin-folder> --update-readme
```

It checks the Claude Code version, runs `claude plugin validate` and `claude plugin test`,
prints which hooks the mod registers and which `$` calls it makes, translates those calls into
plain-language trust notes, and writes the report into the README. Fix until it prints `RESULT:
PASS`. Then do one real dry run, because tests stub Claude Code and cannot show how it feels:
`claude --plugin-dir <plugin-folder>`, trigger the moment, and run `/plugin` to see "1 mod active".

## Step 5: Hand over

Report, briefly: the verdict and why; what triggers the mod and what it does then; the modes and
how to snooze it; the trust surface exactly as the verifier printed it; how to run it
(`claude --plugin-dir`) and share it (a marketplace listing); and anything that is heuristic.
Do not paste the generated code into the reply.

## Honest limits

- The checker is a keyword heuristic over prose. It can miss a moment phrased unusually and
  over-read an example. That is why the verdict is confirmed by judgement, not copied. It needs
  two points of evidence before it counts a moment, ignores the trigger wording every skill puts
  in its own description, and lists weaker hits as `weak_signals` instead of counting them.
  `python3 -I scripts/test_check_skill.py` covers the wordings that used to fool it; add a case
  there whenever a real skill gets a verdict you disagree with. One known miss: a skill that
  talks about a pane that already exists (the built-in browser's, say) still reads as MOD_FIRST,
  because the checker cannot tell a pane to build from a pane to use.
- Matching command text is a reminder, not a guarantee. `echo "git push"` also matches, and a
  skilled user or a rewritten command can slip past. Say so if the user wants enforcement; that
  belongs in permission rules or managed settings.
- `skill.prompt` shows that a skill was *loaded*, not that it *succeeded*. The scaffold treats
  "loaded since the last edit" as "checked". If the user needs proof, have the skill write a
  receipt file and have the mod read it, which costs a `$.fs.read` call that the user must accept.
- Surfaces differ: panes and bands draw in the terminal and the Desktop Code tab, `claude -p`
  runs hooks but draws nothing, WSL sessions in the Desktop app load no plugins, and an
  organisation can block user-installed mods. Mention the ones that matter for this mod.
- Mods follow a fast-moving API. Record the Claude Code version the mod was tested with in its
  README.

## Reference files

- `references/suitability.md`: the three tests, the comparison with settings hooks, skills and MCP
  servers, three worked verdicts, and the costs of a mod.
- `references/mod-contract.md`: verified layout, hook and return shapes, static-analysis rules,
  limits, surfaces, and the test kit.
- `references/patterns.md`: behaviour-to-hook table, what each scaffolded pattern emits, and
  recipes with sample mods for hand-written ones.
- `references/mod-spec.md`: the spec format with a full example.
