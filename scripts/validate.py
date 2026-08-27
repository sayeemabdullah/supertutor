#!/usr/bin/env python3
"""Structural validation for the Supertutor skill.

Checks the invariants that break the skill silently: malformed frontmatter,
routing rows pointing at files that don't exist, workflow files missing their
`Rules` section, seeded data in the files that must ship empty, and slash-command
drift between SKILL.md and the README.

Exit 0 = valid, 1 = one or more failures (each printed).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "supertutor")
REF_DIR = os.path.join(SKILL_DIR, "references")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
README = os.path.join(ROOT, "README.md")

# Written to at runtime; they ship as empty templates and carry no Rules section.
STATEFUL = {"curriculum.md", "progress.md", "weak-areas.md"}

EXPECTED_REF_COUNT = 11
SKILL_MD_MAX_LINES = 500
DESC_MAX = 1024

failures = []


def fail(msg):
    failures.append(msg)


def check_frontmatter(text):
    lines = text.split("\n")
    if lines[0] != "---":
        fail("SKILL.md: does not open with '---'")
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail("SKILL.md: frontmatter is never closed")
        return None

    fm = lines[1:end]
    if len(fm) != 2:
        fail(f"SKILL.md: frontmatter must be exactly 2 lines, found {len(fm)}. "
             "A wrapped description silently breaks triggering.")
        return None

    keys = [l.split(":", 1)[0] for l in fm]
    if keys != ["name", "description"]:
        fail(f"SKILL.md: frontmatter keys must be [name, description], found {keys}")
    if fm[0] != "name: supertutor":
        fail(f"SKILL.md: name must be 'supertutor', found {fm[0]!r}")

    desc = fm[1][len("description: "):] if fm[1].startswith("description: ") else ""
    if not desc:
        fail("SKILL.md: description is empty or malformed")
    if len(desc) > DESC_MAX:
        fail(f"SKILL.md: description is {len(desc)} chars, over the {DESC_MAX} limit")
    return desc


def table_commands(text):
    """Slash commands taken only from table rows: `| `/name` | ... |`."""
    return re.findall(r"^\|\s*`(/[a-z]+)`\s*\|", text, re.M)


def check_red_flags(label, text):
    """A '## Red flags' section with >=2 data rows whose left cell is a quoted
    thought. A rule that quietly stops firing looks identical to one that works;
    naming the rationalization is what catches the violation."""
    if "\n## Red flags" not in text:
        fail(f"{label}: missing '## Red flags' section — naming the rationalization "
             "is what catches the violation, not restating the rule")
        return
    block = text.split("\n## Red flags", 1)[1].split("\n## ", 1)[0]
    rows = [l for l in block.splitlines()
            if l.startswith("|") and not re.match(r"^\|[\s|:-]+\|?$", l)
            and "Thought" not in l]
    if len(rows) < 2:
        fail(f"{label}: '## Red flags' has {len(rows)} row(s); needs at least 2")
    for row in rows:
        if '"' not in row.split("|")[1]:
            fail(f"{label}: a Red flags row has no quoted thought — the left "
                 "column must be the rationalization, verbatim")


def main():
    if not os.path.isdir(REF_DIR):
        fail(f"missing {REF_DIR}")
        return

    skill = open(SKILL_MD).read()
    readme = open(README).read()
    refs = sorted(f for f in os.listdir(REF_DIR)
                  if f.endswith(".md") and os.path.isfile(os.path.join(REF_DIR, f)))

    if len(refs) != EXPECTED_REF_COUNT:
        fail(f"references/ must contain exactly {EXPECTED_REF_COUNT} .md files, found {len(refs)}: {refs}")

    check_frontmatter(skill)
    check_red_flags("SKILL.md", skill)

    # Every routing row (path in the last cell) must resolve to a real file.
    routed = re.findall(r"^\|.*\|\s*`references/([a-z-]+\.md)`\s*\|\s*$", skill, re.M)
    for r in routed:
        if r not in refs:
            fail(f"SKILL.md: routing table points at references/{r}, which does not exist")
    if len(routed) != len(set(routed)):
        dupes = sorted({r for r in routed if routed.count(r) > 1})
        fail(f"SKILL.md: duplicate routing rows for {dupes}")

    workflow_refs = [r for r in refs if r not in STATEFUL]

    for r in refs:
        text = open(os.path.join(REF_DIR, r)).read()
        if not text.lstrip().startswith("# "):
            fail(f"{r}: no H1 heading")
        # Cross-references between reference files must resolve.
        for target in set(re.findall(r"`references/([a-z-]+\.md)`", text)):
            if target not in refs:
                fail(f"{r}: cross-reference to `references/{target}`, which does not exist")

        if r in STATEFUL:
            continue
        if r not in routed:
            fail(f"{r}: exists but no routing row points at it, so it can never load")
        if "\n## Rules" not in text:
            fail(f"{r}: missing '## Rules' section — the pedagogy rules are the product, not boilerplate")
        check_red_flags(r, text)

    # Slash commands: SKILL.md table and README table must match, in order.
    skill_cmds = table_commands(skill)
    readme_cmds = table_commands(readme)
    if not skill_cmds:
        fail("SKILL.md: slash-command table not found")
    if not readme_cmds:
        fail("README.md: slash-command table not found")
    if skill_cmds and readme_cmds and skill_cmds != readme_cmds:
        only_skill = sorted(set(skill_cmds) - set(readme_cmds))
        only_readme = sorted(set(readme_cmds) - set(skill_cmds))
        if only_skill or only_readme:
            fail(f"slash-command drift — only in SKILL.md: {only_skill}, only in README: {only_readme}")
        else:
            fail("SKILL.md and README slash-command tables list the same commands in a different order")

    # Each workflow ref should have a matching slash command.
    if len(skill_cmds) != len(workflow_refs):
        fail(f"{len(skill_cmds)} slash commands but {len(workflow_refs)} workflow reference files")

    if len(skill.split("\n")) > SKILL_MD_MAX_LINES:
        fail(f"SKILL.md is {len(skill.split(chr(10)))} lines, over the "
             f"{SKILL_MD_MAX_LINES}-line router ceiling")

    # The stateful files must ship empty: headers and empty tables only, no data.
    for name in STATEFUL:
        text = open(os.path.join(REF_DIR, name)).read()
        if "*Empty" not in text and "Empty" not in text:
            fail(f"{name}: lost its 'Empty' template marker — it must ship as a blank template")
        # A markdown table data row starts with '|' and is not the header or the
        # |---|--- separator. Comments (<!-- ... -->) are allowed as guidance.
        for line in text.splitlines():
            s = line.strip()
            if not s.startswith("|"):
                continue
            if re.match(r"^\|[\s|:-]+\|?$", s):      # separator row
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            header_words = {"unit", "date learned", "last reviewed", "accuracy",
                            "confidence", "state", "concept", "date", "what went wrong"}
            if all(c == "" or c.lower() in header_words for c in cells):
                continue
            fail(f"{name}: contains a populated table row ({s!r}); state files ship empty")

    print(f"checked {len(refs)} reference files "
          f"({len(workflow_refs)} workflow, {len(STATEFUL)} stateful), "
          f"{len(routed)} routing rows, {len(skill_cmds)} slash commands, "
          f"Red flags tables in SKILL.md + {len(workflow_refs)} workflows")


main()

if failures:
    print(f"\n{len(failures)} problem(s):\n", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    sys.exit(1)
print("all checks passed")
