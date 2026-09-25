"""Orchestration: scan all sources -> apply the 7 stages to every job -> update the cumulative list."""
import glob
import json
import logging
import os
import re
from collections import Counter

from . import config as C
from . import dates, rules
from .location import classify, title_says_abroad, ISRAEL_RE
from .models import Job
from .sources import ScanContext, linkedin, israeli_boards, ats, generic, discovery
from .textutil import canonical_url, norm

log = logging.getLogger("agent")
STATE_FILE = os.path.join(C.DATA_DIR, "state.json")
URL_RE = re.compile(r"https?://[^\s<>\"']+")


# ----------------------------------------------------------------------------- user links (section 2.1 #6)
def read_user_links():
    links = []
    for path in sorted(glob.glob(os.path.join(C.USER_SOURCES_DIR, "*.txt"))):
        with open(path, encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for m in URL_RE.findall(line):
                    links.append(m.rstrip(".,);]"))
                if not URL_RE.search(line) and re.match(r"^[\w.-]+\.[a-z]{2,}(/\S*)?$", line, re.I):
                    links.append("https://" + line)
    seen, out = set(), []
    for u in links:
        k = canonical_url(u)
        if k not in seen:
            seen.add(k)
            out.append(u)
    return out


# ----------------------------------------------------------------------------- scanning
def run_sources(ctx, only=None, today=""):
    def want(name):
        return not only or name in only

    steps = []
    if want("user"):
        steps.append(("user links", lambda: [generic.crawl(ctx, u, method="קישור מקובץ המשתמש")
                                             for u in read_user_links()]))
    if want("linkedin"):
        steps.append(("LinkedIn", lambda: linkedin.scan(ctx)))
    if want("drushim"):
        steps.append(("Drushim", lambda: israeli_boards.scan_drushim(ctx)))
    if want("jobmaster"):
        steps.append(("JobMaster", lambda: israeli_boards.scan_jobmaster(ctx)))
    if want("alljobs"):
        steps.append(("AllJobs", lambda: israeli_boards.scan_alljobs(ctx)))
    if want("indeed"):
        steps.append(("Indeed", lambda: israeli_boards.scan_indeed(ctx)))
    if want("ats"):
        def scan_known_boards():
            boards = [(k, s, C.SEED_COMPANY_NAMES.get(s, "")) for k, s in C.SEED_ATS_BOARDS]
            boards += [(b["kind"], b["slug"], b.get("company", "")) for b in discovery.load_discovered()]
            done = set()
            for kind, slug, company in boards:
                if (kind, slug.lower()) in done:
                    continue
                done.add((kind, slug.lower()))
                if kind == "comeet":
                    ats.scan_comeet(ctx, slug, "page", company)
                elif kind == "comeet_api":
                    ats.scan_comeet(ctx, slug, "api", company)
                elif kind == "workday":
                    ats.scan_workday(ctx, slug, company)
                else:
                    ats.scan_board(ctx, kind, slug, company)
        steps.append(("ATS boards", scan_known_boards))
    if want("generic"):
        steps.append(("generic boards", lambda: generic.scan_generic_boards(ctx)))
    if want("discovery"):
        def discover():
            found = discovery.probe_companies(ctx, today)
            se_found, comeet_pages = discovery.search_engine_discovery(ctx)
            candidates = found + se_found + ctx.new_boards + [("comeet", u, "", "Bing") for u in comeet_pages]
            added = discovery.remember_boards(candidates, today)
            log.info("discovery: %d new sources", len(added))
            for b in added:  # scan newly discovered sources in this same run
                if b["kind"] in ("comeet", "comeet_api"):
                    ats.scan_comeet(ctx, b["slug"], "page" if b["kind"] == "comeet" else "api")
                elif b["kind"] == "workday":
                    ats.scan_workday(ctx, b["slug"])
                elif not any(s.url == ats.board_url(b["kind"], b["slug"]) for s in ctx.statuses):
                    ats.scan_board(ctx, b["kind"], b["slug"], b.get("company", ""))
        steps.append(("discovery", discover))

    for name, fn in steps:
        log.info("scanning %s ...", name)
        try:
            fn()
        except Exception as e:  # one broken source must never stop the daily report
            log.exception("source %s crashed", name)
            st = ctx.status(f"internal://{name}", name, "סורק פנימי")
            st.fail(f"שגיאה פנימית: {type(e).__name__}: {e}"[:300])
        log.info("  %s done - %d raw jobs so far", name, len(ctx.raw_jobs))


# ----------------------------------------------------------------------------- the 7 stages
def evaluate(raw, now):
    """Apply stages 1-7 to one job whose full page was fetched. Returns (Job|None, reason, date)."""
    # stage 1 - potential job by title / essence
    if not rules.is_potential(raw.title):
        return None, "כותרת לא רלוונטית", None
    # stage 2 - the full description must exist (we never decide on a snippet)
    if not raw.description or len(raw.description) < 80:
        return None, "תיאור משרה מלא לא זמין", None
    # stage 3 - mandatory keyword inside the description itself
    kws = rules.find_keywords(raw.description)
    if not kws:
        return None, "אין מילת מפתח בתיאור", None
    # stage 4 - essence & exclusions
    ok, why = rules.essence(raw.title, raw.description)
    if not ok:
        return None, why, None
    # stage 5 - location
    decision, loc_display, loc_note = classify(raw.location, raw.description, raw.url, raw.israeli_context)
    if title_says_abroad(raw.title):
        decision, loc_note = "foreign", "הכותרת מציינת מיקום מחוץ לישראל"
    if decision in ("excluded", "foreign"):
        return None, f"מיקום: {loc_note or decision}", None
    # stage 6 - date (latest of posted / updated)
    d = dates.relevant_date(raw.posted_raw, raw.updated_raw, now)
    fresh = dates.is_fresh(d, now)
    if fresh is False:
        return None, "ישנה מ-20 ימים", d
    # stage 7 - final decision
    reason = f"{why}; מילות מפתח בתיאור: {', '.join(kws[:6])}"
    if loc_note:
        reason += f"; {loc_note}"
    if d is None:
        reason += "; תאריך לא ידוע"
    company = raw.company.strip() or "לא צוין במקור"
    job = Job(title=raw.title.strip(), company=company, source=raw.source, location=loc_display or C.UNKNOWN,
              experience=rules.extract_experience(raw.description, raw.experience_hint), reason=reason,
              url=raw.url, date_display=d.strftime("%d/%m/%Y") if d else C.UNKNOWN_DATE,
              date_iso=d.isoformat() if d else None)
    job.key, job.alt_key = job_keys(job)
    return job, "נשלפה", d


COMPANY_SUFFIX_RE = re.compile(r"\b(?:ltd|inc|llc|limited|group|israel|technologies|בע\"?מ|בעמ)\b")


def _company_key(company):
    return re.sub(r"[^\w]", "", COMPANY_SUFFIX_RE.sub(" ", norm(company)))


def _location_key(location):
    """'Tel Aviv-Yafo, Tel Aviv District, Israel' and 'Tel Aviv' -> same key."""
    m = ISRAEL_RE.search(norm(location))
    if not m:
        return norm(location)
    return re.sub(r"\s(?:yafo|jaffa|יפו|district|illit|ilit|pituach|פיתוח)$", "", m.group(0))


def job_keys(job):
    """Primary key: the direct job URL. Secondary: company + title + city (same job on another site)."""
    alt = "|".join([_company_key(job.company), norm(job.title), _location_key(job.location)])
    return canonical_url(job.url), alt


# ----------------------------------------------------------------------------- state & cumulative list
def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    s.setdefault("jobs", [])
    s.setdefault("last_sent_date", None)
    s.setdefault("history", [])
    return s


def save_state(state):
    os.makedirs(C.DATA_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def update_cumulative(state, accepted, stale, now):
    """Returns (new_jobs, cumulative_jobs, removed_count). Mutates nothing in `state`."""
    today = dates.today_il(now).isoformat()
    cum = [Job.from_dict(d) for d in state["jobs"]]
    by_key = {j.key: j for j in cum}
    by_alt = {j.alt_key: j for j in cum}
    new_jobs = []
    for job in accepted:
        ex = by_key.get(job.key) or by_alt.get(job.alt_key)
        if ex:
            ex.last_seen = today
            if job.date_iso and (not ex.date_iso or job.date_iso > ex.date_iso):
                ex.date_iso, ex.date_display = job.date_iso, job.date_display
            if ex.location == C.UNKNOWN and job.location != C.UNKNOWN:
                ex.location = job.location
            if not ex.experience and job.experience:
                ex.experience = job.experience
            continue
        job.first_seen = job.last_seen = today
        cum.append(job)
        by_key[job.key], by_alt[job.alt_key] = job, job
        new_jobs.append(job)

    # a later run found a reliable date showing the job is older than 20 days -> remove
    stale_keys = set()
    for k, alt, d in stale:
        ex = by_key.get(k) or by_alt.get(alt)
        if ex and (not ex.date_iso or d.isoformat() >= ex.date_iso):
            stale_keys.add(ex.key)
    kept, removed = [], 0
    for j in cum:
        too_old = j.date_iso and dates.age_days(dates.parse_date(j.date_iso), now) > C.MAX_DAYS
        if j.key in stale_keys or too_old:
            removed += 1
            continue
        kept.append(j)
    kept.sort(key=lambda j: (j.date_iso or "0000", j.first_seen), reverse=True)
    new_jobs.sort(key=lambda j: (j.date_iso or "0000"), reverse=True)
    return new_jobs, kept, removed


def scan_and_evaluate(http, now, only=None):
    ctx = ScanContext(http, now)
    run_sources(ctx, only=only, today=dates.today_il(now).isoformat())

    accepted, stale, reasons = [], [], Counter()
    ctx.foreign_locations = Counter()  # audit trail: which location strings were treated as abroad
    seen_keys, seen_alt = set(), set()
    per_listing = Counter()
    for raw in ctx.raw_jobs:
        job, why, d = evaluate(raw, now)
        reasons[why] += 1
        if job is None:
            if why.startswith("מיקום: מיקום לא ישראלי") or why.startswith("מיקום: מחוץ"):
                ctx.foreign_locations[raw.location[:60]] += 1
            if d is not None and why == "ישנה מ-20 ימים":
                tmp = Job(title=raw.title, company=raw.company or "לא צוין במקור", source=raw.source,
                          location="", experience="", reason="", url=raw.url, date_display="", date_iso=None)
                k, _ = job_keys(tmp)
                stale.append((k, None, d))
            continue
        if job.key in seen_keys or job.alt_key in seen_alt:
            reasons["כפילות בהרצה"] += 1
            continue
        seen_keys.add(job.key)
        seen_alt.add(job.alt_key)
        accepted.append(job)
        per_listing[raw.listing_url] += 1
    for st in ctx.statuses:
        st.count = per_listing.get(st.url, 0)
        if st.notes and not st.error and st.status != "הצלחה":
            st.error = "; ".join(dict.fromkeys(st.notes))[:500]
    return ctx, accepted, stale, reasons
