# skill-to-mod

An agent skill for Claude Code that decides whether one of your skills should become a Claude Code mod, and builds the plugin when it should. A mod is code that runs inside Claude Code on events such as a command about to run or a prompt being submitted, so a skill that keeps getting skipped before `git push` can be made to run there. skill-to-mod checks first and says "keep it a skill" when that is the better answer.

Install: `npx skills add arm-pz/skill-to-mod --skill skill-to-mod`

Needs Claude Code 2.1.287 or later (the release that added mods), Python 3, and the `claude` command on your path. Claude Code only.

Ask it things like:

- "Can my release-gate skill be a mod that runs before git push?"
- "Should this skill be a mod or a settings hook?"
- "Turn ./skills/pre-ship-security-red-team into a mod that runs before deploys."
- "Make a mod from this skill with a /status command."

"Mod" here means a Claude Code mod, a plugin whose code runs inside Claude Code. It does not mean a game mod. This project is not made or endorsed by Anthropic.

## What you get

| Step | Output |
|---|---|
| Check | `check_skill.py` reads the skill and reports KEEP_SKILL, HYBRID or MOD_FIRST with the evidence. It reads files only and runs nothing from the skill |
| Decision | Claude weighs that evidence against `references/suitability.md` and tells you the verdict in a few lines. KEEP_SKILL stops there and generates nothing |
| Scaffold | `scaffold_mod.py` writes a plugin: your skill copied unchanged, `plugin.json`, `hooks/register.js`, tests and a README |
| Verify | `verify_mod.py` runs `claude plugin validate` and `claude plugin test`, prints the hooks the mod registers and the `$` calls it makes, and writes that into the README |

The scaffold covers three trigger patterns:

- **gate:** hold ship commands (`git push`, `npm publish`, deploys) until the required skills have run since the last edit
- **prime:** add one line of context when a prompt contains a phrase such as "ship it"
- **command:** a slash command that shows state and can be snoozed

Panes, bands, status lines that draw, model calls and compaction handoffs are not generated. For those the skill points you to Claude Code's built-in `plugin-authoring` skill and Anthropic's sample mods.

## Limits, stated plainly

- The verdict is a keyword heuristic over the skill's text plus a written rubric. It needs two points of evidence before it counts a moment, and lists weaker hits separately. A verdict you disagree with is a bug: add a case to `scripts/test_check_skill.py`.
- A generated gate reads the text of a command. It is a reminder that fails open, not a security control.
- "The skill ran" means it was loaded, not that it passed.
- Mods are not sandboxed and the API is young. Every generated README lists exactly which calls the mod makes. Read it before installing anyone's mod.

## Not for

Writing a skill from scratch (`draft-skill`), fixing a skill that does not trigger (`tune-skill`), or writing a mod with no source skill (Claude Code's built-in `plugin-authoring` skill). `draft-skill` and `tune-skill` are arm-pz repos and install the same way. A worked example of what the gate pattern produces: [ship-sentinel](https://github.com/arm-pz/ship-sentinel).

## Install

```
npx skills add arm-pz/skill-to-mod --skill skill-to-mod
```

Or copy `skills/skill-to-mod/` into `.claude/skills/`.

As a Claude Code plugin:

```
/plugin install skill-to-mod --marketplace arm-pz/skill-to-mod
```

To try it for one session from a clone: `claude --plugin-dir ./skill-to-mod`.

## Structure

```
skill-to-mod/
├── README.md
├── LICENSE
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
└── skills/
    └── skill-to-mod/
        ├── SKILL.md                 # workflow: preflight, check, spec, scaffold, verify, hand over
        ├── references/
        │   ├── suitability.md       # the three tests, mod vs hook vs skill vs MCP, worked verdicts
        │   ├── mod-contract.md      # layout, hook shapes, validator rules, limits, surfaces
        │   ├── patterns.md          # behaviour to hook, scaffolded patterns, hand-written recipes
        │   └── mod-spec.md          # the spec file the scaffold reads
        ├── scripts/
        │   ├── check_skill.py
        │   ├── scaffold_mod.py
        │   ├── verify_mod.py
        │   ├── _common.py
        │   └── test_check_skill.py
        └── evals/
            ├── evals.json
            └── trigger-cases.md      # hand-run trigger cases, with what was and was not run
```

## Licence

See `LICENSE`.
