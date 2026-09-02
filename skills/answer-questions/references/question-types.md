# Application question archetypes

How to handle each kind of question an application form asks. Sort every question
into one of these before drafting.

Contents:
1. Why this company
2. Why this role, why you
3. Tell us about a project
4. What are you looking for next
5. Anything else we should know
6. The cover letter box
7. Behavioral questions
8. Questions to hand back

---

## 1. Why this company

The most-failed question on any form, because most answers are a paraphrase of
the company's own homepage. A reviewer has read their own tagline before.

**Shape** (roughly 120 to 180 words):
- One sentence naming something concrete and non-obvious about what they build or
  the constraint they operate under.
- Two or three sentences connecting that to work the user has actually done, with
  numbers.
- One sentence with a genuine point of view, ideally reframing the user's position
  relative to the company.

**What makes it work:** the reframe. An engineer who has been a heavy user of the
category can say so. An engineer whose hard-won constraint matches the company's
hard problem can say that. Something like "I have only ever been on the paying
side of observability, and I would like to be on the building side" lands because
it is true, specific, and could not be pasted into another application.

**Test:** swap in a competitor's name. If the answer still reads fine, it is not
finished.

---

## 2. Why this role, why you

This is where breadth belongs. Do not build it around one project.

**Shape** (roughly 150 to 200 words): pick three or four achievements from
*different* systems that map onto the posting's actual requirements, each with a
number, compressed into a dense paragraph rather than a bulleted list. Then one
sentence on the gap, if there is a real one.

Selection is the work. A posting about high-throughput ingestion should see the
throughput, latency, and pipeline work, and should not see the CRUD dashboard,
even if the dashboard is the user's favourite. What you leave out is the clearest
evidence that the posting was read.

If the fit report flagged an under-level or off-stack gap, name it here in one
sentence and make the case rather than hoping nobody checks: "the posting asks
for 5 to 8 years and I have 3.5, so here is why I am writing anyway."

---

## 3. Tell us about a project you are proud of

Pick from the resume, and pick the one that maps to the role rather than the one
the user likes most. Ask the user first if they rate it as strong; a project they
privately consider thin will collapse under follow-up questions.

**Shape** (roughly 150 to 250 words):
- What the system had to do, and the constraint that made it hard. The constraint
  is the interesting part and the part most answers omit.
- The decision taken and what it traded away. An engineer who can name a tradeoff
  reads as more senior than one who lists technologies.
- The measured outcome.
- Optional and strong: what they would do differently.

Avoid a technology roll call. "Go, Kafka, Redis, Postgres, Kubernetes" says
nothing; "we accepted a stale read of up to 30 seconds so the hot path never
touched the database" says a great deal.

If the honest description of a project is modest, keep it modest. "A small
internal tool rather than a research result, but it is why this problem interests
me" is a strong sentence. Inflation is the failure mode here.

---

## 4. What are you looking for next

Short, 60 to 100 words. The useful version connects what the user does now to
what this role would change, and it is allowed to be direct about a gap: wanting
to do full time what they have only done as a by-product, wanting scale they
cannot get where they are, wanting to move from consuming a category to building
it.

Avoid growth-and-learning boilerplate. It is true of everyone and therefore
tells the reader nothing.

---

## 5. Anything else we should know

Usually optional, and usually best used for one of:
- A gap worth pre-empting on the user's terms rather than a screener's (location,
  level, notice period framing, an unusual career step).
- A relevant thing the resume format could not hold.
- Nothing at all. Leaving it blank is better than padding, and the skill should
  say so rather than manufacturing content.

---

## 6. The cover letter box

Treat as questions 1 and 2 merged, 200 to 300 words: a specific opening, the
depth paragraph, the point-of-view line, a one-line close. No "Dear Hiring
Manager, I am writing to apply for the position of", which wastes the first line
the reader looks at.

---

## 7. Behavioral questions

"A time you disagreed with a teammate." "A time you failed." "How you handled
feedback."

**The resume does not contain these events, so they cannot be drafted from it.**
Ask the user for what actually happened, then help structure it: situation
briefly, the action they took, the outcome, and what they took from it. Keep
their details and their voice.

Authoring the event is fabrication, even though it feels like a writing task
rather than a factual one. It is the same rule as inventing a metric.

---

## 8. Questions to hand back

Never answered, always returned to the user with a one-line reason:

| Question | Why it is theirs |
|---|---|
| Gender, race, ethnicity, disability, veteran status | Personal disclosures with legal weight. Never inferred. Filled only from a value the user recorded in `resume/profile.json`, otherwise left blank. |
| Salary expectation, current compensation | A negotiating position, not a fact. In several jurisdictions the employer may not ask at all. |
| Notice period, earliest start date | Only the user knows, and a wrong answer is binding. |
| Work authorization, visa status, sponsorship needed | A legal fact about the user. A guess can invalidate the application. |
| Willing to relocate, preferred location | A life decision. |
| Referral source, how did you hear about us | The user knows; the model would be guessing. |

Group these at the end of `answers.md` under a clear heading so the user can work
through them in one pass rather than discovering them one at a time in the form.
