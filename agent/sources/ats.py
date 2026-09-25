"""Company career pages hosted on common ATS platforms, read through their public JSON APIs."""
import json
import re

from .. import rules
from ..location import classify
from ..models import RawJob
from ..net import FetchError
from ..textutil import html_to_text

KIND_LABEL = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "workable": "Workable",
              "smartrecruiters": "SmartRecruiters", "comeet": "Comeet"}


def board_url(kind, slug):
    return {
        "greenhouse": f"https://job-boards.greenhouse.io/{slug}",
        "lever": f"https://jobs.lever.co/{slug}",
        "ashby": f"https://jobs.ashbyhq.com/{slug}",
        "workable": f"https://apply.workable.com/{slug}/",
        "smartrecruiters": f"https://careers.smartrecruiters.com/{slug}",
    }.get(kind, slug)


def parse_ats_url(url):
    """Recognize an ATS career-page URL -> (kind, slug) or None."""
    pats = [
        ("greenhouse", r"greenhouse\.io/embed/job_board(?:/js)?\?for=([\w-]+)"),
        ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([\w-]+)"),
        ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/([\w-]+)"),
        ("lever", r"jobs\.lever\.co/([\w.-]+)"),
        ("ashby", r"jobs\.ashbyhq\.com/([\w.%-]+)"),
        ("workable", r"apply\.workable\.com/([\w-]+)"),
        ("smartrecruiters", r"(?:careers|jobs)\.smartrecruiters\.com/([\w-]+)"),
    ]
    for kind, p in pats:
        m = re.search(p, url, re.I)
        if m and m.group(1).lower() not in ("embed", "api", "v1", "j", "jobs"):
            return kind, m.group(1)
    return None


# Each fetcher returns (company_name, [dict(title, url, location, description, posted, updated, id)])
def _greenhouse(http, slug, need_desc, rt=3):
    name = slug
    if need_desc:
        try:
            name = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}", retries=1).get("name") or slug
        except FetchError:
            pass
    data = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                         params={"content": "true"} if need_desc else None, retries=rt)
    jobs = []
    for j in data.get("jobs", []):
        jobs.append({"title": j.get("title", ""), "url": j.get("absolute_url", ""),
                     "location": (j.get("location") or {}).get("name", ""),
                     "description": html_to_text(j.get("content", "")) if need_desc else "",
                     "posted": j.get("first_published", ""), "updated": j.get("updated_at", ""),
                     "id": str(j.get("id", ""))})
    return name, jobs


def _lever(http, slug, need_desc, rt=3):
    data = http.get_json(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}, retries=rt)
    if not isinstance(data, list):
        raise FetchError("תשובה לא צפויה")
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location", "")]
        loc = " | ".join(l for l in locs if l)
        if j.get("country") == "IL" and "israel" not in loc.lower():
            loc = (loc + ", Israel").strip(", ")
        parts = [j.get("descriptionPlain", "")]
        for lst in j.get("lists") or []:
            parts.append(lst.get("text", ""))
            parts.append(html_to_text(lst.get("content", "")))
        parts.append(j.get("additionalPlain", ""))
        jobs.append({"title": j.get("text", ""), "url": j.get("hostedUrl", ""), "location": loc,
                     "description": "\n".join(p for p in parts if p), "posted": j.get("createdAt"),
                     "updated": "", "id": j.get("id", "")})
    return slug, jobs


def _ashby(http, slug, need_desc, rt=3):
    data = http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                         params={"includeCompensation": "false"}, retries=rt)
    jobs = []
    for j in data.get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "")
        loc = " | ".join(l for l in locs if l)
        if country and country.lower() not in loc.lower():
            loc = f"{loc}, {country}".strip(", ")
        if j.get("isRemote") and "remote" not in loc.lower():
            loc = f"{loc} (Remote)".strip()
        jobs.append({"title": j.get("title", ""), "url": j.get("jobUrl", ""), "location": loc,
                     "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml", "")),
                     "posted": j.get("publishedAt", ""), "updated": j.get("updatedAt", ""), "id": j.get("id", "")})
    return slug, jobs


def _workable(http, slug, need_desc, rt=3):
    name = slug
    if need_desc:
        try:
            name = http.get_json(f"https://apply.workable.com/api/v1/accounts/{slug}", retries=1).get("name") or slug
        except FetchError:
            pass
    jobs, token = [], None
    for _ in range(10):
        body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        if token:
            body["token"] = token
        data = http.post(f"https://apply.workable.com/api/v3/accounts/{slug}/jobs", json=body, retries=rt).json()
        for j in data.get("results", []):
            locs = j.get("locations") or [j.get("location") or {}]
            loc = " | ".join(", ".join(x for x in [l.get("city", ""), l.get("country", "")] if x) for l in locs)
            if j.get("remote"):
                loc = f"{loc} (Remote)".strip()
            jobs.append({"title": j.get("title", ""), "shortcode": j.get("shortcode"),
                         "url": f"https://apply.workable.com/{slug}/j/{j.get('shortcode')}/", "location": loc,
                         "description": "", "posted": j.get("published", ""), "updated": "",
                         "id": j.get("shortcode", "")})
        token = data.get("nextPage")
        if not token:
            break
    return name, jobs


def _workable_desc(http, slug, shortcode):
    d = http.get_json(f"https://apply.workable.com/api/v2/accounts/{slug}/jobs/{shortcode}")
    return "\n".join(html_to_text(d.get(k, "")) for k in ("description", "requirements", "benefits") if d.get(k))


def _smartrecruiters(http, slug, need_desc, rt=3):
    jobs, name, offset = [], slug, 0
    while True:
        data = http.get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                             params={"country": "il", "limit": 100, "offset": offset}, retries=rt)
        for j in data.get("content", []):
            name = (j.get("company") or {}).get("name") or name
            loc = j.get("location") or {}
            jobs.append({"title": j.get("name", ""), "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                         "location": ", ".join(x for x in [loc.get("city", ""), "Israel" if loc.get("country") == "il"
                                                           else loc.get("country", "")] if x),
                         "description": "", "posted": j.get("releasedDate", ""), "updated": "", "id": j.get("id", "")})
        offset += 100
        if offset >= data.get("totalFound", 0):
            break
    return name, jobs


def _smartrecruiters_desc(http, slug, jid):
    d = http.get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}")
    sec = (d.get("jobAd") or {}).get("sections") or {}
    # companyDescription is the "about us" block, not the job description itself
    return "\n".join(html_to_text((sec.get(k) or {}).get("text", ""))
                     for k in ("jobDescription", "qualifications", "additionalInformation"))


FETCHERS = {"greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby, "workable": _workable,
            "smartrecruiters": _smartrecruiters}


def list_board(http, kind, slug, need_desc=True, retries=3):
    return FETCHERS[kind](http, slug, need_desc, retries)


def board_has_israel_jobs(jobs):
    return any(classify(j.get("location", ""))[0] == "israel" for j in jobs)


def scan_board(ctx, kind, slug, company_hint=""):
    http = ctx.http
    if any(s.url == board_url(kind, slug) for s in ctx.statuses):
        return  # already scanned in this run
    st = ctx.status(board_url(kind, slug), f"{KIND_LABEL[kind]} ({company_hint or slug})",
                    f"{KIND_LABEL[kind]} public API")
    if http.out_of_time():
        st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
        return
    try:
        name, jobs = list_board(http, kind, slug)
    except FetchError as e:
        st.fail(str(e), "לא נגיש" if e.status == 404 else "נכשל")
        return
    company = company_hint or (name if name and name != slug else slug.replace("-", " ").replace("_", " ").title())
    st.site = f"{KIND_LABEL[kind]} ({company})"
    for j in jobs:
        if not rules.is_potential(j["title"]) or not j["url"]:
            continue
        # skip jobs clearly abroad before fetching extra detail pages (stage 5 is re-applied later anyway)
        if classify(j["location"])[0] in ("foreign",) and kind in ("workable", "smartrecruiters"):
            continue
        if not ctx.first_time(j["url"]):
            continue
        desc = j["description"]
        try:
            if kind == "workable":
                desc = _workable_desc(http, slug, j["shortcode"])
            elif kind == "smartrecruiters":
                desc = _smartrecruiters_desc(http, slug, j["id"])
        except FetchError:
            st.partial("חלק מעמודי המשרה לא נטענו")
            continue
        ctx.add(RawJob(title=j["title"], company=company, source=company, url=j["url"], description=desc,
                       location=j["location"], posted_raw=j["posted"], updated_raw=j["updated"], job_id=j["id"],
                       israeli_context=False, listing_url=st.url))


# ----------------------------------------------------------------------------- Comeet
COMEET_PAGE_RE = re.compile(r"comeet\.com/jobs/([\w-]+)/([0-9A-F]{2}\.[0-9A-F]{3})", re.I)
COMEET_UID_RE = re.compile(r"""(?:comeet_uid|company-uid|company_uid|integration_id)["'\s:=]+["']([0-9A-F]{2}\.[0-9A-F]{3})""",
                           re.I)
COMEET_TOKEN_RE = re.compile(r"""(?:comeet_token|integration_token|["']token)["'\s:=]+["']([0-9A-F]{16,})""", re.I)


def find_comeet(html):
    """Comeet boards referenced by a page: ('page', company_page_url) and/or ('api', 'UID|TOKEN')."""
    found = set()
    for slug, uid in COMEET_PAGE_RE.findall(html or ""):
        found.add(("page", f"https://www.comeet.com/jobs/{slug}/{uid.upper()}"))
    uid, token = COMEET_UID_RE.search(html or ""), COMEET_TOKEN_RE.search(html or "")
    if uid and token:
        found.add(("api", f"{uid.group(1).upper()}|{token.group(1)}"))
    return found


def comeet_key(value):
    """Company UID - the identity of a Comeet board, so the same company is never scanned twice."""
    m = COMEET_PAGE_RE.search(value)
    return (m.group(2) if m else value.split("|")[0]).upper()


def _comeet_positions_from_page(http, page_url):
    html = http.get_text(page_url)
    i = html.find("COMPANY_POSITIONS_DATA =")
    if i < 0:
        raise FetchError("לא נמצאה רשימת משרות בעמוד Comeet")
    try:
        data, _ = json.JSONDecoder().raw_decode(html[i + len("COMPANY_POSITIONS_DATA ="):].lstrip())
    except ValueError:
        raise FetchError("מבנה נתוני Comeet לא מוכר")
    name = re.search(r'COMPANY_DATA = \{"name": "([^"]+)"', html)
    return (name.group(1) if name else ""), data or []


def scan_comeet(ctx, value, kind="page", company_hint=""):
    """kind='page': a comeet.com/jobs/<company>/<UID> page (its positions are embedded - no token needed).
    kind='api': 'UID|TOKEN' found on a company's own careers page -> Comeet public careers API."""
    http = ctx.http
    key = comeet_key(value)
    if key in ctx.comeet_done:
        return
    ctx.comeet_done.add(key)
    if kind == "page":
        m = COMEET_PAGE_RE.search(value)
        url = f"https://www.comeet.com/jobs/{m.group(1)}/{m.group(2).upper()}" if m else value
        st = ctx.status(url, f"Comeet ({company_hint or (m.group(1) if m else key)})",
                        "Comeet - נתוני המשרות מעמוד החברה")
    else:
        uid, token = value.split("|", 1)
        url = f"https://www.comeet.co/careers-api/2.0/company/{uid}/positions"
        st = ctx.status(url, f"Comeet ({company_hint or uid})", "Comeet public careers API")
    if http.out_of_time():
        st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
        return
    try:
        if kind == "page":
            company, positions = _comeet_positions_from_page(http, url)
        else:
            positions = http.get_json(url, params={"token": token, "details": "true"})
            company = next((p.get("company_name") for p in positions or [] if p.get("company_name")), "")
    except FetchError as e:
        st.fail(str(e))
        return
    company = company_hint or company or key
    st.site = f"Comeet ({company})"
    for p in positions or []:
        title = p.get("name", "")
        job_url = p.get("url_comeet_hosted_page") or p.get("url_active_page") or ""
        if not job_url or not rules.is_potential(title) or not ctx.first_time(job_url):
            continue
        loc = p.get("location") or {}
        country = "Israel" if loc.get("country") == "IL" else loc.get("country", "")
        loc_s = ", ".join(x for x in [loc.get("city", ""), country] if x) or loc.get("name", "")
        details = p.get("details") or (p.get("custom_fields") or {}).get("details") or []
        desc = "\n".join(html_to_text(d.get("value", "")) for d in details if isinstance(d, dict))
        ctx.add(RawJob(title=title, company=p.get("company_name") or company, source=company, url=job_url,
                       description=desc, location=loc_s, updated_raw=p.get("time_updated", ""),
                       job_id=p.get("uid", ""), listing_url=st.url))


# ----------------------------------------------------------------------------- Workday
WORKDAY_RE = re.compile(r"https?://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)")
WORKDAY_QUERIES = ["analyst", "analytics", "data", "BI", "insights"]
ISRAEL_FACET_RE = re.compile(r"israel|tel aviv|herzliya|petah|ra'?anana|yokneam|haifa|jerusalem|ramat gan|netanya|"
                             r"kfar saba|hod hasharon|rosh ha|airport city|modiin|or yehuda", re.I)


def workday_base(url):
    m = WORKDAY_RE.search(url or "")
    if not m or m.group(3) in ("wday", "job"):
        return None
    return f"https://{m.group(1)}.{m.group(2)}.myworkdayjobs.com/{m.group(3)}"


def _israel_facets(facets):
    """Workday location facet ids whose name is in Israel -> {facetParameter: [ids]}."""
    out = {}

    def walk(items, param):
        for f in items or []:
            p = f.get("facetParameter", param)
            if f.get("id") and ISRAEL_FACET_RE.search(f.get("descriptor", "")):
                out.setdefault(p, []).append(f["id"])
            walk(f.get("values"), p)

    walk(facets, None)
    # one location facet is enough (country is preferred - it covers every Israeli office)
    for pref in ("locationCountry", "Location_Country", "locationHierarchy1", "locations"):
        if pref in out:
            return {pref: out[pref]}
    loc = {k: v for k, v in out.items() if k and "location" in k.lower()}
    return dict([next(iter(loc.items()))]) if loc else {}


def scan_workday(ctx, base, company_hint=""):
    http = ctx.http
    m = WORKDAY_RE.search(base)
    tenant, site = m.group(1), m.group(3)
    api = f"https://{base.split('/')[2]}/wday/cxs/{tenant}/{site}"
    if any(s.url == base for s in ctx.statuses):
        return
    st = ctx.status(base, f"Workday ({company_hint or tenant})", "Workday public jobs API (משרות בישראל)")
    if http.out_of_time():
        st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
        return
    try:
        first = http.post(f"{api}/jobs", json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}).json()
    except (FetchError, ValueError) as e:
        st.fail(str(e))
        return
    facets = _israel_facets(first.get("facets"))
    if not facets:
        st.notes.append("אין לחברה משרות בישראל ב-Workday")
        return
    company = company_hint or tenant.title()
    for q in WORKDAY_QUERIES:
        for offset in range(0, 200, 20):
            try:
                data = http.post(f"{api}/jobs", json={"appliedFacets": facets, "limit": 20, "offset": offset,
                                                      "searchText": q}).json()
            except (FetchError, ValueError) as e:
                st.partial(f"חיפוש '{q}': {e}")
                break
            posts = data.get("jobPostings") or []
            for jp in posts:
                title, path = jp.get("title", ""), jp.get("externalPath", "")
                job_url = f"{base}{path}"
                if not path or not rules.is_potential(title) or not ctx.first_time(job_url):
                    continue
                try:
                    info = http.get_json(f"{api}{path}").get("jobPostingInfo") or {}
                except FetchError:
                    st.partial("חלק מעמודי המשרה לא נטענו")
                    continue
                country = (info.get("country") or {}).get("descriptor", "")
                loc = ", ".join(x for x in [info.get("location", ""), country] if x)
                ctx.add(RawJob(title=title, company=company, source=company, url=info.get("externalUrl") or job_url,
                               description=html_to_text(info.get("jobDescription", "")), location=loc,
                               posted_raw=info.get("startDate") or jp.get("postedOn", ""),
                               job_id=info.get("jobReqId", ""), listing_url=st.url))
            if len(posts) < 20:
                break
