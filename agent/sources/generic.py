"""Generic crawler for any career page / job board / single job page (incl. user-supplied links)."""
import re
from urllib.parse import urljoin, urlparse, quote_plus

from bs4 import BeautifulSoup

from .. import config as C
from .. import rules
from ..models import RawJob
from ..net import FetchError
from ..textutil import find_jsonld_jobposting, html_to_text, jsonld_location, main_content_text, site_name
from . import ats, israeli_boards

JOB_HREF_RE = re.compile(r"job|career|position|opening|vacanc|משרה|misra|apply|/j/|/o/|/p/|jid|jobid|/\d{4,}", re.I)
ATS_URL_RE = re.compile(r"https?:(?://|\\/\\/)[\w.-]*(?:greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|"
                        r"smartrecruiters\.com)[^\s\"'<>)]*", re.I)
ATS_LINK_RE = re.compile(r"greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|smartrecruiters\.com|comeet\.com/jobs", re.I)
# a link to one specific job (has an id / uuid / job-name slug) - not a menu link like "Teams" or "Search"
JOB_DETAIL_HREF_RE = re.compile(
    r"\d{4,}|[0-9a-f]{8}-[0-9a-f]{4}|[0-9A-F]{2}\.[0-9A-F]{3}|"
    r"/(?:jobs?|positions?|careers?|open-positions|misra|details|vacancies)/(?!(?:results|search|teams?|locations?|"
    r"students?|all|about|benefits|life|culture|faq)\b)[^/?#]{6,}", re.I)
DATE_TEXT_RE = re.compile(r"(?:פורסם|עודכן|posted|updated|published|date posted)\s*:?\s*"
                          r"((?:לפני\s+)?[\w\s/.,\-]{2,25}?)(?:\n|$|\|)", re.I)


def _job_from_page(url, html, fallback_title="", site=""):
    """Extract a single job from its own page. Prefers schema.org JobPosting, else main content."""
    soup = BeautifulSoup(html, "lxml")
    if "jobmaster.co.il" in urlparse(url).netloc and soup.select_one(".article__jobBody"):
        head = soup.select_one(".jobHead__text__titleAndCompName")
        comp = soup.select_one(".CompanyNameLink, .jobHead__text__moreJobs a")
        body = soup.select_one(".article__jobBody")
        for junk in body.select(".jobsCategories, .jobBtnContainer"):
            junk.decompose()
        info = soup.select_one(".jobHead__text__moreInfo")
        m = re.search(r"פורסם\s+[^\n|]{2,20}?(?:ימים|יום|שעות|שעה|שבוע|שבועות|חודש|אתמול|היום)",
                      info.get_text(" ", strip=True) if info else "")
        return {"title": head.get_text(" ", strip=True) if head else fallback_title,
                "company": re.sub(r"^מעבר למשרות נוספות\s*", "", comp.get_text(" ", strip=True)) if comp else "",
                "description": body.get_text("\n", strip=True), "location": "",
                "posted": m.group(0) if m else "", "updated": ""}
    jp = find_jsonld_jobposting(soup)
    if jp:
        org = jp.get("hiringOrganization") or {}
        company = org.get("name", "") if isinstance(org, dict) else str(org)
        description = html_to_text(jp.get("description", ""))
        # some boards put only the description in JSON-LD; their full text (incl. requirements) is on the page
        host = urlparse(url).netloc
        if "drushim.co.il" in host:
            description = israeli_boards._drushim_description(html) or description
        elif "jobmaster.co.il" in host:
            body = soup.select_one(".article__jobBody")
            if body:
                for junk in body.select(".jobsCategories, .jobBtnContainer"):
                    junk.decompose()
                description = body.get_text("\n", strip=True)
        return {"title": html_to_text(jp.get("title", "")) or fallback_title, "company": company,
                "description": description, "location": jsonld_location(jp),
                "posted": jp.get("datePosted", ""), "updated": jp.get("dateModified", "")}
    h1 = soup.select_one("h1")
    og_site = soup.select_one('meta[property="og:site_name"]')
    title = fallback_title or (h1.get_text(" ", strip=True) if h1 else "")
    page_text = soup.get_text("\n", strip=True)
    m = DATE_TEXT_RE.search(page_text)
    return {"title": title, "company": og_site.get("content", "") if og_site else "",
            "description": main_content_text(soup), "location": "", "posted": m.group(1) if m else "",
            "updated": ""}


def crawl(ctx, url, method="סריקה כללית של עמוד (HTML / JSON-LD)", site=None, israeli_context=None):
    http = ctx.http
    site = site or site_name(url)
    if israeli_context is None:
        israeli_context = bool(re.search(r"\.co\.il|\.org\.il", urlparse(url).netloc))
    # Known ATS -> use its API instead of scraping the rendered page
    parsed = ats.parse_ats_url(url)
    if parsed:
        kind, slug = parsed
        ctx.new_boards.append((kind, slug, "", url))
        ats.scan_board(ctx, kind, slug)
        return
    if ats.COMEET_PAGE_RE.search(url):
        ctx.new_boards.append(("comeet", ats.COMEET_PAGE_RE.search(url).group(0), "", url))
        ats.scan_comeet(ctx, url)
        return
    wd = ats.workday_base(url)
    if wd:
        ctx.new_boards.append(("workday", wd, "", url))
        ats.scan_workday(ctx, wd)
        return
    jv = re.search(r"jobs\.jobvite\.com/(?:careers/)?([\w-]+)", url)
    if jv:  # the search page is rendered in JavaScript; the plain job list is not
        url = f"https://jobs.jobvite.com/{jv.group(1)}/jobs"

    st = ctx.status(url, site, method)
    if http.out_of_time():
        st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
        return
    try:
        html = http.get_text(url)
    except FetchError as e:
        st.fail(str(e), "לא נגיש" if e.status in (401, 403, 404) else "נכשל")
        return
    soup = BeautifulSoup(html, "lxml")

    # 1) ATS boards referenced anywhere in the page (links, iframes, widget scripts, embedded JSON).
    #    Checked first: a careers page may carry JSON-LD for one job while the ATS holds all of them.
    embedded = set()
    for m in ATS_URL_RE.finditer(html):
        p = ats.parse_ats_url(m.group(0).replace("\\/", "/"))
        if p:
            embedded.add(p)
    for kind, slug in embedded:
        ctx.new_boards.append((kind, slug, "", url))
        ats.scan_board(ctx, kind, slug)
    for ckind, value in ats.find_comeet(html):
        ctx.new_boards.append(("comeet" if ckind == "page" else "comeet_api", value, "", url))
        ats.scan_comeet(ctx, value, ckind)
        embedded.add(("comeet", value))
    for base in {ats.workday_base(m.group(0)) for m in ats.WORKDAY_RE.finditer(html)} - {None}:
        ctx.new_boards.append(("workday", base, "", url))
        ats.scan_workday(ctx, base)
        embedded.add(("workday", base))

    #    The recruiting system already returned every job with clean data - following the page's own
    #    links would only create duplicates.
    if embedded:
        st.method += " → " + ", ".join(sorted({k for k, _ in embedded})) + " (נסרק דרך מערכת הגיוס)"
        return

    # 2) the link itself is a single job page
    if find_jsonld_jobposting(soup) or ("jobmaster.co.il" in url and soup.select_one(".article__jobBody")):
        if ctx.first_time(url):
            _emit(ctx, url, _job_from_page(url, html, site=site), site, israeli_context, st)
        return

    # 3) listing page -> follow links whose text looks like a relevant job title
    base_host = urlparse(url).netloc
    links, job_like = [], 0
    for a in soup.select("a[href]"):
        text = a.get_text(" ", strip=True) or a.get("title", "") or a.get("aria-label", "")
        href = urljoin(url, a["href"]).split("#")[0]
        if not text or len(text) > 160 or href == url or not href.startswith("http"):
            continue
        host = urlparse(href).netloc
        if host != base_host and not ATS_LINK_RE.search(host):
            continue
        if not JOB_HREF_RE.search(href):
            continue
        if JOB_DETAIL_HREF_RE.search(urlparse(href).path + "?" + urlparse(href).query):
            job_like += 1
        if rules.is_potential(text):
            links.append((href, text))
    links = list(dict(links).items())[:C.GENERIC_MAX_DETAIL_PER_PAGE]
    if not links and job_like >= 2:
        st.notes.append("אין בעמוד משרות רלוונטיות כרגע")
    elif not links:
        st.partial("לא נמצאו משרות בעמוד - העמוד נטען ב-JavaScript ואין בו מערכת גיוס מוכרת")
    fails = 0
    for href, text in links:
        if not ctx.first_time(href):
            continue
        try:
            jhtml = http.get_text(href)
        except FetchError:
            fails += 1
            continue
        _emit(ctx, href, _job_from_page(href, jhtml, fallback_title=text, site=site), site, israeli_context, st)
    if fails:
        st.partial(f"{fails} עמודי משרה לא נטענו")


def _emit(ctx, url, job, site, israeli_context, st):
    if not job.get("description"):
        st.partial("עמוד משרה ללא תיאור")
        return
    ctx.saw_company(job.get("company"), site)
    ctx.add(RawJob(title=job["title"], company=job.get("company", ""), source=site, url=url,
                   description=job["description"], location=job.get("location", ""),
                   posted_raw=job.get("posted", ""), updated_raw=job.get("updated", ""),
                   israeli_context=israeli_context, listing_url=st.url))


def scan_generic_boards(ctx):
    for name, template in C.GENERIC_BOARDS:
        for q in C.GENERIC_BOARD_QUERIES:
            crawl(ctx, template.format(q=quote_plus(q)), method="חיפוש באתר דרושים (HTML) + עמוד משרה",
                  site=name, israeli_context=True)
