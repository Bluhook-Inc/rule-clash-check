#!/usr/bin/env python3
"""Find likely rule clashes using only the Python 3.10+ standard library."""

import argparse
import itertools
import json
from pathlib import Path
import re
import sys


STOP_WORDS = set("""+a an the and or but if then else as at by for from in into of on to with without
about above after again against all also am any are be because been before being
below between both can could did do does doing down during each few further had
has have having he her here hers herself him himself his how i it its itself just
me more most my myself nor now off once other our ours ourselves out over own same
she so some such than that their theirs them themselves there these they this
those through too under until up very was we were what when where which while
who whom why will would you your yours yourself yourselves every within must
never always only not no required forbidden should stop avoid don t s
""".split())
BULLET = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")
RULE_WORD = re.compile(r"\b(?:must|never|always|only|do not|don't|no|required|forbidden|should)\b", re.I)
NEGATIVE = re.compile(r"\b(?:never|do not|don't|no|not|forbidden|stop|avoid)\b", re.I)
VALUE = re.compile(
    r"\b\d+(?:,\d{3})*(?:\.\d+)?(?:[:/-]\d+)*(?:\s*[ap]m\b)?"
    r"|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.I,
)


def keywords(text):
    """Fold common plurals so email/emails and reply/replies can match."""
    result = set()
    for word in re.findall(r"[a-z]{4,}", text.lower()):
        if word in STOP_WORDS:
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = word[:-1]
        if len(word) >= 4 and word not in STOP_WORDS:
            result.add(word)
    return result


def values(text):
    # List markers are not rule quantities.
    text = BULLET.sub("", text)
    return {re.sub(r"[\s,]", "", match.lower()) for match in VALUE.findall(text)}


def extract_rules(paths):
    """Read roots plus one import level, preserving source locations."""
    rules = []
    seen_lines = set()
    visited = set()

    def read(path, depth):
        path = Path(path)
        identity = path.resolve()
        # A file seen as an import may still need expansion as an explicit root.
        if (identity, depth) in visited:
            return
        visited.add((identity, depth))
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            print(f"Warning: cannot read {path}: {error}", file=sys.stderr)
            return
        fence = None
        for line_number, raw in enumerate(lines, 1):
            text = raw.strip()
            if fence:
                if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", text):
                    fence = None
                continue
            opening = re.match(r"^(`{3,}|~{3,})", text)
            if opening:
                fence = opening.group(1)
                continue
            imported = re.fullmatch(r"@(.+\.md)", text)
            if imported:
                if depth == 0:
                    read(path.parent / imported.group(1), depth + 1)
                continue
            if text and (BULLET.match(text) or RULE_WORD.search(text)):
                location = (identity, line_number)
                if location not in seen_lines:
                    seen_lines.add(location)
                    rules.append({"file": str(path), "line": line_number, "text": text})

    for path in paths:
        read(path, 0)
    return rules


def find_candidates(rules, min_shared=2):
    annotated = [(rule, keywords(rule["text"]), bool(NEGATIVE.search(rule["text"])),
                  values(rule["text"])) for rule in rules]
    pairs = []
    for a, b in itertools.combinations(annotated, 2):
        if (a[0]["file"], a[0]["line"]) == (b[0]["file"], b[0]["line"]):
            continue
        shared = sorted(a[1] & b[1])
        opposite = a[2] != b[2]
        different_values = a[3] != b[3]
        if len(shared) < min_shared or not (opposite or different_values):
            continue
        reason = []
        if opposite:
            reason.append("different polarity")
        if different_values:
            reason.append("different numbers, dates, or times")
        pairs.append({"score": len(shared) + 2 * opposite + different_values,
                      "a": a[0], "b": b[0], "shared": shared, "reason": reason})
    return sorted(pairs, key=lambda pair: -pair["score"])[:200]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-shared", type=int, default=2)
    try:
        args = parser.parse_args(argv)
        if args.min_shared < 1:
            parser.error("--min-shared must be at least 1")
    except SystemExit:
        return 0
    pairs = find_candidates(extract_rules(args.paths), args.min_shared)
    if args.json:
        print(json.dumps(pairs, indent=2))
    else:
        for pair in pairs:
            print(f"Score: {pair['score']}")
            for side in ("a", "b"):
                rule = pair[side]
                print(f"{rule['file']}:{rule['line']}: {rule['text']}")
            print(f"Shared: {', '.join(pair['shared'])}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
