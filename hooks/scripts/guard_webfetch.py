#!/usr/bin/env python3
"""PreToolUse guard: refuse a WebFetch that carries resume LaTeX content.

The only pipeline stage with web access is the JD extractor, and it must fetch
only the job posting, never send the user's resume anywhere. As a belt-and-braces
check behind that tool scoping, this hook blocks any WebFetch whose arguments
contain LaTeX resume markers (e.g. \\resumeItem, \\resumeSubheading,
\\begin{document}). A genuine job-posting fetch never contains these, so the
false-positive risk is low.

Reads the PreToolUse JSON payload on stdin; exit 2 blocks. Fails open on errors.
"""
import json
import re
import sys

RESUME_MARKERS = re.compile(
    r"\\resumeItem|\\resumeSubheading|\\resumeProjectHeading|\\begin\{document\}"
)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    blob = json.dumps(data.get("tool_input") or {})
    if RESUME_MARKERS.search(blob):
        sys.stderr.write(
            "apply-kit guardrail: refusing a WebFetch that appears to contain "
            "resume LaTeX content. Resume data must never be sent to the web.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
