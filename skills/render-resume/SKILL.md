---
name: render-resume
description: Compile a LaTeX resume to PDF with latexmk (falling back to tectonic or pdflatex) and report the output path, surfacing compile errors clearly. Use whenever the user wants to build, render, compile, or generate the PDF of their resume .tex — typically right after tailoring, or to rebuild the master. Detects the available TeX engine and gives install guidance if none is present.
---

# render-resume

Compile a resume `.tex` (default: the scratchpad `tailored.tex`) to PDF.
Deterministic — no tailoring decisions happen here.

## Input
- Path to a `.tex` (default: `tailored.tex` in the scratchpad; falls back to
  `./resume/main.tex` if asked to render the master).

## Engine fidelity — important
This resume is authored for **pdfLaTeX** (`\pdfgentounicode` for ATS + `roboto`
Type1 fonts). `latexmk` (→ pdflatex) renders it **faithfully** and needs no shim —
prefer it. **Tectonic runs XeTeX and does NOT render this resume correctly:** it
crashes on `fontawesome5`, lacks the pdfTeX ATS primitives, and falls back from
Roboto to a Computer Modern serif. `render.sh` auto-shims tectonic so it at least
produces a one-page PDF, but treat that as a rough preview only — the final PDF
the user submits should come from pdflatex/latexmk (or Overleaf). Tell the user
this if only tectonic is available.

## Procedure
1. Run the bundled render script, `"${CLAUDE_SKILL_DIR}/scripts/render.sh" <tex-file>`
   (when installed as a plugin, `${CLAUDE_SKILL_DIR}` resolves to this skill's
   directory; if that variable is unset, fall back to `scripts/render.sh` relative
   to this skill). It:
   - detects `latexmk` (preferred, faithful), else `tectonic` (preview-only,
     see fidelity note), else `pdflatex`/`xelatex`;
   - for tectonic, compiles a shimmed throwaway copy; other engines use the file as-is;
   - compiles in the file's directory and prints the PDF path;
   - **enforces the one-page rule**: parses the TeX log for the page count and
     exits non-zero (code 5) if the resume is more than one page.
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
  [`GUARDRAILS.md`](../../../GUARDRAILS.md).
