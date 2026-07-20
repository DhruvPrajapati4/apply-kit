#!/usr/bin/env python3
"""PostToolUse guard: fail loudly when a render violated the one-page rule.

render.sh already exits non-zero (code 5) and prints "ONE-PAGE RULE VIOLATED" when
the resume overflows one page. This hook re-surfaces that as a blocking signal
after the render command runs, so a two-page PDF can never quietly pass as done:
the model is told to condense and re-render before using the output.

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
    if "ONE-PAGE RULE VIOLATED" in haystack:
        sys.stderr.write(
            "apply-kit guardrail: the resume rendered to more than one page. "
            "Condense (tighten wording, drop the least-relevant bullet) and "
            "re-render until it is exactly one page. Do not use this PDF.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
