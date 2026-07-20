---
name: ingest-resume
description: Take a user's own resume file (.tex or .docx) into the pipeline as the working master, and check it has the sections a software-engineering resume needs. Use whenever the user attaches or points to a resume file to tailor, or at the start of apply-to-job when no master resume is set yet. Preserves the user's own template and content; it polishes an existing resume, it never writes one from scratch or invents missing sections.
---

# ingest-resume

Bring the user's resume into the pipeline as the working master, in their own
template, and give an honest read on whether it has what a software-engineering
resume needs. This skill does not design or author a resume: apply-kit imposes no
template, and missing content is reported, never fabricated.

## Input
- A path to a resume file: `.tex` or `.docx`.
  - `.pdf` is not supported yet (a PDF has no layout structure to preserve; see the
    roadmap). If given a PDF, say so and ask for the `.tex` or `.docx` source, or
    for the content pasted as text.

## Procedure

1. **Detect the format** by extension.
2. **Produce the working master** in the session scratchpad as `master.tex`,
   preserving the user's template:
   - `.tex` → copy the file verbatim. This fully preserves their template, macros,
     and design. Do not reformat it.
   - `.docx` → convert with `pandoc "<file>" -o master.tex --standalone`. This
     preserves content and structure (headings, bold, bullets) but not the exact
     Word styling; tell the user the converted LaTeX is a faithful-content starting
     point, not a pixel copy of their Word layout. If `pandoc` is not installed,
     stop and give the install hint (`brew install pandoc`).
3. **Section-completeness check (for software-engineering roles).** Read the
   working master and classify each section:
   - **Required:** Contact (name plus at least one of email / phone / LinkedIn /
     GitHub), Experience (work history), Skills (technical skills), Education.
   - **Expected:** Projects (strongly recommended for SWE, especially early-career).
   - **Optional (note only if present):** Summary/Objective, Certifications,
     Open-source, Publications.
   Mark each Present / Thin / Missing. "Thin" means the section exists but is
   sparse (e.g. Skills with one line, Experience with no bullets).
4. **Report, do not fix.** Missing or thin sections are surfaced to the user as a
   heads-up so they can add real content to their own resume. Never invent a
   section or its content to fill a gap.

## Output
Write `ingest-report.md` to the scratchpad and report:
- the working master path (`master.tex`) and the source format;
- the section table (Present / Thin / Missing);
- any required section that is missing or thin, phrased as a question to the user
  ("Your resume has no Skills section — add one to your source resume if you have
  the content, or proceed as-is?").

Then hand off to `resume-fit-report` / `tailor-resume`, which read this working
master. If invoked from `apply-to-job`, return control to the orchestrator.

## Guardrails
- **Polish, never author.** This skill preserves and organizes the user's real
  content. It does not write new bullets, add skills, or fill missing sections with
  invented material. Gaps are reported, not filled.
- **Preserve the user's template.** Never restyle a `.tex` into a different design;
  apply-kit has no house template.
- **Keep resume data local.** Convert and write only in the scratchpad; never send
  resume content to any external tool. See [`GUARDRAILS.md`](../../GUARDRAILS.md).
