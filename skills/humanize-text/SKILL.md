---
name: humanize-text
description: Strip the tell-tale signatures of AI-generated prose so writing reads as naturally human. Removes em dashes and en dashes, converts smart quotes and other typographic Unicode to plain ASCII, and dials back robotic AI phrasing and structure. Use this as a finishing pass WHENEVER you generate, write, refine, rephrase, reword, polish, draft, or edit any prose the user will send or publish — emails, messages, docs, posts, cover letters, commit bodies, PR descriptions, blog text — even when the user only asks to "clean it up" or "make it sound natural" without naming AI. Do NOT apply it to code, code comments, config, or verbatim quotes.
---

# humanize-text

AI-written prose has a recognizable fingerprint. The loudest tell is the em dash
(—), which humans rarely type but models emit constantly, followed by smart
quotes and a handful of stock phrases. This skill removes those signatures while
preserving the writer's meaning and voice. Apply it as the **last pass** over any
prose you produce for the user to send or publish.

The goal is text that reads as if a competent person typed it in a normal editor,
not text that has been scrubbed into blandness. Fix the tells; keep the substance.

## 1. Punctuation and Unicode (the mechanical, high-signal fixes)

These are the strongest AI markers. Replace them thoughtfully — choose the
punctuation a human would actually have used, don't just delete.

- **Em dash `—`**: rewrite, don't blank out. Pick by role:
  - parenthetical aside → wrap in commas, or use parentheses
  - a pause before a payoff/explanation → colon
  - two independent clauses joined → split into two sentences, or use a semicolon
  - Example: `We shipped it — finally.` → `We shipped it, finally.`
  - Example: `Three services — auth, billing, search — went down.` → `Three services (auth, billing, search) went down.`
- **En dash `–`**:
  - number/date/page ranges → a hyphen, or the word "to" (`2019–2023` → `2019 to 2023`)
  - used as a dash → treat like an em dash above
- **Smart/curly quotes** `“ ” ‘ ’` → straight `"` and `'`.
- **Ellipsis `…`** → three periods `...`, or cut it (trailing ellipses read as AI hedging).
- **Non-breaking spaces, zero-width chars, and other stray Unicode** → normal ASCII space or delete.
- Leave ordinary hyphens in compound words alone (`well-known`, `real-time`, `p99`).

## 2. Phrasing tells (lighter touch — reduce, don't robotically purge)

Models overuse a stock vocabulary and a few sentence shapes. Trim them where they
appear, but only if the replacement stays natural — don't mangle a fine sentence
just to avoid a word.

- Inflated verbs/nouns: *delve, leverage, utilize, foster, underscore, elevate,
  boast, harness, spearhead, tapestry, realm, landscape, testament, beacon.*
  Prefer plain equivalents (*use* over *utilize*, *show* over *underscore*).
- Hollow intensifiers: *seamless, robust, cutting-edge, game-changing,
  best-in-class, world-class, unlock, supercharge.*
- Formulaic frames: *"It's not just X, it's Y", "In today's fast-paced world",
  "At the end of the day", "When it comes to…"* — cut or rephrase directly.
- Throat-clearing transitions stacked at sentence starts: *Moreover, Furthermore,
  Additionally, In conclusion.* Keep at most where they earn their place.
- Compulsive rule-of-three lists and perfectly parallel bullet phrasing — vary the
  rhythm; real writing is a little uneven.
- Emoji sprinkled into headings or bullets (unless the user's own style uses them).

## 3. What NOT to touch

Correctness matters more than de-AI-ing. Never alter:

- **Code, code blocks, inline code, commands, file paths, URLs, regexes** — a dash
  or quote there is syntax, not style.
- **Verbatim quotations, names, citations, and literal strings** the user must
  keep exact.
- **Technical notation**: ranges/signs where a hyphen is meaningful (`-1`, `x-y`),
  version numbers, IDs.
- The **meaning, claims, or facts** of the text. This is a style pass only.

## Applying it

- When you generate prose in a normal response, apply these fixes inline before
  you present it — the user should just receive clean text.
- When editing a file of prose, make the edits directly.
- For a large plain-prose file, `scripts/humanize.py <file>` does the safe
  mechanical pass (dashes, quotes, ellipses, stray Unicode) and skips fenced code
  blocks; the phrasing work in section 2 still needs your judgment.
- If a change would distort meaning or the user explicitly wants a dash/quote kept,
  leave it and say why.
