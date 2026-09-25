"""Dynamic source discovery (spec 2.2).

1. Company -> ATS probing: every company seen on LinkedIn / Drushim / JobMaster / AllJobs is probed on the
   common ATS platforms (Greenhouse, Lever, Ashby, Workable, SmartRecruiters). Boards that exist and publish
   Israeli jobs become permanent scan sources (data/discovered_sources.json).
2. Search-engine discovery (best effort): ATS career pages found through web search.
3. ATS boards embedded in any crawled page / user link (handled in generic.crawl) are persisted too.
"""
import base64
import concurrent.futures as cf
import json
import os
import re
import time
import unicodedata
from datetime import timedelta
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

from bs4 import BeautifulSoup

from .. import config as C
from ..net import FetchError
from . import ats

DISCOVERED_FILE = os.path.join(C.DATA_DIR, "discovered_sources.json")
CACHE_FILE = os.path.join(C.DATA_DIR, "discovery_cache.json")
STOP_WORDS = {"ltd", "inc", "llc", "limited", "group", "technologies", "technology", "tech", "israel", "il",
              "the", "co", "corp", "corporation", "software", "solutions", "labs", "company", "גרופ", "בעמ"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load_discovered():
    return _load(DISCOVERED_FILE, [])


def remember_boards(boards, today):
    """Persist (kind, slug, company, via) boards; returns the ones that are new."""
    known = load_discovered()
    have = {(b["kind"], b["slug"].lower()) for b in known}
    have |= {(k, s.lower()) for k, s in C.SEED_ATS_BOARDS}
    added = []
    for kind, slug, company, via in boards:
        if kind not in C.ATS_KINDS + ["comeet", "comeet_api", "workday"] or (kind, slug.lower()) in have:
            continue
        have.add((kind, slug.lower()))
        rec = {"kind": kind, "slug": slug, "company": company, "via": via, "found_on": today}
        known.append(rec)
        added.append(rec)
    if added:
        _save(DISCOVERED_FILE, known)
    return added


def slug_candidates(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\(.*?\)|\.com|\.io|\.ai|[^a-z0-9 \-]", " ", n)
    words = [w for w in re.split(r"[\s\-]+", n) if w and w not in STOP_WORDS]
    if not words:
        return []
    c = ["".join(words), "-".join(words), words[0]]
    return [s for s in dict.fromkeys(c) if 3 <= len(s) <= 40]


def _probe(http, kind, slug):
    try:
        _, jobs = ats.list_board(http, kind, slug, need_desc=False, retries=0)
    except (FetchError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return (kind, slug) if jobs and ats.board_has_israel_jobs(jobs) else None


def probe_companies(ctx, today):
    """Probe ATS platforms for companies seen during this run. Cached for DISCOVERY_RECHECK_DAYS."""
    cache = _load(CACHE_FILE, {})
    cutoff = (ctx.now.date() - timedelta(days=C.DISCOVERY_RECHECK_DAYS)).isoformat()
    # most likely slug of every company first ("moonactive"), then the alternatives ("moon-active", "moon")
    by_rank = [[], [], []]
    for company, site in ctx.companies.items():
        for rank, slug in enumerate(slug_candidates(company)):
            if cache.get(slug, "") < cutoff:
                by_rank[rank].append((company, site, slug))
    todo = (by_rank[0] + by_rank[1] + by_rank[2])[:C.DISCOVERY_MAX_PROBES_PER_RUN]
    budget_end = time.time() + C.DISCOVERY_MAX_MINUTES * 60
    st = ctx.status("ats-probe://" + ",".join(C.ATS_KINDS), "גילוי אוטומטי (חברות → ATS)", "")
    found = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {}
        for company, site, slug in todo:
            for kind in C.ATS_KINDS:
                futs[ex.submit(_probe_until, ctx.http, kind, slug, budget_end)] = (company, site, slug)
        done_slugs = set()
        for f in cf.as_completed(futs):
            company, site, slug = futs[f]
            r = f.result()
            if r == "skipped":
                continue
            done_slugs.add(slug)
            if r:
                found.append((r[0], r[1], company, f"נמצא דרך {site}"))
    for slug in done_slugs:
        cache[slug] = today
    skipped = len({s for _, _, s in todo} - done_slugs)
    _save(CACHE_FILE, cache)
    st.method = (f"בדיקת {len(done_slugs)} מזהי חברות מול Greenhouse/Lever/Ashby/Workable/SmartRecruiters"
                 + (f" ({skipped} נדחו להרצה הבאה - מגבלת זמן)" if skipped else ""))
    st.notes.append(f"נמצאו {len(found)} לוחות קריירה עם משרות בישראל")
    return found


def _probe_until(http, kind, slug, budget_end):
    if time.time() > budget_end or http.out_of_time():
        return "skipped"
    return _probe(http, kind, slug)


def _decode_bing(href):
    q = parse_qs(urlparse(href).query).get("u", [""])[0]
    if q.startswith("a1"):
        try:
            return base64.urlsafe_b64decode(q[2:] + "=" * (-len(q[2:]) % 4)).decode("utf-8", "ignore")
        except ValueError:
            return ""
    return href


def search_engine_discovery(ctx):
    found, comeet_pages = [], []
    for q in C.SEARCH_DISCOVERY_QUERIES:
        url = f"https://www.bing.com/search?q={quote_plus(q)}&count=50"
        st = ctx.status(url, "Bing (גילוי מקורות)", "חיפוש מנוע חיפוש לאיתור עמודי קריירה")
        if ctx.http.out_of_time():
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        try:
            html = ctx.http.get_text(url, retries=1)
        except FetchError as e:
            st.fail(str(e))
            continue
        soup = BeautifulSoup(html, "lxml")
        hits = 0
        for a in soup.select("li.b_algo h2 a[href], li.b_algo a[href]"):
            link = unquote(_decode_bing(a["href"]))
            p = ats.parse_ats_url(link)
            if p:
                found.append((p[0], p[1], "", "Bing"))
                hits += 1
            elif re.search(r"comeet\.com/jobs/[\w-]+/[\w.]+", link):
                comeet_pages.append(re.search(r"https?://[^?#]*comeet\.com/jobs/[\w-]+/[\w.]+", link).group(0))
                hits += 1
        if hits == 0:
            st.partial("לא נמצאו קישורי קריירה בתוצאות")
    return found, list(dict.fromkeys(comeet_pages))
