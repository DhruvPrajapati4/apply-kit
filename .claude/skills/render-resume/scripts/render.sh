#!/usr/bin/env bash
# Compile a LaTeX resume to PDF and enforce the one-page rule.
# Prefers latexmk (pdflatex), then tectonic, then a raw engine.
#
# The resume is authored for pdfLaTeX. Tectonic runs XeTeX, which (a) lacks the
# pdfTeX primitives \input{glyphtounicode}/\pdfgentounicode and (b) crashes on
# the fontawesome5 package. So when compiling with tectonic we build a shimmed
# throwaway copy (fontawesome5 -> fontawesome v4, ATS glyph lines commented) and
# emit the PDF under the original name. pdflatex/latexmk need no shim.
#
# Usage: render.sh <path-to.tex>
set -euo pipefail

TEX="${1:-}"
if [[ -z "$TEX" || ! -f "$TEX" ]]; then
  echo "usage: render.sh <path-to.tex>" >&2
  exit 2
fi

DIR="$(cd "$(dirname "$TEX")" && pwd)"
BASE="$(basename "$TEX" .tex)"
cd "$DIR"

# MacTeX/TeX Live binaries often aren't on PATH until a new shell. Add the known
# locations so rendering works right after install. The GUI MacTeX uses
# /Library/TeX/texbin; the no-GUI cask installs to /usr/local/texlive/<year>/bin/*.
[[ -d /Library/TeX/texbin ]] && PATH="/Library/TeX/texbin:$PATH"
for d in /usr/local/texlive/*/bin/*/; do [[ -x "$d/latexmk" || -x "$d/pdflatex" ]] && PATH="$d:$PATH"; done

engine=""
if command -v latexmk >/dev/null 2>&1; then engine="latexmk"
elif command -v tectonic >/dev/null 2>&1; then engine="tectonic"
elif command -v pdflatex >/dev/null 2>&1; then engine="pdflatex"
elif command -v xelatex >/dev/null 2>&1; then engine="xelatex"
fi

if [[ -z "$engine" ]]; then
  cat >&2 <<'EOF'
error: no LaTeX engine found (looked for latexmk, tectonic, pdflatex, xelatex).
Install one:
  macOS (matches your latexmk workflow):  brew install --cask mactex-no-gui
  macOS (lightweight, auto-fetches pkgs): brew install tectonic
Or compile the .tex on Overleaf instead.
EOF
  exit 3
fi

echo ">> compiling $BASE.tex with $engine"
LOG=""
case "$engine" in
  latexmk)
    latexmk -pdf -interaction=nonstopmode -halt-on-error "$BASE.tex"
    LOG="$BASE.log" ;;
  tectonic)
    # XeTeX compatibility shim on a throwaway copy; original .tex untouched.
    SHIM="${BASE}.__tec"
    sed -e 's/\\usepackage{fontawesome5}/\\usepackage{fontawesome}/' \
        -e 's/^\\input{glyphtounicode}/%&/' \
        -e 's/^\\pdfgentounicode=1/%&/' \
        "$BASE.tex" > "$SHIM.tex"
    echo ">> (tectonic shim applied: fontawesome5->fontawesome, glyphtounicode disabled)"
    # Tectonic prints many benign font-loading warnings; capture them and only
    # surface output if the compile actually fails (it exits non-zero on error).
    if ! tectonic -X compile "$SHIM.tex" --keep-logs >/dev/null 2>"$SHIM.err"; then
      cat "$SHIM.err" >&2
      exit 1
    fi
    mv -f "$SHIM.pdf" "$BASE.pdf"
    LOG="$SHIM.log"
    ;;
  *)
    "$engine" -interaction=nonstopmode -halt-on-error "$BASE.tex" >/dev/null
    LOG="$BASE.log" ;;
esac

if [[ ! -f "$BASE.pdf" ]]; then
  echo "error: compile finished but $BASE.pdf not found; check $DIR/$LOG" >&2
  exit 4
fi
echo ">> built: $DIR/$BASE.pdf"

# --- One-page guard -------------------------------------------------------
# The TeX log reports "Output written on <file> (N page[s], ...)".
PAGES=""
if [[ -n "$LOG" && -f "$LOG" ]]; then
  PAGES="$(grep -oE 'Output written on [^(]*\(([0-9]+) page' "$LOG" | grep -oE '[0-9]+ page' | grep -oE '[0-9]+' | tail -1 || true)"
fi

if [[ -z "$PAGES" ]]; then
  echo ">> pages: unknown (couldn't parse $LOG) — verify manually that it's one page" >&2
elif [[ "$PAGES" -eq 1 ]]; then
  echo ">> pages: 1  ✓ one-page rule satisfied"
else
  echo "" >&2
  echo "!! ONE-PAGE RULE VIOLATED: resume rendered to $PAGES pages." >&2
  echo "!! Trim/condense content and re-render before using this PDF." >&2
  exit 5
fi
