#!/usr/bin/env python3
"""Mechanical de-AI pass for plain-prose files.

Replaces the high-signal typographic tells (em/en dashes, smart quotes,
ellipses, stray Unicode) with plain ASCII a human would type. Lines inside
fenced code blocks (``` ... ```) and indented code are left untouched, because
a dash or quote there is usually syntax, not style.

This handles ONLY the mechanical substitutions from section 1 of the skill.
Phrasing/structure tells (section 2) need human judgment and are not touched.

Usage:
    humanize.py <file>            # rewrite in place
    humanize.py <file> --stdout   # print result, leave file unchanged
"""
import re
import sys

# En dash between digits -> " to " (ranges); handled before the generic map.
RANGE_RE = re.compile(r"(?<=\d)\s*–\s*(?=\d)")

CHAR_MAP = {
    "—": ", ",   # em dash  -> comma+space (safe default; review for clause splits)
    "–": "-",     # en dash  -> hyphen (non-range uses)
    "‘": "'",     # left single quote
    "’": "'",     # right single quote / apostrophe
    "“": '"',     # left double quote
    "”": '"',     # right double quote
    "…": "...",  # ellipsis
    " ": " ",     # non-breaking space
    " ": " ",     # thin space
    "​": "",       # zero-width space
    "‌": "",       # zero-width non-joiner
    "﻿": "",       # BOM / zero-width no-break space
    "−": "-",     # minus sign -> hyphen
}


def transform_line(line: str) -> str:
    line = RANGE_RE.sub(" to ", line)
    for src, dst in CHAR_MAP.items():
        line = line.replace(src, dst)
    # tidy up spacing artifacts from em-dash-as-comma at a clause edge
    line = re.sub(r"\s+,", ",", line)
    line = re.sub(r",\s*,", ",", line)
    # collapse internal runs of spaces, but preserve trailing spaces
    # (two trailing spaces are a meaningful Markdown line break)
    line = re.sub(r" {2,}(?=\S)", " ", line)
    return line


def humanize(text: str) -> str:
    out, in_fence = [], False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or line.startswith("    ") or line.startswith("\t"):
            out.append(line)  # code: leave verbatim
            continue
        out.append(transform_line(line))
    return "".join(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--stdout"]
    to_stdout = "--stdout" in sys.argv[1:]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        original = f.read()
    result = humanize(original)
    if to_stdout:
        sys.stdout.write(result)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        changed = sum(1 for a, b in zip(original, result) if a != b) or (len(original) != len(result))
        print(f"humanized: {path}" + ("" if changed else " (no changes)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
