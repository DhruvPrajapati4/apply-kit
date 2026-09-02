# apply-kit

A set of [Claude Code](https://claude.com/claude-code) skills that tailor your
LaTeX resume to a specific job posting, faithfully and on one page.

You give Claude a job URL or a pasted job description. apply-kit reads the
posting, checks how well your resume fits, tailors a copy to mirror the role's
language, and renders a submittable PDF. It can also find the postings for you,
by querying company applicant tracking systems directly, including companies it
was never told about. Your master resume is
never modified, and nothing is ever invented: the skills only reorder and
rephrase what your resume already says.

> **Status:** early access. apply-kit is packaged as
> an installable Claude Code plugin and works within whatever template your resume
> already uses (`.tex` or `.docx`). PDF ingest and a standalone Agent SDK guide are
> still on the roadmap below.

## The pipeline

Each skill does one narrow job and writes its artifact to Claude's scratchpad, so
you can run the whole thing or any single step.

| Skill | What it does |
|---|---|
| `find-jobs` | Searches company ATS boards (Greenhouse, Lever, Ashby, Workable, Workday) directly for live openings, filtered on location, title, stack, and the years of experience the posting actually states. Casts beyond its bundled company list via Workable's cross-company index, and grows that list with every company it resolves. Use it when you do not have a specific posting yet. |
| `ingest-resume` | Takes your own resume file (`.tex` or `.docx`) as the working master in your own template, and checks it has the sections a software-engineering resume needs. Polishes an existing resume; never authors one or invents missing sections. |
| `extract-jd` | Fetches a job URL (or takes pasted text) and normalizes it into a structured brief: role, seniority, must-haves, and verbatim ATS keywords. |
| `resume-fit-report` | Read-only. Scores how well your master resume matches the JD and separates presentation gaps (fixable) from genuine gaps (never invented). |
| `tailor-resume` | Copies your master `.tex` to the scratchpad and applies faithful edits in the resume's own template: reorders and rephrases to hit the JD's keywords, surfaces reserve bullets, trims to one page. |
| `render-resume` | Compiles the tailored `.tex` to PDF with `latexmk` (falling back to tectonic or pdflatex) and enforces the one-page rule. |
| `answer-questions` | Drafts the free-text parts of an application ("why us", "why you", "a project you are proud of") from your real resume and the posting, then hands back the questions only you can answer: salary, notice period, work authorization. Self-identification answers come from `resume/profile.json` if you recorded them, and are left blank if you did not. |
| `submit-application` | Fills the application form from the tailored PDF and your drafted answers, then stops at the submit button for your confirmation. Skips portals that need an account (Workday and similar), never solves a CAPTCHA, and leaves salary and availability fields for you. |
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
- **Honest about coverage.** Discovery reaches beyond its bundled company list,
  but no job board publishes an index of employers, so no search here is
  complete. Every report says which companies were scanned, which came up empty,
  and what was never reachable, because a short list without that context reads
  as "nothing is out there".
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
4. Optional: answer the self-identification questions once. Every form asks the
   same voluntary EEO questions (gender, race and ethnicity, disability, veteran
   status), and the answers do not change between applications. Record them in
   `resume/profile.json` and form filling stops asking:

   ```json
   {
     "self_identification": {
       "gender": "...",
       "race_ethnicity": "...",
       "hispanic_or_latino": "...",
       "disability": "...",
       "veteran_status": "..."
     }
   }
   ```

   `resume/` is git-ignored, so this stays on your machine. Any field you leave
   out, and the whole file if you skip this, means that question is left blank on
   the form for you to handle. These values are never inferred from your name,
   your location, or your resume, and every one that gets filled shows up in the
   pre-submit manifest. Salary, notice period and work authorization stay out of
   the file on purpose: they are negotiable or offer-specific, so a stored answer
   would be wrong more often than right.

## Usage

In Claude Code, from your resume project. For the whole hunt in one command:

```
/find-and-apply backend roles in Berlin, Rust and Postgres, 4 to 7 years
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
/find-jobs data platform roles in Dublin or remote, Scala and Spark, senior
```

Add `--skip-providers workday` to the search if you only want roles that can be
applied to without creating an account.

That returns a ranked shortlist of live openings with real apply links, plus an
honest note on which companies were scanned and came up empty and which could not
be scanned at all. Feed any lead straight into `/apply-to-job`.

Discovery is not limited to the companies bundled with the plugin. It first
searches Workable's public cross-company index, which needs no list and turns up
employers nobody curated, then scans the boards it has slugs for. Any new company
it resolves is added to the bundled list, so each run starts wider than the last.
The gap to be aware of: Greenhouse, Lever and Ashby publish per-board endpoints
and no index of boards, so a company on one of those is only reachable once its
slug is known.

The search script also runs standalone, without Claude, in three modes:

```
# 1. discover: no company list at all, finds employers nobody curated
python3 skills/find-jobs/scripts/ats_search.py discover \
  --query 'backend engineer' --location india \
  --title 'backend|platform' --stack 'go,kubernetes' \
  --companies skills/find-jobs/references/companies.json --markdown leads.md

# 2. probe: resolve company names to boards and keep what it finds
python3 skills/find-jobs/scripts/ats_search.py probe \
  --names 'Proximity Works, Fortanix' --stage series-b \
  --append skills/find-jobs/references/companies.json

# 3. search: the curated list, filtered hard
python3 skills/find-jobs/scripts/ats_search.py search \
  --companies skills/find-jobs/references/companies.json \
  --location 'berlin|remote' --title 'backend|platform' \
  --exclude 'manager|intern' --stack 'rust,postgres' \
  --stage 'series-[abc]' --markdown leads.md
```

`discover` queries Workable's public cross-company job index, so it reaches
companies that are not in any list. That is also its limit: Greenhouse, Lever and
Ashby expose per-board endpoints and no index of boards, so reaching a company on
those still means knowing its slug.

`probe` resolves a company name to its board by guessing the plausible slug forms
and seeing which exist, since slugs frequently do not match the company name
(`Harness` is `harnessinc`, `Temporal` is `temporaltechnologies`). With
`--append` it merges what it verified into
`skills/find-jobs/references/companies.json`, with the date and an optional
funding stage, so the list grows as you use it rather than by hand. No ATS
publishes funding stage, so `--stage` records what you tell it and nothing more;
`search --stage` then narrows a run to those companies.

## Roadmap

- PDF resume ingest (best-effort: a PDF has no layout structure to preserve, so
  this can keep content and section order but not reproduce the original design).
- A "Using apply-kit from the Agent SDK" guide so the same pipeline can run
  outside Claude Code.

Already shipped: a one-command search-to-application run; job discovery straight
from company ATS boards, including a listless cross-company search and a company
list that grows itself; voluntary self-identification answers recorded once
instead of per application; grounded
free-text answers for application forms; gated form filling that stops at the
submit button; installable
plugin with a marketplace entry; a scoped subagent per pipeline stage; generic `.tex`/`.docx` resume input with a software-engineering
section-completeness check; bundled `humanize-text` so generated prose ships
human-clean; and agent-behavior guardrails (prompt-injection resistance, no
fabrication, private data kept local, no instruction leaking, one-page rule)
enforced by tool scoping and hooks. See [`GUARDRAILS.md`](GUARDRAILS.md).

## License

[MIT](LICENSE).
