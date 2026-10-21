# Trigger cases for skill-to-mod

Format follows tune-skill's `references/test-cases.md`. Status column: **read** means I decided by
reading the descriptions only. Nothing here was run in a real triggering loop.

Siblings compared: `plugin-authoring` (built in), `tune-skill`, `draft-skill`, `skill-creator`.

| # | Message | Expected skill | Mode | Pass condition | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | "Can my release-checklist skill be a mod? I want it to run before every git push." | skill-to-mod | check, then maybe build | Runs `check_skill.py`, states a verdict in five lines or fewer, builds nothing before that | read: pass |
| 2 | "Turn my deploy-notes skill into a mod." | skill-to-mod | check, then scaffold | Checks `claude --version` first, runs the checker before scaffolding, names the plugin `deploy-notes-mod` | read: pass |
| 3 | "Should my code-review skill be a mod or stay a skill?" | skill-to-mod | check only | Gives a verdict; if KEEP_SKILL, generates no files and names a better fit | read: pass |
| 4 | "I keep forgetting to run my pre-ship checklist skill before pushing. Make Claude do it for me." | skill-to-mod | HYBRID gate | Recognises the moment (push), proposes a gate, does not copy the checklist into hooks | read: pass |
| 5 | "I want my context-guardian skill to show a live panel with how full the context is." | skill-to-mod | MOD_FIRST, hand-written | Gives MOD_FIRST, loads `plugin-authoring` for the API, keeps the skill text intact | read: pass, contested (plugin-authoring also matches "live panel"; it should come second, not first) |
| 6 | "Make me a mod that shows a pane with my current git branch." | plugin-authoring | n/a | No source skill, so skill-to-mod stays out | read: pass |
| 7 | "My changelog skill never triggers when I ask for release notes. Fix it." | tune-skill | n/a | Edits the description; does not suggest a mod | read: pass |
| 8 | "Write me a new skill for reviewing SQL migrations." | draft-skill | n/a | Writes a skill; no mod mentioned | read: pass |
| 9 | "Zip my skill and write the install steps." | skill-creator (or the packaging skill the user has) | n/a | Packages only; skill-to-mod stays out | read: pass |
| 10 | "Add a pre-push hook to settings.json that runs ./check.sh." | none of these (settings hook) | n/a | No skill is involved, so skill-to-mod should not start, though "before push" overlaps with its wording | read: pass, fragile |

## Boundary pairs

| Message | Should trigger | Why |
| --- | --- | --- |
| "Make me a new skill that reminds me to run tests before pushing." | draft-skill | Writes a new skill. The description now says so. |
| "Make my existing test-reminder skill run before pushing." | skill-to-mod | The skill exists and needs a moment. |
| "Give my context-guardian skill a status line entry." | skill-to-mod | "Existing skill" plus a face. |
| "Add a status line entry showing the current git branch." | plugin-authoring | No source skill. |

## Message that spans both

"My release-gate skill doesn't trigger well. Fix its description, then turn it into a mod."
Should start with `tune-skill` (the wording), hand back the fixed folder, then continue with
`skill-to-mod` on the fixed copy. skill-to-mod's own KEEP_SKILL step already points back to
`tune-skill` when the real problem is triggering.

## Not run

- skill-creator's automated triggering loop.
- Any message above against a live agent with all five skills installed.
