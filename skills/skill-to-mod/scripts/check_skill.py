#!/usr/bin/env python3
"""Check whether a skill is a good candidate to become a Claude Code mod.

Usage: python3 check_skill.py <skill-folder-or-SKILL.md> [--text]

Prints a JSON report (or a short text summary with --text): frontmatter problems,
the "moments" the skill talks about (events a mod could hook), any interface it
describes, how much of it is plain knowledge, risk words, and a heuristic verdict:

  KEEP_SKILL  nothing in the skill happens at a particular moment. Leave it a skill.
  HYBRID      the skill has real instructions AND moments. Keep it, add a thin mod
              that triggers it.
  MOD_FIRST   the skill is mostly a description of behaviour at moments or an
              interface. The mod is the product; hand-write it.

The verdict is evidence for you to weigh against references/suitability.md, not a
decision. This script reads files only; it never runs anything from the skill.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_skill_md, parse_frontmatter, plugin_name_problem  # noqa: E402

# (id, label, regex, weight, hook it would use)
EVENT_SIGNALS = [
    ("before-risky-action", "acts before a risky or outward-facing command",
     r"\b(before|prior to|ahead of)\b[^.\n]{0,50}\b(commit(ting)?|push(ing)?|deploy(ing)?|ship(ping)?|launch(ing)?(?!\s+(the|a|an|each|every|your|next|all|it|them|one|two|three)\b)|releas(e|ing)|merg(e|ing)|publish(ing)?|delet(e|ing)|migrat\w+|going live|production)\b",
     2, "tool.call (Bash)"),
    ("after-edit", "reacts after files are edited",
     r"\b(after|every time|each time)\b[^.\n]{0,40}\b(edit(s|ing)?|writ(e|es|ing)|chang(e|es|ing)|modif\w+|sav(e|es|ing))\b[^.\n]{0,25}\b(files?|code|sources?|tests?|\w+\.\w{1,4})\b",
     1, "tool.call (Edit/Write)"),
    # Only a quoted phrase counts ("when the user says "ship it""). Wording like "use when the user
    # wants..." is how every skill describes its own trigger, and "if the user says stop, stop" is
    # an instruction, so neither is a moment a mod could hook.
    ("user-says", "fires on a phrase the user types",
     r"\b(when(ever)?|if) the user (says|types|writes|mentions)\b[^.\n]{0,15}[\"“'‘`]",
     1, "prompt.submit"),
    ("turn-end", "acts at the end of a turn or answer",
     r"\b(after|at the end of|when)\b[^.\n]{0,20}\b(each|every|the)\b[^.\n]{0,12}\b(turn|response|reply|answer)\b",
     1, "turn.complete"),
    ("session-start", "acts when a session starts",
     r"\b(at the start of|on|when) (a |the )?(new )?(session|startup)\b|\bsession start\b",
     1, "session.start"),
    ("context-or-compaction", "watches context size, compaction or handoff",
     r"\b(context (window|limit|fills?|usage|budget)|compact(s|ed|ing|ion)|auto-?compact\w*|(session|context|compaction)[- ]hand ?offs?|hand ?off (file|note|summary|doc)s?)\b",
     2, "session.compact / $.session.usage"),
    ("automatic", "is meant to run automatically",
     r"\b(automatically|on every (turn|prompt|message|commit|push|edit|save|tool call|session)|without being asked|always runs?)\b",
     1, "(any event)"),
]

# Extra rules per signal. body_only: ignore the frontmatter description, which describes when the
# skill loads, not what it does. min_hits: one passing mention is not a theme. Signals below their
# minimum are reported as weak and not counted.
SIGNAL_RULES = {
    "user-says": {"body_only": True},
    "context-or-compaction": {"min_hits": 2},
}
# Total event weight needed before the skill counts as having a moment a mod could hook.
MOMENT_MIN = 2

UI_RE = r"\b(pane|panel|status ?line|toast|live view|above the prompt)\b"
# A "browser pane" is a browser, not a mod surface.
UI_NOISE_RE = r"\b(browser|in-app|preview)\s+(pane|panel)\b"
UI_MIN = 2

KNOWLEDGE_RE = (
    r"\b(guidelines?|style guide|tone|voice|template|format(ting)?|examples?|best practices?|reference|"
    r"how to|principles?|rubric|checklist|step[- ]by[- ]step|workflow|prompt|explain|write|draft|analy[sz]e)\b"
)

RISK_SIGNALS = [
    ("network", r"\b(curl|wget|https?://|webhook|fetch\()", "talks to the network"),
    ("secrets", r"\b(api[_ -]?key|token|secret|password|credential|private key|\.env)\b", "mentions secrets or credentials"),
    ("shell", r"\b(sudo|rm -rf|ssh|chmod|eval|exec)\b", "runs powerful shell commands"),
    ("scripts", r"\bscripts?/", "bundles scripts"),
]


def first_evidence(regex, text):
    m = re.search(regex, text, re.I)
    if not m:
        return None
    start = max(0, m.start() - 30)
    return re.sub(r"\s+", " ", text[start : m.end() + 40]).strip()


def analyse(path):
    skill_md = find_skill_md(path)
    if skill_md is None:
        return {"ok": False, "error": "no SKILL.md found at " + str(path)}
    root = skill_md.parent
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body, problems = parse_frontmatter(text)
    name = fm.get("name", "")
    desc = fm.get("description", "")
    lint = list(problems)
    if not name:
        lint.append("frontmatter has no name")
    elif name != root.name and root.name not in ("", "."):
        lint.append(f"name '{name}' does not match its folder '{root.name}'")
    if not desc:
        lint.append("frontmatter has no description, so nothing can trigger this skill")
    elif len(desc) > 1024:
        lint.append(f"description is {len(desc)} characters; keep it under 1024")
    if len(body.split()) < 20:
        lint.append("body is nearly empty")

    scan = desc + "\n" + body
    events, weak = [], []
    for sid, label, rx, weight, hook in EVENT_SIGNALS:
        rule = SIGNAL_RULES.get(sid, {})
        hay = body if rule.get("body_only") else scan
        hits = len(re.findall(rx, hay, re.I))
        if not hits:
            continue
        item = {"id": sid, "label": label, "weight": weight, "hits": hits, "hook": hook, "evidence": first_evidence(rx, hay)}
        (events if hits >= rule.get("min_hits", 1) else weak).append(item)
    ui_hits = len(re.findall(UI_RE, scan, re.I)) - len(re.findall(UI_NOISE_RE, scan, re.I))
    ui_hits = ui_hits if ui_hits >= UI_MIN else 0
    knowledge_hits = len(re.findall(KNOWLEDGE_RE, scan, re.I))
    words = len(body.split())
    has_refs = any((root / d).is_dir() for d in ("references", "assets", "reference"))
    has_scripts = (root / "scripts").is_dir()

    risks = []
    for rid, rx, label in RISK_SIGNALS:
        hits = len(re.findall(rx, scan, re.I))
        if hits or (rid == "scripts" and has_scripts):
            risks.append({"id": rid, "label": label, "hits": hits})

    event_pts = sum(e["weight"] for e in events)
    ui_pts = 2 if ui_hits else 0
    # Knowledge: how much of the skill is guidance Claude must read, not behaviour at a moment.
    know_pts = min(knowledge_hits, 12) / 12 * 3 + (1 if has_refs else 0) + (1 if words > 600 else 0)

    reasons = []
    if event_pts < MOMENT_MIN and ui_pts == 0:
        verdict = "KEEP_SKILL"
        reasons.append("nothing in it happens at a particular moment, so there is nothing for a mod to hook")
        if events or weak:
            reasons.append("only weak signals, which do not make a moment: " + ", ".join(e["id"] for e in events + weak))
    elif ui_pts and know_pts < 2:
        verdict = "MOD_FIRST"
        reasons.append("it describes an interface and carries little standalone instruction")
    elif event_pts >= 4 and know_pts < 1:
        verdict = "MOD_FIRST"
        reasons.append("it is mostly behaviour at moments, with little for Claude to read")
    else:
        verdict = "HYBRID"
        reasons.append("it has instructions worth keeping as a skill and moments a mod can trigger it at")
    if events and verdict != "KEEP_SKILL":
        reasons.append("moments found: " + ", ".join(e["id"] for e in events))
    if ui_pts:
        reasons.append("interface words found (needs a hand-written pane, band or status line)")
    if know_pts >= 2:
        reasons.append("substantial guidance: keep the skill text intact and bundle it")

    patterns, by_hand = [], []
    ids = {e["id"] for e in events} if verdict != "KEEP_SKILL" else set()
    if "before-risky-action" in ids:
        patterns.append("gate")
    if "user-says" in ids:
        patterns.append("prime")
    if patterns:
        patterns.append("command")
    if ui_pts:
        by_hand.append("pane / band / status line (see plugin-authoring and Anthropic's sample mods)")
    if ids & {"turn-end", "session-start", "context-or-compaction", "after-edit"}:
        by_hand.append("hooks for: " + ", ".join(sorted(ids & {"turn-end", "session-start", "context-or-compaction", "after-edit"})))

    suggested = (name or root.name) + "-mod"
    return {
        "ok": True,
        "skill": {"name": name, "folder": str(root), "description_chars": len(desc), "body_words": words,
                  "has_references": has_refs, "has_scripts": has_scripts},
        "lint": lint,
        "events": events,
        "weak_signals": weak,
        "ui_mentions": ui_hits,
        "knowledge_hits": knowledge_hits,
        "risks": risks,
        "scores": {"event": event_pts, "ui": ui_pts, "knowledge": round(know_pts, 1)},
        "verdict": verdict,
        "reasons": reasons,
        "scaffoldable_patterns": patterns,
        "hand_written": by_hand,
        "suggested_plugin_name": suggested,
        "plugin_name_problem": plugin_name_problem(suggested),
        "note": "Heuristic evidence only. Confirm against references/suitability.md before telling the user a verdict.",
    }


def as_text(r):
    if not r.get("ok"):
        return "ERROR: " + r["error"]
    s = r["skill"]
    out = [f"{s['name'] or s['folder']}: {r['verdict']}"]
    out += ["  - " + x for x in r["reasons"]]
    if r["lint"]:
        out.append("Frontmatter / lint:")
        out += ["  ! " + x for x in r["lint"]]
    if r["risks"]:
        out.append("Trust notes: " + "; ".join(x["label"] for x in r["risks"]))
    if r["scaffoldable_patterns"]:
        out.append("Scaffoldable: " + ", ".join(r["scaffoldable_patterns"]))
    if r["hand_written"]:
        out.append("By hand: " + "; ".join(r["hand_written"]))
    return "\n".join(out)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    report = analyse(args[0])
    print(as_text(report) if "--text" in argv else json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
