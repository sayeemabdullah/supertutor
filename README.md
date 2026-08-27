# Supertutor

A Claude Skill that acts as a structured learning coach — 8 workflows covering curriculum
design, teaching, active-recall quizzing, Feynman-style explanation checks, spaced review,
progress tracking, exam prep, and study methods.

Ask Claude to teach or quiz you in plain language and it routes to the right workflow
automatically. Claude already explains things well; the value here is the scaffolding
around explanation — sequencing, retrieval practice, and honest tracking of what stuck.

---

## What it does

| Command | Workflow | Covers | Example |
|---|---|---|---|
| `/plan` | Curriculum design | Goal, starting point, time budget → a sequenced plan with milestones and an out-of-scope list | *"Help me learn linear algebra for an ML course in 6 weeks"* |
| `/learn` | Teaching a unit | Hook → core idea → why it exists → worked example → their turn → check | *"Teach me the next unit"* |
| `/quiz` | Assessment | One question at a time, weighted to weak areas, confidence recorded with every answer | *"Quiz me on what we've covered"* |
| `/explain` | Feynman mode | You explain it jargon-free; Claude probes the weakest point until a gap surfaces | *"Let me explain backprop back to you"* |
| `/review` | Spaced review | Computes what's due (1/3/7/16/35-day intervals), interleaves topics, retrieval not re-reading | *"What's due for review?"* |
| `/status` | Progress tracking | Confidence map (solid / fragile / broken), trend, one next action, honest readiness verdict | *"Am I ready for the exam?"* |
| `/exam` | Exam & interview prep | Backward plan from the date, timed practice, triage when time is short, mock interviews | *"I have a system-design interview in 2 weeks"* |
| `/methods` | Study methods | Evidence-ranked techniques, why the effective ones feel worse, session structure | *"Why do I forget everything I read?"* |

### How to invoke it

**`/supertutor` is the only slash command.** Claude.ai registers one command per skill,
taken from the `name` field — the commands above are routing hints the skill reads once
it's running, not entries the menu knows about.

All three of these work:

```
/supertutor quiz me on unit 3
quiz me on unit 3
I keep forgetting the stuff from last week
```

The last one is the point: no keyword needed. "Explain this back to me" routes to Feynman
mode, "what should I study next" routes to progress tracking. The command is there for
when you want to override Claude's guess.

---

## Install

**Requirements:** any Claude plan with **Code execution and file creation** enabled.

### 1. Enable code execution

Go to **Settings → Capabilities** and turn on **Code execution and file creation**.

> If the Skills menu is missing or greyed out, this is almost always why — it's not a
> plan limitation. On Team and Enterprise plans, an owner may need to enable it at the
> organization level.

### 2. Get the skill file

**Option A — download the packaged file**

Download [`supertutor.skill`](../../raw/main/supertutor.skill) from this repo, or grab a
pinned version from [Releases](../../releases/latest).

You never build it yourself. CI rebuilds the archive from `supertutor/` on every PR and
commits it, so the copy on `main` always matches the source.

**Option B — build it from a clone**

```bash
git clone https://github.com/sayeemabdullah/supertutor.git
cd supertutor
./scripts/build.sh
```

Use the script rather than a bare `zip` — it produces the same bytes CI does, and fails
if the archive root isn't `supertutor/`, which is what Claude.ai rejects on upload.

### 3. Upload to Claude

1. Go to **Customize → Skills** ([claude.ai/customize/skills](https://claude.ai/customize/skills))
2. Click **+** → **Create skill** → **Upload a skill**
3. Select the `.skill` or `.zip` file
4. Toggle it on

### 4. Start a new conversation

Skills load at session start, so an already-open chat won't pick it up.

```
Help me learn statistics. Run /plan.
```

---

## Updating an installed skill

Claude.ai has **no in-place update**. Uploading a revised file does not replace the copy
already installed — you get a second skill with the same `name`, and two skills answering
to `/supertutor` route unpredictably. Delete the old one first.

1. **Customize → Skills** ([claude.ai/customize/skills](https://claude.ai/customize/skills))
2. Click the skill to open it
3. Click **···** next to the toggle → **Delete** → confirm
4. **+** → **Create skill** → **Upload a skill** → pick the new `supertutor.skill`
5. Toggle it on
6. **Start a new conversation** — open chats keep the old version for their whole session

### One thing you will lose

`references/curriculum.md`, `references/progress.md`, and `references/weak-areas.md` are
written to *during conversations*, and those edits live in the chat session — not in the
copy you uploaded. Re-uploading resets all three to blank templates.

So before you delete: open the skill in Claude, ask it to print the current contents of
all three files, and paste them into your local copies. Otherwise you lose your
curriculum, your progress history, and your weak-areas list.

### Checking whether you're out of date

```bash
gh release view --repo sayeemabdullah/supertutor --json tagName --jq .tagName
```

Or look at [Releases](../../releases/latest). If that tag is newer than the one you
installed, re-download and re-upload. There's no version string inside the skill itself,
so if you're unsure, re-download — it costs a minute and is always safe.

---

## First run

Run `/plan` and name a subject. The skill asks three questions — the goal, what you
already know, and how much time you have — then builds a curriculum and saves it to
`references/curriculum.md`. Everything after that reads from the saved state.

As you work, `/learn` and `/quiz` append to `references/progress.md` (dates, accuracy vs.
confidence) and log shaky concepts to `references/weak-areas.md`, so `/status` and
`/review` have real history to work from rather than starting fresh each session.

---

## How it's built

```
supertutor/
├── SKILL.md                      # ~80-line router: frontmatter, routing table, pedagogy rules
└── references/
    ├── curriculum-design.md      # /plan
    ├── teaching.md               # /learn
    ├── assessment.md             # /quiz
    ├── feynman.md                # /explain
    ├── spaced-review.md          # /review
    ├── progress-tracking.md      # /status
    ├── exam-prep.md              # /exam
    ├── study-methods.md          # /methods
    ├── curriculum.md             # stateful — your active plan
    ├── progress.md               # stateful — units done, accuracy vs. confidence
    └── weak-areas.md             # stateful — missed questions, priority-ordered
```

Skills load in three stages: the `description` is always in context, the SKILL.md body
loads when the skill triggers, and reference files load only when needed. Putting all 8
workflows in one file would load mostly-irrelevant instruction on every request.

So `SKILL.md` is just a routing table. Ask for a quiz, it reads `references/assessment.md`
and nothing else. Every workflow file ends with a `Rules` section encoding that domain's
failure mode — accepting a vague answer as correct, inflating praise, presenting untested
material as learned.

---

## What it won't do

These constraints are deliberate, not oversights:

- **Won't accept a vague answer as correct.** "Sort of" and hand-waving are gaps; it
  names the specific missing piece.
- **Won't inflate praise.** Warm about the person, exacting about the answer. "Close"
  when it isn't is a disservice.
- **Won't present untested material as learned.** Readiness verdicts are given against
  the stated goal, with the untested category called out explicitly.
- **Won't claim to track what it can't.** Claude cannot initiate contact, so spaced
  review only runs when you return; for heavy memorization, a dedicated
  spaced-repetition tool schedules better, and the skill says so.
- **Won't promise a grade or an outcome.**

---

## Extending it

To add a workflow:

1. Write `references/<name>.md` — a scope line, the workflow, then a `Rules` section
   covering that domain's failure mode.
2. Add a row to the routing table in `SKILL.md`.
3. Add the slash command to the table in `SKILL.md`, and a row to the table in this
   README.
4. **Add the workflow to the `description` field.** This is the step people forget, and
   skipping it means the workflow never triggers — Claude decides whether to use a skill
   based only on its description.
5. Run `make check`, open a PR, then tag a release.

---

## Building and releasing

**You never build, commit, or push `supertutor.skill`.** CI owns that file.

Edit `supertutor/`, open a PR, and that's the whole job. CI rebuilds the archive, commits
it to your branch, and it reaches `main` with your merge. Releases are built and published
by CI too. `make hooks` installs a guard that stops the archive being staged by hand.

```bash
make hooks    # once — installs a pre-commit guard against hand-built archives
make check    # structural validation, same as CI
make skill    # rebuild locally to inspect; do not commit the result
```

| When | What runs |
|---|---|
| Every PR | `validate.yml` — validates, rebuilds, and commits the archive to the PR branch if it's stale |
| Push to `main` | Same workflow in verify-only mode; fails if `main`'s archive drifts from source |
| Push a `v*` tag | `release.yml` — validates, builds, and attaches `supertutor.skill` to a GitHub Release |

### Cutting a release

A maintainer pushes a tag; CI does everything else:

```bash
git tag v1.0 && git push origin v1.0
```

The released asset is byte-identical to the one on `main` — `scripts/build.sh` normalizes
file timestamps and sorts the file list before zipping, so the same source always produces
the same file.

`scripts/validate.py` enforces the invariants that break the skill silently: frontmatter
is exactly `name` + `description` on one line, every routing row resolves to a real file,
every workflow file has a `Rules` section, the slash-command tables in `SKILL.md` and this
README match, and the three stateful files ship empty.

---

`SUPERTUTOR-SPEC.md` contains the full verbatim build spec the skill was generated from.
