#!/usr/bin/env python3
"""Search company applicant tracking systems (ATS) directly for open roles.

Job aggregators are noisy and stale. Company ATS boards are neither: they are the
same data the company's own careers page renders, they are public, and they carry
the full posting text, so we can filter on location, stack, and stated years of
experience instead of guessing from a title.

Two modes:

  probe   Given candidate slugs, find which ATS (if any) each one lives on.
          Slugs frequently do not match the company name, so this is how you
          discover them. Cheap to run against a long guess list.

  search  Given a resolved slug list, pull every posting and filter it.

Standard library only, so it runs anywhere python3 does.

Usage:
  ats_search.py probe  --slugs acme,globex,initech [--json out.json]
  ats_search.py search --companies companies.json \\
                       --location 'berlin|remote' \\
                       --title 'backend|platform|sde|software engineer' \\
                       --exclude 'manager|director|intern|principal' \\
                       --stack 'rust,kubernetes,kafka,postgres' \\
                       --max-min-years 5 \\
                       --markdown leads.md --json leads.json
  ats_search.py --selftest
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import html
import json
import re
import sys
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


def run_probe(slugs: list[str]) -> list[dict]:
    results = []
    with futures.ThreadPoolExecutor(WORKERS) as pool:
        for hits in pool.map(probe_one, slugs):
            results.extend(hits)
    return results


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
    location = re.compile(args.location, re.I) if args.location else None
    title = re.compile(args.title, re.I) if args.title else None
    exclude = re.compile(args.exclude, re.I) if args.exclude else None
    stack = args.stack.split(",") if args.stack else []

    skip = frozenset(
        p.strip().lower() for p in (args.skip_providers or "").split(",") if p.strip()
    )
    everything = []
    with futures.ThreadPoolExecutor(WORKERS) as pool:
        for jobs in pool.map(lambda e: fetch_company(e, skip), companies):
            everything.extend(jobs)

    leads = []
    for j in everything:
        j["min_years"] = min_years(j.get("description", ""))
        if not matches(j, location, title, exclude, args.max_min_years):
            continue
        j["stack_hits"] = stack_hits(j.get("description", ""), j.get("title", ""), stack)
        j["score"] = len(j["stack_hits"])
        leads.append(j)

    leads.sort(key=lambda j: (-j["score"], j["company"], j["title"]))
    print(
        f"Scanned {len(everything)} postings across {len(companies)} companies, "
        f"{len(leads)} matched.",
        file=sys.stderr,
    )
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
        lines.append(
            f"| {j['company']} | {title} | {loc} | {yrs} | {hits} | [apply]({j['url']}) |"
        )
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

    print("selftest: all checks passed")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true", help="run offline checks and exit")
    sub = p.add_subparsers(dest="mode")

    pp = sub.add_parser("probe", help="discover which ATS a slug lives on")
    pp.add_argument("--slugs", required=True, help="comma-separated slugs, or a file path")
    pp.add_argument("--json", help="write results here")

    sp = sub.add_parser("search", help="pull and filter postings")
    sp.add_argument("--companies", required=True, help="path to a companies JSON file")
    sp.add_argument("--location", help="regex matched against the posting location")
    sp.add_argument("--title", help="regex a title must match")
    sp.add_argument("--exclude", help="regex a title must NOT match")
    sp.add_argument("--stack", help="comma-separated tech terms to score overlap on")
    sp.add_argument("--max-min-years", type=int,
                    help="drop postings whose stated floor exceeds this")
    sp.add_argument("--skip-providers",
                    help="comma-separated providers to ignore, e.g. 'workday' for "
                         "boards that need an account and cannot be auto-filled")
    sp.add_argument("--markdown", help="write a markdown table here")
    sp.add_argument("--json", help="write raw results here")

    args = p.parse_args()

    if args.selftest:
        selftest()
        return 0

    if args.mode == "probe":
        raw = args.slugs
        try:
            with open(raw) as fh:
                slugs = [ln.strip() for ln in fh if ln.strip()]
        except OSError:
            slugs = [s.strip() for s in raw.split(",") if s.strip()]
        hits = run_probe(slugs)
        for h in hits:
            print(f"{h['provider']:11} {h['slug']:24} {h['job_count']} jobs")
        if not hits:
            print("no ATS boards found for those slugs", file=sys.stderr)
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
