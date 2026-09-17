---
name: render-resume
description: Compile a LaTeX resume to PDF with latexmk (falling back to tectonic or pdflatex) and report the output path, surfacing compile errors clearly. Use whenever the user wants to build, render, compile, or generate the PDF of their resume .tex — typically right after tailoring, or to rebuild the master. Detects the available TeX engine and gives install guidance if none is present.
---

# render-resume

Compile a resume `.tex` (default: the scratchpad `tailored.tex`) to PDF.
Deterministic — no tailoring decisions happen here.

## Input
- Path to a `.tex` (default: `tailored.tex` in the scratchpad; falls back to the
  working master, `master.tex` in the scratchpad or `./resume/main.tex`, if asked
  to render the master).

## Engine fidelity — important
This resume is authored for **pdfLaTeX** (`\pdfgentounicode` for ATS + `roboto`
Type1 fonts). `latexmk` (→ pdflatex) renders it **faithfully** and needs no shim —
prefer it. **Tectonic runs XeTeX and does NOT render this resume correctly:** it
crashes on `fontawesome5`, lacks the pdfTeX ATS primitives, and falls back from
Roboto to a Computer Modern serif. `render.sh` auto-shims tectonic so it at least
produces a PDF, but treat that as a rough preview only — the final PDF
the user submits should come from pdflatex/latexmk (or Overleaf). Tell the user
this if only tectonic is available.

## The page budget
apply-kit does not force a one-page resume. The budget is the **master resume's own
page count**, so a two- or three-page senior/staff/manager master stays that long and
a one-page master stays one page. A tailored copy may come in shorter than the
budget; it may never come in longer.

Before rendering a tailored resume, read the budget from the `.page-budget` file
next to the source master (written by `ingest-resume`) and pass it as the script's
second argument. If that file does not exist, ask the user how many pages their
master is, write the answer there, then render. Rendering the master itself needs no
argument: the script measures it and records the real count.

## Procedure
1. Run the bundled render script,
   `"${CLAUDE_SKILL_DIR}/scripts/render.sh" <tex-file> [page-budget]`
   (when installed as a plugin, `${CLAUDE_SKILL_DIR}` resolves to this skill's
   directory; if that variable is unset, fall back to `scripts/render.sh` relative
   to this skill). It:
   - detects `latexmk` (preferred, faithful), else `tectonic` (preview-only,
     see fidelity note), else `pdflatex`/`xelatex`;
   - for tectonic, compiles a shimmed throwaway copy; other engines use the file as-is;
   - compiles in the file's directory and prints the PDF path;
   - **enforces the page budget**: parses the TeX log for the page count and exits
     non-zero (code 5) if the resume ran longer than the budget. The budget is the
     second argument, else a `.page-budget` file next to the `.tex`, else 1.
2. **If no TeX engine is found**, the script exits non-zero with install guidance.
   Relay it: on macOS, `brew install --cask mactex-no-gui` (full, includes
   `latexmk`) or `brew install tectonic` (lightweight, auto-fetches packages).
   If the user only ever compiles on Overleaf, don't push a local install — just
   hand them the tailored `.tex` path to upload.
3. **On compile error**, read the `.log`, quote the first real error (the line
   after `! `) and the offending source line, and propose a fix. Common causes
   here: unescaped specials (`& % $ # _`) introduced during tailoring, or a
   missing package (`roboto`, `fontawesome5`) — tectonic auto-fetches these;
   a minimal TeX install may not have them.

## Output
- Report the PDF path so the user can open/download it.
- Offer to open it (`open <pdf>` on macOS).

## Guardrails
- **Local and deterministic.** Compilation happens locally via `render.sh`. Never
  upload the `.tex` or `.pdf` to any external service; if the user wants Overleaf,
  hand them the local path to upload themselves.
- **No content decisions here.** This skill compiles; it does not edit or invent
  resume content. If the build fails, fix LaTeX syntax only — never alter the
  meaning of a bullet to make it compile.
- **Keep outputs private** — PDFs land in the scratchpad or the git-ignored
  `applications/` folder, never committed. See
  [`GUARDRAILS.md`](../../GUARDRAILS.md).
