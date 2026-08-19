# apply-kit

A set of [Claude Code](https://claude.com/claude-code) skills that tailor your
LaTeX resume to a specific job posting, faithfully and on one page.

You give Claude a job URL or a pasted job description. apply-kit reads the
posting, checks how well your resume fits, tailors a copy to mirror the role's
language, and renders a submittable PDF. It can also find the postings for you,
by querying company applicant tracking systems directly. Your master resume is
never modified, and nothing is ever invented: the skills only reorder and
rephrase what your resume already says.

> **Status:** early access / closed-user-group testing. apply-kit is packaged as
> an installable Claude Code plugin and works within whatever template your resume
> already uses (`.tex` or `.docx`). PDF ingest and a standalone Agent SDK guide are
> still on the roadmap below.

## The pipeline

Each skill does one narrow job and writes its artifact to Claude's scratchpad, so
you can run the whole thing or any single step.

| Skill | What it does |
|---|---|
| `find-jobs` | Searches company ATS boards (Greenhouse, Lever, Ashby, Workable, Workday) directly for live openings, filtered on location, title, stack, and the years of experience the posting actually states. Use it when you do not have a specific posting yet. |
| `ingest-resume` | Takes your own resume file (`.tex` or `.docx`) as the working master in your own template, and checks it has the sections a software-engineering resume needs. Polishes an existing resume; never authors one or invents missing sections. |
| `extract-jd` | Fetches a job URL (or takes pasted text) and normalizes it into a structured brief: role, seniority, must-haves, and verbatim ATS keywords. |
| `resume-fit-report` | Read-only. Scores how well your master resume matches the JD and separates presentation gaps (fixable) from genuine gaps (never invented). |
| `tailor-resume` | Copies your master `.tex` to the scratchpad and applies faithful edits in the resume's own template: reorders and rephrases to hit the JD's keywords, surfaces reserve bullets, trims to one page. |
| `render-resume` | Compiles the tailored `.tex` to PDF with `latexmk` (falling back to tectonic or pdflatex) and enforces the one-page rule. |
| `answer-questions` | Drafts the free-text parts of an application ("why us", "why you", "a project you are proud of") from your real resume and the posting, then hands back the questions only you can answer: demographic fields, salary, notice period, work authorization. |
| `submit-application` | Fills the application form from the tailored PDF and your drafted answers, then stops at the submit button for your confirmation. Skips portals that need an account (Workday and similar), never solves a CAPTCHA, and leaves demographic and salary fields for you. |
| `find-and-apply` | The whole hunt in one command: search, score every lead against your resume, show you a ranked shortlist, then tailor, render, answer and prepare each application you pick. |
| `apply-to-job` | Single-job orchestrator. Runs the stages in order and pauses for your review before rendering. |

Each stage also has a matching **scoped subagent** (`agents/`) with a minimal tool
allowlist, so a stage physically cannot overstep: the scout and the extractor are
the only ones with web access and neither can edit your resume, the analyst is
read-only, the tailor has no web or shell (it cannot exfiltrate your resume or run
git), and the renderer only compiles.

## Core principles

- **Never invent.** Every claim in the output traces to content already in your
  master resume. Genuine gaps are reported to you, never written into the resume.
- **One page, always.** Length is treated as a fixed budget and the render step
  fails if the resume spills onto a second page.
- **You stay in the loop.** The orchestrator shows you the diff and change log
  before anything is rendered, and nothing is ever submitted without your explicit
  yes for that specific application.
- **Your master is sacred.** All edits happen on a scratchpad copy. Your original
  `.tex` is never touched.
- **Safe with untrusted input.** Job postings are treated as data, never as
  instructions, so text planted in a posting cannot redirect the assistant or push
  fabrications into your resume. Your resume data stays local and is never sent to
  the web. See [`GUARDRAILS.md`](GUARDRAILS.md) for the full set.

## Prerequisites

- [Claude Code](https://claude.com/claude-code).
- `python3` on your PATH (used by the guardrail hooks).
- `pandoc` if you want to ingest a `.docx` resume (`brew install pandoc`).
  Not needed if your resume is already `.tex`.
- A LaTeX toolchain for rendering. On macOS:
  - `brew install --cask mactex-no-gui` (full, includes `latexmk`, recommended), or
  - `brew install tectonic` (lightweight; preview-quality only for this template).
  - No local install? You can still use the tailored `.tex` on
    [Overleaf](https://overleaf.com).

## Install

apply-kit is a Claude Code plugin. From Claude Code:

```
/plugin marketplace add DhruvPrajapati4/apply-kit
/plugin install apply-kit@apply-kit
```

This registers the repo as a marketplace and installs the plugin (skills, and,
as they land, agents and hooks). To iterate on the plugin locally, add the local
checkout as a marketplace instead:

```
/plugin marketplace add /path/to/apply-kit
/plugin install apply-kit@apply-kit
```

## Setup

1. Install the plugin (above).
2. Bring your own resume. Either point `ingest-resume` at a `.tex` or `.docx`
   file, or put a master LaTeX resume at `resume/main.tex` in your resume project
   (this path is git-ignored so your resume never gets committed). apply-kit works
   within whatever template your resume already uses; it has no house template of
   its own.
3. Optional: mark reserve bullets. Any commented-out bullet line is treated as a
   real, pre-approved accomplishment held in reserve that tailoring may swap in
   when a job makes it more relevant.

## Usage

In Claude Code, from your resume project. For the whole hunt in one command:

```
/find-and-apply backend roles in Bengaluru, Go and Kubernetes, 3 to 5 years
```

That searches company boards, scores the leads against your resume, and shows
you a ranked shortlist. You pick which ones to go after; each pick is then
tailored, rendered, answered and filled in, and you are asked once per
application before anything is sent. Two decisions are always yours: which jobs,
and whether to submit each one.

For a single posting you already have:

```
/apply-to-job https://job-boards.greenhouse.io/acme/jobs/12345
```

or paste the description directly:

```
/apply-to-job <paste the full job description here>
```

Claude will produce a fit report, show you the tailored diff for approval, then
render a one-page PDF. You can also invoke any single skill on its own, for
example `/resume-fit-report` to just get a gap analysis.

If you do not have a posting in mind yet, start with discovery:

```
/find-jobs backend roles in Bengaluru, Go and Kubernetes, around 3 to 5 years
```

Add `--skip-providers workday` to the search if you only want roles that can be
applied to without creating an account.

That returns a ranked shortlist of live openings with real apply links, plus an
honest note on which companies were scanned and came up empty and which could not
be scanned at all. Feed any lead straight into `/apply-to-job`.

The search script also runs standalone, without Claude:

```
python3 skills/find-jobs/scripts/ats_search.py probe --slugs acme,acmeinc,globex
python3 skills/find-jobs/scripts/ats_search.py search \
  --companies skills/find-jobs/references/companies.json \
  --location 'bengaluru|bangalore' --title 'backend|platform' \
  --exclude 'manager|intern' --stack 'golang,kafka' --markdown leads.md
```

`probe` resolves which board a company slug lives on, since slugs frequently do
not match the company name. Verified slugs live in
`skills/find-jobs/references/companies.json`; adding to it makes later runs
faster.

## Roadmap

- PDF resume ingest (best-effort: a PDF has no layout structure to preserve, so
  this can keep content and section order but not reproduce the original design).
- A "Using apply-kit from the Agent SDK" guide so the same pipeline can run
  outside Claude Code.

Already shipped: a one-command search-to-application run; job discovery straight
from company ATS boards; grounded
free-text answers for application forms; gated form filling that stops at the
submit button; installable
plugin with a marketplace entry; a scoped subagent per pipeline stage; generic `.tex`/`.docx` resume input with a software-engineering
section-completeness check; bundled `humanize-text` so generated prose ships
human-clean; and agent-behavior guardrails (prompt-injection resistance, no
fabrication, private data kept local, no instruction leaking, one-page rule)
enforced by tool scoping and hooks. See [`GUARDRAILS.md`](GUARDRAILS.md).

## License

TBD before public release.
