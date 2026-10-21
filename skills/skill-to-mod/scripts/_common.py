"""Shared helpers for the skill-to-mod scripts: frontmatter parsing and name rules."""
import re
from pathlib import Path

MIN_CLAUDE_CODE = (2, 1, 287)  # the release that introduced mods
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


def find_skill_md(path):
    """Accept a folder holding SKILL.md, or the SKILL.md file itself."""
    p = Path(path).expanduser()
    if p.is_file() and p.name == "SKILL.md":
        return p
    if p.is_dir() and (p / "SKILL.md").is_file():
        return p / "SKILL.md"
    return None


def parse_frontmatter(text):
    """Return (frontmatter dict, body, problems). A small YAML subset: scalars and > | blocks."""
    problems = []
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)(.*)$", text, re.S)
    if not m:
        return {}, text, ["SKILL.md has no YAML frontmatter between --- lines"]
    block, body = m.group(1), m.group(2)
    fm, key, style, buf = {}, None, None, []

    def flush():
        nonlocal key, style, buf
        if key is None:
            return
        if style == "|":
            fm[key] = "\n".join(buf).strip()
        elif style == ">":
            fm[key] = " ".join(s.strip() for s in buf if s.strip()).strip()
        else:
            fm[key] = " ".join(s.strip() for s in buf).strip()
        key, style, buf = None, None, []

    for line in block.splitlines():
        top = re.match(r"^([A-Za-z0-9_.-]+):[ \t]*(.*)$", line)
        if top and not line.startswith((" ", "\t")):
            flush()
            key, value = top.group(1), top.group(2).strip()
            if re.match(r"^[>|][+-]?$", value):
                style = value[0]
                buf = []
            else:
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                style = None
                buf = [value]
        elif key is not None:
            buf.append(line)
    flush()
    return fm, body, problems


def claude_version():
    """The installed Claude Code version as a tuple, or None if it can't be read."""
    import subprocess

    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(x) for x in m.groups()) if m else None


def plugin_name_problem(name):
    """Why a plugin name would be refused, or None."""
    if not NAME_RE.match(name):
        return "use lowercase letters, digits and hyphens, 2-63 characters, starting with a letter or digit"
    if name.startswith("claude") or "anthropic" in name:
        return "names that look like Anthropic's own (starting with claude, or containing anthropic) are refused by claude plugin validate"
    return None
