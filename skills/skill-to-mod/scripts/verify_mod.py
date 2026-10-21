#!/usr/bin/env python3
"""Verify a mod plugin: Claude Code version, `claude plugin validate`, `claude plugin test`,
and a plain-language read of what the mod can reach.

Usage: python3 verify_mod.py <plugin-folder> [--update-readme] [--directory]

  --update-readme  write the validator's hooks:/calls: report into README.md between the
                   <!-- trust:start --> and <!-- trust:end --> markers
  --directory      also hold the plugin to the marketplace directory rules (README, LICENSE,
                   icon); without it those are listed as publish-readiness notes only

Exit status 0 only when validation and every test pass.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import MIN_CLAUDE_CODE, claude_version  # noqa: E402

LINE = re.compile(r"^\s*[>❯]\s+(\S+)\s+(hooks|calls|env reads|env writes|state reads|state writes|answers its own command|gating hook with \.catch|gating hook without \.catch):\s*(.*)$")

# What each call means for the person installing the mod.
CALL_NOTES = {
    "process.run": "starts programs on your machine, outside any sandbox",
    "process.spawn": "starts long-running programs on your machine, outside any sandbox",
    "http.fetch": "makes network requests: anything the mod can read could leave the machine",
    "fs.read": "reads files as you",
    "fs.write": "writes files as you",
    "env.get": "reads environment variables, which can hold API keys",
    "env.set": "changes environment variables",
    "mcp.call": "calls tools on your connected MCP servers",
    "mcp.connect": "connects an MCP server",
    "model.complete": "spends your plan or API usage on its own model calls",
    "model.fork": "spends your plan or API usage and sends the conversation to a model",
    "prompt.submit": "can start a turn as if you had typed it",
    "session.send": "sends messages to your other sessions",
    "session.messages": "reads the whole transcript",
    "tool.register": "adds a tool Claude can call",
    "agent.spawn": "starts subagents",
    "settings.read": "reads your settings files",
}
HOOK_NOTES = {
    "tool.check": "can approve or refuse tool calls before you are asked: review it line by line",
    "telemetry.log": "sees usage records",
    "plugin.register": "judges other mods as they load",
    "engine.create": "changes the API other mods receive",
    "session.append": "rewrites what the transcript stores",
}


def run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return p.returncode, p.stdout, p.stderr


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    plugin = Path(args[0]).expanduser().resolve()
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        print(f"not a plugin folder (no .claude-plugin/plugin.json): {plugin}")
        return 2

    version = claude_version()
    if version is None:
        print("claude is not on PATH, so nothing can be validated or tested here.")
        return 2
    if version < MIN_CLAUDE_CODE:
        print("Claude Code {} is too old: mods need {} or later. Update Claude Code first.".format(
            ".".join(map(str, version)), ".".join(map(str, MIN_CLAUDE_CODE))))
        return 2
    print("Claude Code " + ".".join(map(str, version)))

    # 1. validate
    cmd = ["claude", "plugin", "validate", str(plugin)]
    if "--directory" in argv:
        cmd += ["--profile", "directory"]
    code, out, err = run(cmd, 120)
    text = out + err
    findings = {}
    for line in text.splitlines():
        m = LINE.match(line)
        if m:
            findings.setdefault(m.group(2), []).append(f"{m.group(1)} {m.group(3)}")
    ok_validate = code == 0 and "Validation passed" in text
    print("\n[validate] " + ("passed" if ok_validate else "FAILED"))
    if not ok_validate:
        print(text.strip()[-2500:])
    for key in ("hooks", "calls", "env reads", "env writes", "state reads", "state writes"):
        for item in findings.get(key, []):
            print(f"  {key}: {item}")
    for item in findings.get("gating hook without .catch", []):
        print(f"  note: gating hook without .catch: {item} (if it fails, Claude Code skips it and the call proceeds; add a .catch if it must fail closed)")

    # 2. what the mod can reach
    calls = set()
    for item in findings.get("calls", []):
        for c in re.findall(r"\$\.([\w.]+)", item):
            calls.add(c)
    hooked = set()
    for item in findings.get("hooks", []):
        for h in re.split(r",\s*(?![^{]*\})", item.split(" ", 1)[1] if " " in item else item):
            hooked.add(re.sub(r"\{.*", "", h).strip())
    print("\n[reach]")
    notes = [f"  $.{c}: {CALL_NOTES[c]}" for c in sorted(calls) if c in CALL_NOTES]
    notes += [f"  hooks {h}: {HOOK_NOTES[h]}" for h in sorted(hooked) if h in HOOK_NOTES]
    if findings.get("env reads"):
        notes.append("  reads environment variables: " + "; ".join(findings["env reads"]))
    print("\n".join(notes) if notes else "  Nothing outside Claude Code: no files, processes, network, environment variables or other sessions.")

    # 3. publish readiness (does not affect the result)
    ready = re.findall(r"^\s*>\s+(.+?):\s+.*?\(([A-Z_]+)\)", text, re.M)
    if ready:
        print("\n[publish readiness] (not needed to run it)")
        for where, code_name in ready:
            print(f"  {code_name}: {where}")

    # 4. tests
    tests = sorted(plugin.rglob("*.test.ts")) + sorted(plugin.rglob("*.test.tsx"))
    ok_tests = True
    print()
    if not tests:
        print("[test] no *.test.ts files: add tests before you rely on this mod")
    else:
        code, out, err = run(["claude", "plugin", "test", str(plugin)], 300)
        text = out + err
        m_pass = re.search(r"(\d+) pass", text)
        m_fail = re.search(r"(\d+) fail", text)
        passed, failed = int(m_pass.group(1)) if m_pass else 0, int(m_fail.group(1)) if m_fail else 0
        ok_tests = code == 0 and failed == 0 and passed > 0
        print(f"[test] {passed} passed, {failed} failed" + ("" if ok_tests else "  <- FAILED"))
        if not ok_tests:
            print(text.strip()[-3000:])

    # 5. README trust block
    if "--update-readme" in argv:
        readme = plugin / "README.md"
        lines = [f"- {k}: {v}" for k in ("hooks", "calls", "env reads", "env writes", "state reads", "state writes") for v in findings.get(k, [])]
        block = "```text\n" + "\n".join(f"{k}: {v}" for k in ("hooks", "calls") for v in findings.get(k, [])) + "\n```"
        if readme.is_file() and "<!-- trust:start -->" in readme.read_text(encoding="utf-8"):
            body = readme.read_text(encoding="utf-8")
            body = re.sub(r"<!-- trust:start -->.*?<!-- trust:end -->", lambda _m: "<!-- trust:start -->\n" + block + "\n<!-- trust:end -->", body, flags=re.S)
            readme.write_text(body, encoding="utf-8")
            print("\nREADME trust block updated.")
        else:
            print("\nREADME has no trust markers; left alone.")

    ok = ok_validate and ok_tests
    print("\nRESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
