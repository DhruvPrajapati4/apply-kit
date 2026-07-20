---
name: extract-jd
description: Fetch and normalize a job posting into a structured requirements brief (role, seniority, must-haves, ATS keywords). Use whenever the user shares a job URL or pastes/links a job description and wants it analyzed, summarized, or broken down — including loose asks like "what does this job want" or dropping a link with no further instruction — and as the first step before a fit check or resume tailoring. Handles URL fetching with a clean fallback to pasted text when a site (LinkedIn, Workday, Greenhouse, Lever, Ashby) blocks scraping.
---

# extract-jd

Turn a job posting (URL or pasted text) into a structured brief that downstream
skills (`resume-fit-report`, `tailor-resume`) can consume.

## Input
- A job URL, **or**
- Pasted job-description text, **or**
- A path to a file containing the JD.

## Procedure

1. **If given a URL**, fetch it with `WebFetch`, asking it to return the full job
   description, role title, company, location, and required/preferred
   qualifications verbatim.
   - Job boards (LinkedIn, Workday, Greenhouse, Lever, Ashby) frequently block
     bots or render the JD only via JavaScript. If the fetch returns a login
     wall, a cookie/consent page, near-empty content, or obvious boilerplate
     instead of a real JD, **do not guess** — stop and ask the user to paste the
     JD text. Say plainly that the site blocked automated fetching.
2. **Clean** the content: strip nav, cookie banners, "similar jobs", benefits
   boilerplate, and legal EEO text. Keep role, responsibilities, and
   qualifications.
3. **Extract** into the brief below. Pull skills/keywords **verbatim** from the
   posting (exact casing/phrasing) — these drive ATS keyword matching later.
   Do not infer requirements the posting doesn't state.

## Output

Write `jd-brief.md` to the session scratchpad directory:

```markdown
# JD Brief: <Role> @ <Company>

- **Company:** ...
- **Role / title:** ...
- **Seniority:** intern | junior | mid | senior | staff | ... (as stated or inferred; mark which)
- **Location / remote:** ...
- **Domain:** (fintech, infra, ML, ...)

## Must-have requirements
- ... (only what the posting marks as required)

## Nice-to-have
- ...

## Key responsibilities
- ...

## ATS keywords (verbatim from posting)
`Go`, `Kubernetes`, `distributed systems`, ...

## Notes
- Anything ambiguous, or requirements stated only implicitly.
```

Report the brief path and a 2–3 line summary. If this was invoked as part of
`apply-to-job`, return control to the orchestrator; otherwise ask whether to run
`resume-fit-report` next.
