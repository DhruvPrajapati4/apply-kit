# apply-kit

A set of [Claude Code](https://claude.com/claude-code) skills that tailor your
LaTeX resume to a specific job posting, faithfully and on one page.

You give Claude a job URL or a pasted job description. apply-kit reads the
posting, checks how well your resume fits, tailors a copy to mirror the role's
language, and renders a submittable PDF. Your master resume is never modified,
and nothing is ever invented: the skills only reorder and rephrase what your
resume already says.

> **Status:** early / closed-user-group testing. The skills currently assume a
> single-file LaTeX master resume (Jake's Resume Template). Support for pasting a
> resume as DOCX / PDF / plain LaTeX, plus packaging as an installable plugin, is
> on the roadmap below.

## The pipeline

Each skill does one narrow job and writes its artifact to Claude's scratchpad, so
you can run the whole thing or any single step.

| Skill | What it does |
|---|---|
| `extract-jd` | Fetches a job URL (or takes pasted text) and normalizes it into a structured brief: role, seniority, must-haves, and verbatim ATS keywords. |
| `resume-fit-report` | Read-only. Scores how well your master resume matches the JD and separates presentation gaps (fixable) from genuine gaps (never invented). |
| `tailor-resume` | Copies your master `.tex` to the scratchpad and applies faithful, template-aware edits: reorders and rephrases to hit the JD's keywords, surfaces reserve bullets, trims to one page. |
| `render-resume` | Compiles the tailored `.tex` to PDF with `latexmk` (falling back to tectonic or pdflatex) and enforces the one-page rule. |
| `apply-to-job` | Orchestrator. Runs all four in order and pauses for your review before rendering. |

## Core principles

- **Never invent.** Every claim in the output traces to content already in your
  master resume. Genuine gaps are reported to you, never written into the resume.
- **One page, always.** Length is treated as a fixed budget and the render step
  fails if the resume spills onto a second page.
- **You stay in the loop.** The orchestrator shows you the diff and change log
  before anything is rendered.
- **Your master is sacred.** All edits happen on a scratchpad copy. Your original
  `.tex` is never touched.

## Prerequisites

- [Claude Code](https://claude.com/claude-code).
- A LaTeX toolchain for rendering. On macOS:
  - `brew install --cask mactex-no-gui` (full, includes `latexmk`, recommended), or
  - `brew install tectonic` (lightweight; preview-quality only for this template).
  - No local install? You can still use the tailored `.tex` on
    [Overleaf](https://overleaf.com).

## Setup

1. Copy the `.claude/skills/` directory into your resume project so Claude Code
   picks the skills up (project-scoped skills live under `.claude/skills/`).
2. Put your master LaTeX resume at `resume/main.tex` (this path is git-ignored so
   your resume never gets committed). The skills are tuned for Jake's Resume
   Template but work with any single-file `.tex`.
3. Optional: mark reserve bullets. Any commented-out `\resumeItem{...}` line is
   treated as a real, pre-approved accomplishment held in reserve that tailoring
   may swap in when a job makes it more relevant.

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

- Accept a resume pasted as DOCX / PDF / plain LaTeX instead of assuming a fixed
  master path.
- Guardrails for public use: resist instructions embedded in fetched job
  descriptions, and keep skill internals from leaking into output.
- Package as an installable Claude Code plugin with a marketplace entry.

## License

TBD before public release.
