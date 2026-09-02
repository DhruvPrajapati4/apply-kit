#!/usr/bin/env python3
"""Search company applicant tracking systems (ATS) directly for open roles.

Job aggregators are noisy and stale. Company ATS boards are neither: they are the
same data the company's own careers page renders, they are public, and they carry
the full posting text, so we can filter on location, stack, and stated years of
experience instead of guessing from a title.

Three modes:

  discover  Search every Workable-hosted board at once, with no company list at
            all. This is how roles at companies nobody curated get found.

  probe     Given company names or candidate slugs, find which ATS (if any)
            each one lives on, and optionally append the verified ones to a
            companies file. Slugs frequently do not match the company name, so
            this is how you resolve them. Cheap to run against a long list.

  search    Given a resolved slug list, pull every posting and filter it.

The companies file is a cache of resolved slugs, not a fixed universe: probe
--append grows it, and discover finds work outside it entirely.

Standard library only, so it runs anywhere python3 does.

Usage:
  ats_search.py discover --query 'backend engineer' --location india \\
                       --title 'backend|platform' --stack 'go,kubernetes' \\
                       --companies companies.json \\
                       --markdown leads.md --json leads.json
  ats_search.py probe  --names 'Acme Labs, Globex' --stage series-b \\
                       --append companies.json
  ats_search.py probe  --slugs acme,globex,initech [--json out.json]
  ats_search.py search --companies companies.json \\
                       --location 'berlin|remote' \\
                       --title 'backend|platform|sde|software engineer' \\
                       --exclude 'manager|director|intern|principal' \\
                       --stack 'rust,kubernetes,kafka,postgres' \\
                       --max-min-years 5 --stage 'series-[abc]' \\
                       --markdown leads.md --json leads.json
  ats_search.py --selftest
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime
import html
import json
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; apply-kit/0.1; +https://github.com/DhruvPrajapati4/apply-kit)"
TIMEOUT = 30  # large boards return several MB with content=true
WORKERS = 12


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _get(url: str, data: bytes | None = None) -> object:
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _clean(text: str | None) -> str:
    """Strip HTML to plain text. Postings arrive as HTML on most providers."""
    if not text:
        return ""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Providers
#
# Each returns a list of normalized postings. Adding a provider means adding one
# function here and one entry in PROVIDERS; nothing else changes.
# --------------------------------------------------------------------------

def _greenhouse(slug: str) -> list[dict]:
    d = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    return [
        {
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description": _clean(j.get("content")),
            "updated": j.get("updated_at", ""),
        }
        for j in d.get("jobs", [])
    ]


def _lever(slug: str) -> list[dict]:
    d = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in d:
        body = j.get("descriptionPlain", "") + " " + " ".join(
            _clean(s.get("text", "")) + " " + _clean(s.get("content", ""))
            for s in j.get("lists", [])
        )
        out.append({
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location") or "",
            "url": j.get("hostedUrl", ""),
            "description": _clean(body),
            "updated": str(j.get("createdAt", "")),
        })
    return out


def _ashby(slug: str) -> list[dict]:
    d = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    return [
        {
            "title": j.get("title", ""),
            "location": j.get("location") or "",
            "url": j.get("jobUrl", ""),
            "description": _clean(j.get("descriptionPlain") or j.get("descriptionHtml")),
            "updated": j.get("publishedAt", ""),
        }
        for j in d.get("jobs", [])
    ]


def _workable(slug: str) -> list[dict]:
    d = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    return [
        {
            "title": j.get("title", ""),
            "location": j.get("city") or (j.get("location") or {}).get("city", ""),
            "url": j.get("url") or j.get("shortlink", ""),
            "description": _clean(j.get("description")),
            "updated": j.get("published_on", ""),
        }
        for j in d.get("jobs", [])
    ]


def workable_search(query: str, location: str, pages: int = 5) -> list[dict]:
    """Search across every Workable-hosted board at once.

    The provider functions above all need a slug you already know, which is why
    a curated company list existed in the first place. This endpoint backs
    Workable's own public job-seeker site, so it spans their whole customer base
    and needs no list: it is the one cross-tenant search any of the five
    providers expose. Greenhouse, Lever and Ashby publish per-board endpoints
    only, and none of them publish an index of boards, so a Workable-only sweep
    is the honest ceiling here. Report it as such.
    """
    out, token = [], None
    for _ in range(max(1, pages)):
        params = {"query": query or "", "location": location or ""}
        if token:
            params["pageToken"] = token
        d = _get("https://jobs.workable.com/api/v1/jobs?" + urllib.parse.urlencode(params))
        jobs = d.get("jobs", [])
        if not jobs:
            break
        for j in jobs:
            co = j.get("company") or {}
            loc = j.get("location") or {}
            out.append({
                "title": j.get("title", ""),
                "location": ", ".join(j.get("locations") or [])
                            or ", ".join(filter(None, [loc.get("city"), loc.get("countryName")])),
                "url": j.get("url", ""),
                "description": _clean(j.get("description")) + " "
                               + _clean(j.get("requirementsSection")),
                "updated": j.get("updated", ""),
                "company": co.get("title", ""),
                "website": co.get("website", ""),
                "provider": "workable",
            })
        token = d.get("nextPageToken")
        if not token:
            break
    return out


def _recruitee(slug: str) -> list[dict]:
    d = _get(f"https://{slug}.recruitee.com/api/offers/")
    return [
        {
            "title": j.get("title", ""),
            "location": j.get("city") or "",
            "url": j.get("careers_url", ""),
            "description": _clean(j.get("description")),
            "updated": j.get("published_at", ""),
        }
        for j in d.get("offers", [])
    ]


def _workday(cfg: dict) -> list[dict]:
    """Workday needs a host, tenant and board rather than a single slug.

    Find them in the careers-page link, which looks like
    https://<host>/<board> where host is <tenant>.wdN.myworkdayjobs.com
    """
    host, tenant, board = cfg["host"], cfg["tenant"], cfg["board"]
    api = f"https://{host}/wday/cxs/{tenant}/{board}/jobs"
    out, offset = [], 0
    while offset < 500:  # hard stop; no board we target is larger
        payload = json.dumps(
            {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}
        ).encode()
        d = _get(api, data=payload)
        postings = d.get("jobPostings", [])
        if not postings:
            break
        for j in postings:
            out.append({
                "title": j.get("title", ""),
                "location": j.get("locationsText", ""),
                "url": f"https://{host}/{board}{j.get('externalPath', '')}",
                # The list endpoint omits the body. Fetching each posting costs a
                # request per job, so we filter Workday on title and location only.
                "description": "",
                "updated": j.get("postedOn", ""),
            })
        offset += 20
        if offset >= int(d.get("total", 0)):
            break
    return out


PROVIDERS = {
    "greenhouse": _greenhouse,
    "lever": _lever,
    "ashby": _ashby,
    "workable": _workable,
    "recruitee": _recruitee,
    "workday": _workday,
}


# --------------------------------------------------------------------------
# Parsing and filtering
# --------------------------------------------------------------------------

YEARS_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:[-–—]|to)?\s*(\d{1,2})?\s*\+?\s*year",
    re.I,
)


def min_years(description: str) -> int | None:
    """Lowest years-of-experience figure stated anywhere in the posting.

    Heuristic, and deliberately so. A posting mentions years in several places
    ("5+ years backend", "2 years with Kubernetes"), and there is no reliable
    marker for which one is the bar. The lowest number is the most permissive
    reading, which is the right bias for a candidate deciding whether to apply:
    it errs toward showing a role rather than hiding it. Always read the posting
    before trusting this number.
    """
    values = []
    for lo, hi in YEARS_RE.findall(description or ""):
        for v in (lo, hi):
            if v and 0 < int(v) <= 20:
                values.append(int(v))
    return min(values) if values else None


def stack_hits(description: str, title: str, stack: list[str]) -> list[str]:
    blob = f"{title} {description}".lower()
    hits = []
    for term in stack:
        t = term.strip().lower()
        if not t:
            continue
        # Word-boundary match so "go" does not fire on "category" or "ongoing".
        if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", blob):
            hits.append(term.strip())
    return hits


def matches(posting: dict, location: re.Pattern | None, title: re.Pattern | None,
            exclude: re.Pattern | None, max_min_years: int | None) -> bool:
    if location and not location.search(posting.get("location", "")):
        return False
    if title and not title.search(posting.get("title", "")):
        return False
    if exclude and exclude.search(posting.get("title", "")):
        return False
    if max_min_years is not None:
        my = posting.get("min_years")
        # Keep postings that state no requirement; absence is not a rejection.
        if my is not None and my > max_min_years:
            return False
    return True


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

STRIPPABLE = {
    "inc", "llc", "ltd", "limited", "corp", "co", "labs", "lab", "technologies",
    "technology", "tech", "software", "systems", "ai", "io", "hq", "the", "group",
}


def slug_candidates(name: str) -> list[str]:
    """Guess the board slugs a company name might resolve to.

    Nothing maps a name to an ATS slug, so the only route is to generate the
    plausible forms and let probe say which ones exist. Cheap: a wrong guess is
    one 404.
    """
    words = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if w]
    if not words:
        return []
    cands = ["".join(words), "-".join(words), "".join(words) + "inc"]
    if len(words) > 1 and words[-1] in STRIPPABLE:
        core = words[:-1]
        cands += ["".join(core), "-".join(core)]
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def filter_and_score(postings: list[dict], args: argparse.Namespace) -> list[dict]:
    """Apply the title/location/years filters and score stack overlap."""
    location = re.compile(args.location, re.I) if args.location else None
    title = re.compile(args.title, re.I) if args.title else None
    exclude = re.compile(args.exclude, re.I) if args.exclude else None
    stack = args.stack.split(",") if args.stack else []

    leads = []
    for j in postings:
        j["min_years"] = min_years(j.get("description", ""))
        if not matches(j, location, title, exclude, args.max_min_years):
            continue
        j["stack_hits"] = stack_hits(j.get("description", ""), j.get("title", ""), stack)
        j["score"] = len(j["stack_hits"])
        leads.append(j)
    leads.sort(key=lambda j: (-j["score"], j["company"], j["title"]))
    return leads


def probe_one(slug: str) -> list[dict]:
    found = []
    for name, fn in PROVIDERS.items():
        if name == "workday":
            continue  # needs host/tenant/board, cannot be guessed from a slug
        try:
            jobs = fn(slug)
        except Exception:
            continue
        if jobs:
            found.append({"slug": slug, "provider": name, "job_count": len(jobs)})
    return found


def run_probe(slugs: list[str], names: list[str] | None = None) -> list[dict]:
    """Resolve slugs to boards. With names, guess each name's slugs first."""
    pairs = [("", s) for s in slugs]
    for name in names or []:
        pairs += [(name, s) for s in slug_candidates(name)]

    results = []
    with futures.ThreadPoolExecutor(WORKERS) as pool:
        for (name, _slug), hits in zip(pairs, pool.map(lambda p: probe_one(p[1]), pairs)):
            for h in hits:
                results.append({**h, "name": name or h["slug"]})
    return results


def append_companies(path: str, hits: list[dict], stage: str | None) -> tuple[int, int]:
    """Merge verified boards into the companies file so the list grows itself.

    Without this the file only grows when someone remembers to hand-edit it,
    which is how a list of verified slugs goes stale.
    """
    with open(path) as fh:
        entries = json.load(fh)
    if isinstance(entries, dict):
        entries = entries.get("companies", [])

    by_name = {(e.get("name") or "").lower(): e for e in entries}
    today = datetime.date.today().isoformat()
    added = changed = 0

    # One name can match several slugs; keep the board carrying the most jobs.
    best: dict[tuple[str, str], dict] = {}
    for h in hits:
        key = (h["name"].lower(), h["provider"])
        if h["job_count"] > best.get(key, {}).get("job_count", -1):
            best[key] = h

    for h in best.values():
        entry = by_name.get(h["name"].lower())
        if entry is None:
            entry = {"name": h["name"]}
            entries.append(entry)
            by_name[h["name"].lower()] = entry
            added += 1
        elif entry.get(h["provider"]) != h["slug"]:
            changed += 1
        entry[h["provider"]] = h["slug"]
        if stage:
            entry["stage"] = stage
        entry["verified"] = today

    entries.sort(key=lambda e: (e.get("name") or "").lower())
    body = ",\n".join("  " + _entry_line(e) for e in entries)
    with open(path, "w") as fh:
        fh.write("[\n" + body + "\n]\n")
    return added, changed


def _entry_line(value: object) -> str:
    """One entry per line, in the companies file's existing shape.

    json.dump would reflow all 85 lines, so a two-company merge would read as a
    whole-file rewrite in the diff. Matching the hand-written style keeps the
    diff to the lines that actually changed.
    """
    if isinstance(value, dict):
        inner = ", ".join(f"{json.dumps(k)}: {_entry_line(v)}" for k, v in value.items())
        return "{ " + inner + " }"
    return json.dumps(value)


def fetch_company(entry: dict, skip: frozenset[str] = frozenset()) -> list[dict]:
    name = entry.get("name") or ""
    out = []
    for provider, fn in PROVIDERS.items():
        cfg = entry.get(provider)
        if not cfg or provider in skip:
            continue
        try:
            jobs = fn(cfg)
        except Exception as exc:  # a dead slug must not kill the whole run
            print(f"  ! {name or cfg} via {provider}: {exc}", file=sys.stderr)
            continue
        for j in jobs:
            j["company"] = name or (cfg if isinstance(cfg, str) else provider)
            j["provider"] = provider
            out.append(j)
    return out


def run_search(companies: list[dict], args: argparse.Namespace) -> list[dict]:
    if getattr(args, "stage", None):
        stage = re.compile(args.stage, re.I)
        before = len(companies)
        companies = [c for c in companies if stage.search(c.get("stage", ""))]
        print(
            f"Stage filter '{args.stage}' kept {len(companies)}/{before} companies. "
            "Entries with no stage recorded are dropped, so an untagged file "
            "will scan nothing.",
            file=sys.stderr,
        )

    skip = frozenset(
        p.strip().lower() for p in (args.skip_providers or "").split(",") if p.strip()
    )
    everything = []
    with futures.ThreadPoolExecutor(WORKERS) as pool:
        for jobs in pool.map(lambda e: fetch_company(e, skip), companies):
            everything.extend(jobs)

    leads = filter_and_score(everything, args)
    print(
        f"Scanned {len(everything)} postings across {len(companies)} companies, "
        f"{len(leads)} matched.",
        file=sys.stderr,
    )
    return leads


def run_discover(args: argparse.Namespace) -> list[dict]:
    """List-free search, then flag which companies the curated file is missing."""
    postings = workable_search(args.query, args.location, args.pages)
    # The API already filtered on --location; a regex post-filter is opt-in.
    args.location = args.location_regex
    leads = filter_and_score(postings, args)

    known = set()
    if args.companies:
        with open(args.companies) as fh:
            entries = json.load(fh)
        if isinstance(entries, dict):
            entries = entries.get("companies", [])
        known = {(e.get("name") or "").lower() for e in entries}
    for j in leads:
        j["new_company"] = j["company"].lower() not in known if known else None

    fresh = sorted({j["company"] for j in leads if j.get("new_company")})
    tail = (f", {len(fresh)} companies not in the curated file" if known
            else " (pass --companies to see which companies are new)")
    print(
        f"Discovered {len(postings)} postings across "
        f"{len({p['company'] for p in postings})} Workable companies, "
        f"{len(leads)} matched{tail}.",
        file=sys.stderr,
    )
    if fresh:
        print("New companies: " + ", ".join(fresh), file=sys.stderr)
    return leads


def to_markdown(leads: list[dict]) -> str:
    lines = [
        "# Job leads",
        "",
        f"{len(leads)} matching postings, sorted by stack overlap.",
        "",
        "`Min yrs` is the lowest experience figure stated anywhere in the posting.",
        "It is a heuristic, so confirm it in the posting before ruling a role out.",
        "",
        "| Company | Role | Location | Min yrs | Stack match | Link |",
        "|---|---|---|---|---|---|",
    ]
    for j in leads:
        hits = ", ".join(j["stack_hits"]) or "-"
        yrs = j["min_years"] if j["min_years"] is not None else "-"
        title = j["title"].replace("|", "/")
        loc = (j["location"] or "-").replace("|", "/")
        company = j["company"] + (" (new)" if j.get("new_company") else "")
        lines.append(
            f"| {company} | {title} | {loc} | {yrs} | {hits} | [apply]({j['url']}) |"
        )
    if any(j.get("new_company") for j in leads):
        lines += [
            "",
            "`(new)` marks a company absent from the curated companies file. Resolve",
            "and keep it with: `probe --names '<company>' --append <companies.json>`.",
        ]
    if any(j["provider"] == "workday" for j in leads):
        lines += [
            "",
            "Workday postings are filtered on title and location only, because that",
            "board's list endpoint omits the body text.",
        ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Self-check
# --------------------------------------------------------------------------

def selftest() -> None:
    """Offline check of the parsing and filtering logic."""
    assert min_years("We want 5+ years of backend experience") == 5
    assert min_years("3-6 years building distributed systems") == 3
    assert min_years("6–8 years, plus 2 years of Kubernetes") == 2
    assert min_years("No experience requirement stated") is None
    assert min_years("A 99 years lease") is None, "implausible figures are ignored"

    assert stack_hits("We write Go and Kafka", "Backend Engineer", ["go", "kafka"]) == ["go", "kafka"]
    assert stack_hits("An ongoing category of work", "Engineer", ["go"]) == [], \
        "substring false positives must not match"

    loc = re.compile("metropolis|megacity", re.I)
    ttl = re.compile("backend", re.I)
    exc = re.compile("manager", re.I)
    keep = {"title": "Backend Engineer", "location": "Metropolis, Freedonia", "min_years": 3}
    drop_loc = {"title": "Backend Engineer", "location": "Berlin", "min_years": 3}
    drop_ttl = {"title": "Frontend Engineer", "location": "Metropolis", "min_years": 3}
    drop_exc = {"title": "Backend Engineering Manager", "location": "Metropolis", "min_years": 3}
    drop_yrs = {"title": "Backend Engineer", "location": "Metropolis", "min_years": 9}
    unknown_yrs = {"title": "Backend Engineer", "location": "Metropolis", "min_years": None}

    assert matches(keep, loc, ttl, exc, 5)
    assert not matches(drop_loc, loc, ttl, exc, 5)
    assert not matches(drop_ttl, loc, ttl, exc, 5)
    assert not matches(drop_exc, loc, ttl, exc, 5)
    assert not matches(drop_yrs, loc, ttl, exc, 5)
    assert matches(unknown_yrs, loc, ttl, exc, 5), "unstated years is not a rejection"

    assert _clean("<p>Hello &amp; <b>bye</b></p>") == "Hello & bye"

    assert slug_candidates("Acme Labs") == ["acmelabs", "acme-labs", "acmelabsinc", "acme"], \
        "a strippable trailing word yields the bare-name variants too"
    assert slug_candidates("Zeta") == ["zeta", "zetainc"]
    assert slug_candidates("Observe.ai") == ["observeai", "observe-ai", "observeaiinc", "observe"]
    assert slug_candidates("  ") == []

    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "companies.json")
        nested = ('  { "name": "Globex", "workday": { "host": "h", "tenant": "t", '
                  '"board": "External" } }')
        with open(path, "w") as fh:
            fh.write('[\n  { "name": "Zeta", "lever": "zeta" },\n' + nested + "\n]\n")
        hits = [
            {"name": "Acme", "provider": "greenhouse", "slug": "acmeinc", "job_count": 9},
            {"name": "Acme", "provider": "greenhouse", "slug": "acme", "job_count": 2},
            {"name": "Zeta", "provider": "lever", "slug": "zeta", "job_count": 4},
        ]
        added, changed = append_companies(path, hits, "series-b")
        with open(path) as fh:
            text = fh.read()
        merged = json.loads(text)
        assert (added, changed) == (1, 0), (added, changed)
        by_name = {e["name"]: e for e in merged}
        assert by_name["Acme"]["greenhouse"] == "acmeinc", "the busiest board wins"
        assert by_name["Acme"]["stage"] == "series-b"
        assert by_name["Zeta"]["lever"] == "zeta", "an existing entry is not clobbered"
        assert [e["name"] for e in merged] == ["Acme", "Globex", "Zeta"], "file stays sorted"
        assert "verified" in by_name["Acme"] and "verified" not in by_name["Globex"], \
            "only touched entries are stamped"
        assert nested + "," in text, "untouched lines keep their exact formatting"

    print("selftest: all checks passed")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true", help="run offline checks and exit")
    sub = p.add_subparsers(dest="mode")

    dp = sub.add_parser("discover", help="search all Workable boards, no company list")
    dp.add_argument("--query", default="", help="free-text search, e.g. 'backend engineer'")
    dp.add_argument("--location", default="", help="plain location for the API, e.g. 'india'")
    dp.add_argument("--location-regex", help="optional regex re-filter of the results")
    dp.add_argument("--pages", type=int, default=5, help="pages of 20 to pull (default 5)")
    dp.add_argument("--companies", help="companies file to diff against, to flag new ones")
    dp.add_argument("--title", help="regex a title must match")
    dp.add_argument("--exclude", help="regex a title must NOT match")
    dp.add_argument("--stack", help="comma-separated tech terms to score overlap on")
    dp.add_argument("--max-min-years", type=int,
                    help="drop postings whose stated floor exceeds this")
    dp.add_argument("--markdown", help="write a markdown table here")
    dp.add_argument("--json", help="write raw results here")

    pp = sub.add_parser("probe", help="resolve company names or slugs to ATS boards")
    pp.add_argument("--slugs", help="comma-separated slugs, or a file path")
    pp.add_argument("--names", help="comma-separated company names; slugs are guessed")
    pp.add_argument("--append", metavar="COMPANIES_JSON",
                    help="merge verified boards into this companies file")
    pp.add_argument("--stage", help="funding stage to record on appended entries, "
                                    "e.g. 'series-b'. Not available from any ATS, so "
                                    "it is whatever you supply.")
    pp.add_argument("--json", help="write results here")

    sp = sub.add_parser("search", help="pull and filter postings")
    sp.add_argument("--companies", required=True, help="path to a companies JSON file")
    sp.add_argument("--location", help="regex matched against the posting location")
    sp.add_argument("--title", help="regex a title must match")
    sp.add_argument("--exclude", help="regex a title must NOT match")
    sp.add_argument("--stack", help="comma-separated tech terms to score overlap on")
    sp.add_argument("--max-min-years", type=int,
                    help="drop postings whose stated floor exceeds this")
    sp.add_argument("--stage", help="regex matched against each company's recorded "
                                    "stage, e.g. 'series-[abc]'. Untagged entries "
                                    "are dropped.")
    sp.add_argument("--skip-providers",
                    help="comma-separated providers to ignore, e.g. 'workday' for "
                         "boards that need an account and cannot be auto-filled")
    sp.add_argument("--markdown", help="write a markdown table here")
    sp.add_argument("--json", help="write raw results here")

    args = p.parse_args()

    if args.selftest:
        selftest()
        return 0

    if args.mode == "discover":
        leads = run_discover(args)
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(leads, fh, indent=2)
        md = to_markdown(leads)
        if args.markdown:
            with open(args.markdown, "w") as fh:
                fh.write(md)
            print(f"wrote {args.markdown}", file=sys.stderr)
        else:
            print(md)
        return 0

    if args.mode == "probe":
        if not args.slugs and not args.names:
            print("probe needs --slugs or --names", file=sys.stderr)
            return 1
        slugs = []
        if args.slugs:
            try:
                with open(args.slugs) as fh:
                    slugs = [ln.strip() for ln in fh if ln.strip()]
            except OSError:
                slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
        names = [n.strip() for n in (args.names or "").split(",") if n.strip()]

        hits = run_probe(slugs, names)
        for h in hits:
            print(f"{h['provider']:11} {h['name']:28} {h['slug']:24} {h['job_count']} jobs")
        for name in names:
            found = {h["slug"] for h in hits if h["name"] == name}
            if len(found) > 1:
                print(
                    f"! {name} matched several slugs ({', '.join(sorted(found))}). "
                    "Open the boards before trusting one: a slug can belong to a "
                    "different company of the same name.",
                    file=sys.stderr,
                )
        if not hits:
            print("no ATS boards found", file=sys.stderr)
        if args.append and hits:
            added, changed = append_companies(args.append, hits, args.stage)
            print(f"{args.append}: {added} added, {changed} updated", file=sys.stderr)
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(hits, fh, indent=2)
        return 0

    if args.mode == "search":
        with open(args.companies) as fh:
            companies = json.load(fh)
        if isinstance(companies, dict):  # allow {"companies": [...]}
            companies = companies.get("companies", [])
        leads = run_search(companies, args)
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(leads, fh, indent=2)
        md = to_markdown(leads)
        if args.markdown:
            with open(args.markdown, "w") as fh:
                fh.write(md)
            print(f"wrote {args.markdown}", file=sys.stderr)
        else:
            print(md)
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
