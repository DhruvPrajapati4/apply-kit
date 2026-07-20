# apply-kit

A set of [Claude Code](https://claude.com/claude-code) skills that tailor your
LaTeX resume to a specific job posting, faithfully and on one page.

You give Claude a job URL or a pasted job description. apply-kit reads the
posting, checks how well your resume fits, tailors a copy to mirror the role's
language, and renders a submittable PDF. Your master resume is never modified,
and nothing is ever invented: the skills only reorder and rephrase what your
resume already says.

> **Status:** early access / closed-user-group testing. apply-kit is packaged as
> an installable Claude Code plugin and works within whatever template your resume
> already uses (`.tex` or `.docx`). PDF ingest and a standalone Agent SDK guide are
> still on the roadmap below.

## The pipeline

Each skill does one narrow job and writes its artifact to Claude's scratchpad, so
you can run the whole thing or any single step.

| Skill | What it does |
|---|---|
| `ingest-resume` | Takes your own resume file (`.tex` or `.docx`) as the working master in your own template, and checks it has the sections a software-engineering resume needs. Polishes an existing resume; never authors one or invents missing sections. |
| `extract-jd` | Fetches a job URL (or takes pasted text) and normalizes it into a structured brief: role, seniority, must-haves, and verbatim ATS keywords. |
| `resume-fit-report` | Read-only. Scores how well your master resume matches the JD and separates presentation gaps (fixable) from genuine gaps (never invented). |
| `tailor-resume` | Copies your master `.tex` to the scratchpad and applies faithful edits in the resume's own template: reorders and rephrases to hit the JD's keywords, surfaces reserve bullets, trims to one page. |
| `render-resume` | Compiles the tailored `.tex` to PDF with `latexmk` (falling back to tectonic or pdflatex) and enforces the one-page rule. |
| `apply-to-job` | Orchestrator. Runs the stages in order and pauses for your review before rendering. |

Each stage also has a matching **scoped subagent** (`agents/`) with a minimal tool
allowlist, so a stage physically cannot overstep: the extractor is the only one
with web access, the analyst is read-only, the tailor has no web or shell (it
cannot exfiltrate your resume or run git), and the renderer only compiles.

## Core principles

- **Never invent.** Every claim in the output traces to content already in your
  master resume. Genuine gaps are reported to you, never written into the resume.
- **One page, always.** Length is treated as a fixed budget and the render step
  fails if the resume spills onto a second page.
- **You stay in the loop.** The orchestrator shows you the diff and change log
  before anything is rendered.
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

In Claude Code, from your resume project:

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

## Roadmap

- PDF resume ingest (best-effort: a PDF has no layout structure to preserve, so
  this can keep content and section order but not reproduce the original design).
- A "Using apply-kit from the Agent SDK" guide so the same pipeline can run
  outside Claude Code.

Already shipped: installable plugin with a marketplace entry; a scoped subagent
per pipeline stage; generic `.tex`/`.docx` resume input with a software-engineering
section-completeness check; bundled `humanize-text` so generated prose ships
human-clean; and agent-behavior guardrails (prompt-injection resistance, no
fabrication, private data kept local, no instruction leaking, one-page rule)
enforced by tool scoping and hooks. See [`GUARDRAILS.md`](GUARDRAILS.md).

## License

TBD before public release.
