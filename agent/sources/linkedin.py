"""LinkedIn Jobs via the public (logged-out) jobs endpoints."""
import logging
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .. import config as C
from .. import rules
from ..models import RawJob
from ..net import FetchError

log = logging.getLogger("agent")

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
ISRAEL_GEO_ID = "101620260"
MAX_PAGES = 40
PAST_SECONDS = C.MAX_DAYS * 86400


def build_queries():
    base = []
    for t in C.TITLES_EN:
        if re.match(r"(?i)(senior|junior|lead)\s", t):
            continue  # "Data Analyst" already matches "Senior Data Analyst"
        base.append(t.replace("&", "and"))
    base = list(dict.fromkeys(base))
    n = C.LINKEDIN_QUERY_GROUP_SIZE
    queries = [" OR ".join(f'"{t}"' for t in base[i:i + n]) for i in range(0, len(base), n)]
    he = list(dict.fromkeys(t.replace("/ית", "") for t in C.TITLES_HE if "ית " not in t and not t.endswith("ית")))
    queries += [" OR ".join(f'"{t}"' for t in he[i:i + n]) for i in range(0, len(he), n)]
    queries += C.LINKEDIN_EXTRA_QUERIES
    return queries


def _search_url(q, start):
    return SEARCH + "?" + urlencode({"keywords": q, "location": "Israel", "geoId": ISRAEL_GEO_ID,
                                     "f_TPR": f"r{PAST_SECONDS}", "start": start})


def parse_cards(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for li in soup.select("li"):
        urn = li.select_one("[data-entity-urn]")
        if not urn:
            continue
        jid = urn["data-entity-urn"].split(":")[-1]
        g = lambda sel: (li.select_one(sel).get_text(" ", strip=True) if li.select_one(sel) else "")
        t = li.select_one("time")
        out.append({
            "id": jid,
            "title": g("h3") or g(".base-search-card__title"),
            "company": g("h4") or g(".base-search-card__subtitle"),
            "location": g(".job-search-card__location"),
            "date": t.get("datetime", "") if t else "",
        })
    return out


def fetch_detail(http, jid):
    html = http.get_text(DETAIL.format(jid), headers={"Accept-Language": "en-US,en;q=0.9"})
    soup = BeautifulSoup(html, "lxml")
    desc = soup.select_one(".show-more-less-html__markup") or soup.select_one(".description__text")
    if not desc:
        raise FetchError("לא נמצא תיאור משרה בעמוד")
    posted = soup.select_one(".posted-time-ago__text")
    seniority, industry = "", ""
    for item in soup.select(".description__job-criteria-item"):
        h = item.select_one("h3")
        v = item.select_one(".description__job-criteria-text")
        if h and v and "seniority" in h.get_text().lower():
            seniority = v.get_text(strip=True)
        if h and v and "industr" in h.get_text().lower():
            industry = v.get_text(" ", strip=True)
    title = soup.select_one(".top-card-layout__title, h2")
    return {
        "description": desc.get_text("\n", strip=True),
        "posted_rel": posted.get_text(strip=True) if posted else "",
        "seniority": seniority if seniority and seniority.lower() != "not applicable" else "",
        "industry": industry,
        "title": title.get_text(strip=True) if title else "",
    }


def scan(ctx, queries=None):
    http = ctx.http
    queries = queries or build_queries()
    for qi, q in enumerate(queries, 1):
        if http.out_of_time():
            st = ctx.status(_search_url(q, 0), "LinkedIn", "LinkedIn Jobs guest search (ישראל, 20 ימים)")
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        st = ctx.status(_search_url(q, 0), "LinkedIn", "LinkedIn Jobs guest search API + עמוד משרה מלא")
        cards_total, detail_fail = 0, 0
        for page in range(MAX_PAGES):
            try:
                html = http.get_text(_search_url(q, page * 10))
            except FetchError as e:
                if page == 0:
                    st.fail(str(e), "לא נגיש" if e.status in (403, 999) else "נכשל")
                else:
                    st.partial(f"עצירה בעמוד {page + 1}: {e}")
                break
            cards = parse_cards(html)
            if not cards:
                break
            cards_total += len(cards)
            for c in cards:
                url = f"https://www.linkedin.com/jobs/view/{c['id']}"
                if not rules.is_potential(c["title"]):
                    continue
                ctx.saw_company(c["company"], "LinkedIn")
                if not ctx.first_time(url):
                    continue
                try:
                    d = fetch_detail(http, c["id"])
                except FetchError as e:
                    detail_fail += 1
                    if "זמן" in str(e):
                        break
                    continue
                ctx.add(RawJob(title=c["title"] or d["title"], company=c["company"], source="LinkedIn", url=url,
                               description=d["description"], location=c["location"],
                               posted_raw=c["date"] or d["posted_rel"], job_id=c["id"],
                               israeli_context=True, listing_url=st.url, industry=d["industry"]))
            if len(cards) < 5:
                break
        if detail_fail:
            st.partial(f"{detail_fail} עמודי משרה לא נטענו")
        log.info("  LinkedIn query %d/%d: %d cards, %d job pages so far, status=%s %s",
                 qi, len(queries), cards_total, len(ctx.raw_jobs), st.status, st.error[:80])
        if cards_total == 0 and st.status == "הצלחה":
            st.notes.append("0 תוצאות")
