# Rule Clash Check

Find the rules in your CLAUDE.md that fight each other, before your agents do.

For teams using Claude Code, Codex, or Cursor with rules files. Free and open source.

## What it finds

- Opposite instructions about the same subject.
- Different deadlines, times, dates, or spending limits.
- Duplicate rules, and rules with no clear owner (the skill catches these when it reads your files).

A script suggests pairs. The skill reads them in context and suggests one fix per clash.

## Example report

From a run on `tests/fixtures/CLAUDE.md`:

| # | Line A | Line B | Kind | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| 1 | 3: Always reply to customer emails within 1 hour. | 4: Never send customer email replies before a person approves them. | clash | An agent can't meet the 1-hour rule if nobody approves in time. | "Reply to customer emails within 1 hour, after a person approves the reply." |
| 2 | 5: Post the weekly report every Monday at 9 AM. | 6: Post the weekly report every Friday at 4 PM. | clash | Two agents could each post the report, or each wait for the other. | Keep one day and time and delete the other line. |
| 3 | 7: Deploy website changes only after staging is checked. | 8: Do not use staging for website changes; deploy directly. | clash | One rule needs staging and the other bans it. | Keep line 7 and delete line 8. |

Files checked: `tests/fixtures/CLAUDE.md`, `tests/fixtures/extra.md`.

## Install

Copy `skills/rule-clash-check` into `~/.claude/skills/` or your project's `.claude/skills/`.

```sh
mkdir -p ~/.claude/skills
cp -R skills/rule-clash-check ~/.claude/skills/
```

The script needs Python 3.10 or newer. It uses only the standard library.

## Run

In Claude Code, say: "check my rules for clashes".

Or run the script from this repository:

```sh
python3 skills/rule-clash-check/find_candidates.py CLAUDE.md AGENTS.md
python3 skills/rule-clash-check/find_candidates.py CLAUDE.md --json --min-shared 3
```

The script's raw output for the sample file:

```text
Score: 6
tests/fixtures/CLAUDE.md:3: - Always reply to customer emails within 1 hour.
tests/fixtures/CLAUDE.md:4: - Never send customer email replies before a person approves them.
Shared: customer, email, reply
```

## How it works

**The script**
- Follows one level of `@relative/path.md` imports. Imports can point outside the repo, so run it only on rules you trust.
- Warns you about missing files.
- Skips fenced code and matches words of four or more letters, with common plurals folded together.
- Pairs two lines when they share at least two words and use opposite wording or different values.
- Prints up to 200 pairs, highest score first, and always exits with status zero.
- Only reads files. It never edits them.

**The skill**
Different wording can hide a clash, so the skill also reads your files itself. It offers a patch and leaves your files alone unless you ask for edits. Each report ends with one line about our Team Rule Check waitlist.

## Why we built it

We run a large team of AI agents at Bluhook. Rule clashes were one of our most common problems.

## Next step

Want to see which jobs a team of AI agents could take off your plate? [Take the free AI evaluation](https://bluhook.com/eval).

## License

[MIT](LICENSE). Copyright Bluhook.
