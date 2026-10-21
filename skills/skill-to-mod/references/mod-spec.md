# Mod spec format

A JSON file read by `scripts/scaffold_mod.py`. Keep it outside the skill folder.

```json
{
  "plugin": "release-gate-mod",
  "description": "Makes sure the release-gate checklist runs before anything ships.",
  "version": "0.1.0",
  "author": "Your Name",
  "keywords": ["release"],
  "gate": {
    "match": ["git push", "gh pr create", "npm publish", "re:\\bterraform\\s+apply\\b"],
    "example": "git push origin main",
    "required": ["release-gate"],
    "mode": "ask",
    "staleOnEdit": true,
    "maxHolds": 2
  },
  "prime": {
    "match": ["ship it", "go live"],
    "text": "Optional. Defaults to a line naming the outstanding checks."
  },
  "command": { "name": "release-gate-mod" }
}
```

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `plugin` | no | Plugin name. Default `<skill>-mod`. Lowercase letters, digits, hyphens; must not start with `claude` or contain `anthropic`. |
| `description` | no | One line for the manifest and README. |
| `version`, `author`, `keywords` | no | Manifest fields. |
| `gate` | one of `gate` / `prime` | Hold ship commands until required skills have run. |
| `gate.match` | yes | Commands that count as shipping. A plain entry is words matched anywhere a command can start (`git push` matches `cd x && git push`, not `git pushx`). An entry starting `re:` is a raw JavaScript regular expression, test-compiled with Node. |
| `gate.example` | if every entry is `re:` | A command that matches, used by the generated tests. |
| `gate.required` | no | Skills that must have run. Default: the source skill. All must have run. Users change it with `/plugin configure <plugin>@<marketplace>`. |
| `gate.mode` | no | `ask` (default), `block`, `nudge` or `off`. Users change it with `/plugin configure <plugin>@<marketplace>`. |
| `gate.staleOnEdit` | no | Default true. A successful Edit/Write clears earlier checks. |
| `gate.maxHolds` | no | Default 2. After this many holds the command is let through. |
| `prime` | one of `gate` / `prime` | Add one line of context when a prompt matches. |
| `prime.match` | yes | Phrases, case-insensitive, matched on word boundaries; `re:` raw entries allowed. |
| `prime.example` | if every entry is `re:` | A phrase that matches. |
| `prime.text` | no | The line Claude reads. Default depends on whether a gate exists. |
| `command` | no | `false` for none. Otherwise `{ "name": ... }`; default name is the plugin name. It must not equal the skill's name. |

## What the generator refuses

A missing or broken skill frontmatter, a reserved plugin name, a regular expression that does not
compile, a command named like the skill, an output folder inside the skill folder, and a non-empty
output folder (unless `--force`). It prints the reason in one line.

## What it writes

`.claude-plugin/plugin.json` (with `userConfig` for `mode` and `required` when there is a gate),
`hooks/hooks.json`, `hooks/register.js`, `tests/<plugin>.test.ts`, `README.md`, and a copy of the
skill in `skills/<name>/`.
