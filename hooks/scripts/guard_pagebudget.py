#!/usr/bin/env python3
"""PostToolUse guard: fail loudly when a render blew the page budget.

The budget is the master resume's own page count (one page for most resumes,
two or three for a senior/staff/manager profile), not a hardcoded 1. render.sh
already exits non-zero (code 5) and prints "PAGE BUDGET EXCEEDED" when the
tailored resume runs longer than the master. This hook re-surfaces that as a
blocking signal after the render command runs, so an overlong PDF can never
quietly pass as done: the model is told to condense and re-render.

Reads the PostToolUse JSON payload on stdin; exit 2 feeds the reason back to the
model. Fails open on errors.
"""
import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    haystack = json.dumps(data.get("tool_response") or {}) + json.dumps(
        data.get("tool_input") or {}
    )
    if "PAGE BUDGET EXCEEDED" in haystack:
        sys.stderr.write(
            "apply-kit guardrail: the resume rendered longer than the master "
            "resume's page count. Condense (tighten wording, drop the "
            "least-relevant bullet) and re-render until it is back within the "
            "page budget. Do not use this PDF.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
