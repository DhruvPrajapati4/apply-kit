#!/usr/bin/env python3
"""PreToolUse guard: refuse to stage or commit personal data.

apply-kit keeps a user's real resume and past applications in the git-ignored
`resume/` and `applications/` directories. A `git add -f` or a misconfigured
.gitignore could still slip them into version control, which for a public-bound
repo would leak personal data permanently into history. This hook is the hard
backstop: it inspects both what a git command is about to add and what is already
staged, and blocks (exit code 2) if anything lives under those protected
directories.

Reads the PreToolUse JSON payload on stdin; exit 2 with a reason on stderr blocks
the tool. Fails open on unexpected errors so it never wedges an unrelated command.
"""
import json
import re
import subprocess
import sys

# Match a path segment that IS `resume/` or `applications/` (anchored at start or
# after a slash). This deliberately does NOT match e.g. skills/resume-fit-report/.
PROTECTED = re.compile(r"(^|/)(resume|applications)/")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # can't parse -> don't interfere

    cmd = (data.get("tool_input") or {}).get("command", "") or ""

    candidates = set()

    # Files already staged (catches `git commit` of a forced-add resume file).
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        candidates.update(p for p in out.split("\n") if p)
    except Exception:
        pass

    # Path-looking tokens in the command itself (catches `git add -f resume/x`).
    for tok in cmd.split():
        if PROTECTED.search(tok):
            candidates.add(tok)

    hits = sorted({p for p in candidates if PROTECTED.search(p)})
    if hits:
        sys.stderr.write(
            "apply-kit guardrail: refusing to stage/commit personal data under "
            "resume/ or applications/: " + ", ".join(hits) + "\n"
            "These directories are git-ignored on purpose. If this is intentional, "
            "do it manually outside this session.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
