#!/usr/bin/env python3
"""PreToolUse guard: refuse a shell command that submits a job application.

Submitting an application is irreversible and outward-facing, so it belongs to
the user, behind an explicit per-application confirmation in the conversation
(see `submit-application`). Scripting it past that gate with curl or wget would
route around the only control that matters.

This hook blocks a Bash command that POSTs (or PUTs) to a known applicant
tracking system. Reading those same hosts is untouched, because discovery in
`find-jobs` depends on it: only write verbs are refused.

Scope, stated plainly: this catches the shell path. It cannot see a click in a
browser tool, so a submit button in `claude-in-chrome` is gated by the human
confirmation in the skill, not by this hook. That is a real limit, not an
oversight, and the docs say so.

Reads the PreToolUse JSON payload on stdin; exit 2 blocks. Fails open on errors.
"""
import json
import re
import sys

ATS_HOSTS = re.compile(
    r"""(
        greenhouse\.io | lever\.co | ashbyhq\.com | workable\.com |
        myworkdayjobs\.com | icims\.com | taleo\.net | successfactors\.com |
        smartrecruiters\.com | jobvite\.com | recruitee\.com | breezy\.hr |
        bamboohr\.com | rippling\.com | teamtailor\.com | freshteam\.com
    )""",
    re.I | re.X,
)

# A write verb: an explicit method flag, or any form/data payload flag, which
# curl turns into a POST on its own.
WRITE_VERB = re.compile(
    r"""(
        -X\s*['"]?(POST|PUT|PATCH) |
        --request\s+['"]?(POST|PUT|PATCH) |
        \s(-d|--data|--data-raw|--data-binary|--data-urlencode|-F|--form)\b |
        --upload-file | --post-data | --post-file
    )""",
    re.I | re.X,
)

USES_HTTP_CLIENT = re.compile(r"\b(curl|wget|http|https|xh)\b")

# Workday's job *search* is a POST even though it only reads. find-jobs relies on
# it, so exempt that one path rather than forcing the search through a detour.
READ_ONLY_POST = re.compile(r"/wday/cxs/[^/\s]+/[^/\s]+/jobs\b", re.I)


def blocks(command: str) -> bool:
    """True if this shell command would write to an ATS."""
    if not command:
        return False
    if not USES_HTTP_CLIENT.search(command):
        return False
    if not ATS_HOSTS.search(command):
        return False
    if not WRITE_VERB.search(command):
        return False  # a read of a job board is exactly what find-jobs does
    if READ_ONLY_POST.search(command):
        return False
    return True


def selftest() -> None:
    allow = [
        "curl -s https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        "curl -s https://api.lever.co/v0/postings/acme?mode=json",
        "curl -X POST https://x.wd3.myworkdayjobs.com/wday/cxs/x/External/jobs -d '{}'",
        "curl -X POST https://api.example.com/thing -d x=1",
        "ls -la",
        "",
    ]
    deny = [
        "curl -X POST https://boards.greenhouse.io/acme/applications -d @app.json",
        "curl -F resume=@r.pdf https://jobs.lever.co/acme/123/apply",
        "wget --post-file=app.json https://acme.ashbyhq.com/api/apply",
        "curl --request PUT https://acme.icims.com/candidate --data-binary @x",
    ]
    for c in allow:
        assert not blocks(c), f"should allow: {c}"
    for c in deny:
        assert blocks(c), f"should block: {c}"
    print("selftest: all checks passed")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    if not blocks((data.get("tool_input") or {}).get("command") or ""):
        return 0

    sys.stderr.write(
        "apply-kit guardrail: refusing a shell command that writes to an "
        "applicant tracking system. Submitting an application is irreversible "
        "and needs the user's explicit per-application confirmation. Use the "
        "submit-application skill, which prepares the submission and stops at "
        "the submit control, rather than POSTing to the ATS directly.\n"
    )
    return 2


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    sys.exit(main())
