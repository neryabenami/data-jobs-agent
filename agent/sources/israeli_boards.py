"""Israeli job boards: Drushim, JobMaster, AllJobs, plus an Indeed attempt."""
import json
import re
from urllib.parse import quote, quote_plus, urljoin

from bs4 import BeautifulSoup

from .. import config as C
from .. import rules
from ..models import RawJob
from ..net import FetchError
from ..textutil import find_jsonld_jobposting, html_to_text, jsonld_location

MAX_PAGES = 12


# ----------------------------------------------------------------------------- Drushim
DRUSHIM_API = "https://webapi.drushim.co.il/api/jobs/search"


def _drushim_description(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "header", "footer", "nav"]):
        t.decompose()
    text = soup.get_text("\n", strip=True)
    start = text.find("תיאור משרה")
    if start >= 0:
        end_candidates = [text.find(m, start) for m in ("\nקטגוריה\n", "\nתחומים\n", "רוצה לקבל עדכונים")]
        end = min([e for e in end_candidates if e > start] or [len(text)])
        return text[start + len("תיאור משרה"):end].strip()
    jp = find_jsonld_jobposting(BeautifulSoup(html, "lxml"))
    return html_to_text(jp.get("description", "")) if jp else ""


def scan_drushim(ctx):
    http = ctx.http
    for q in C.BOARD_QUERIES:
        list_url = f"https://www.drushim.co.il/jobs/search/{quote(q)}/"
        st = ctx.status(list_url, "Drushim", "Drushim search API + עמוד משרה מלא")
        if http.out_of_time():
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        detail_fail = 0
        for page in range(MAX_PAGES):
            try:
                data = http.get_json(DRUSHIM_API, params={"searchterm": q, "page": page})
            except FetchError as e:
                (st.fail(str(e)) if page == 0 else st.partial(f"עצירה בעמוד {page + 1}: {e}"))
                break
            items = data.get("ResultList") or []
            for it in items:
                info, content, comp = it.get("JobInfo") or {}, it.get("JobContent") or {}, it.get("Company") or {}
                link = info.get("Link")
                if not link:
                    continue
                url = urljoin("https://www.drushim.co.il", link)
                title = content.get("Name") or ""
                company = comp.get("CompanyDisplayName") or comp.get("NameInHebrew") or ""
                if not rules.is_potential(title):
                    continue
                ctx.saw_company(company, "Drushim")
                if not ctx.first_time(url):
                    continue
                cities = [a.get("City") for a in content.get("Addresses") or [] if a.get("City")]
                zones = [z.get("NameInHebrew") for z in content.get("Zones") or [] if z.get("NameInHebrew")]
                location = ", ".join(dict.fromkeys(cities)) or " / ".join(zones)
                try:
                    desc = _drushim_description(http.get_text(url))
                except FetchError:
                    detail_fail += 1
                    continue
                if not desc:
                    detail_fail += 1
                    continue
                ctx.add(RawJob(title=title, company=company, source="Drushim", url=url, description=desc,
                               location=location, posted_raw=info.get("Date", ""),
                               updated_raw=info.get("JumpDate", ""), job_id=str(it.get("Code", "")),
                               experience_hint=(content.get("Experience") or {}).get("NameInHebrew", ""),
                               israeli_context=True, listing_url=st.url))
            nxt = data.get("NextPageNumber")
            total_pages = data.get("TotalPagesNumber") or 0
            if not items or nxt is None or nxt <= page or nxt >= total_pages:
                break
        if detail_fail:
            st.partial(f"{detail_fail} עמודי משרה לא נטענו")


# ----------------------------------------------------------------------------- JobMaster
def scan_jobmaster(ctx):
    http = ctx.http
    for q in C.BOARD_QUERIES:
        base = f"https://www.jobmaster.co.il/jobs/?q={quote_plus(q)}"
        st = ctx.status(base, "JobMaster", "JobMaster search (HTML) + עמוד משרה מלא")
        if http.out_of_time():
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        detail_fail, seen_ids = 0, set()
        for page in range(1, MAX_PAGES + 1):
            url = base if page == 1 else f"{base}&currPage={page}"
            try:
                html = http.get_text(url)
            except FetchError as e:
                (st.fail(str(e)) if page == 1 else st.partial(f"עצירה בעמוד {page}: {e}"))
                break
            soup = BeautifulSoup(html, "lxml")
            arts = soup.select("article.JobItem")
            ids = [a.get("id", "").replace("misra", "") for a in arts]
            if not arts or set(ids) <= seen_ids:
                break
            seen_ids.update(ids)
            for a in arts:
                jid = a.get("id", "").replace("misra", "")
                head = a.select_one("a.CardHeader")
                if not jid or not head:
                    continue
                title = head.get_text(" ", strip=True)
                comp = a.select_one(".CompanyNameLink")
                company = comp.get_text(" ", strip=True) if comp else ""
                job_url = f"https://www.jobmaster.co.il/jobs/checknum.asp?key={jid}"
                if not rules.is_potential(title):
                    continue
                ctx.saw_company(company, "JobMaster")
                if not ctx.first_time(job_url):
                    continue
                loc = a.select_one(".jobLocation")
                date_el = a.select_one(".paddingTop10px .Gray")
                try:
                    dsoup = BeautifulSoup(http.get_text(job_url), "lxml")
                except FetchError:
                    detail_fail += 1
                    continue
                body = dsoup.select_one(".article__jobBody") or dsoup.select_one(".jobDescription")
                if not body:
                    detail_fail += 1
                    continue
                for junk in body.select(".jobsCategories, .jobBtnContainer, script, style"):
                    junk.decompose()
                ctx.add(RawJob(title=title, company=company, source="JobMaster", url=job_url,
                               description=body.get_text("\n", strip=True),
                               location=loc.get_text(" ", strip=True) if loc else "",
                               posted_raw=date_el.get_text(" ", strip=True) if date_el else "", job_id=jid,
                               israeli_context=True, listing_url=st.url))
        if detail_fail:
            st.partial(f"{detail_fail} עמודי משרה לא נטענו")


# ----------------------------------------------------------------------------- AllJobs
def scan_alljobs(ctx):
    http = ctx.http
    for q in C.BOARD_QUERIES:
        base = ("https://www.alljobs.co.il/SearchResultsGuest.aspx?page={p}&position=&type=&freetxt="
                + quote_plus(q))
        st = ctx.status(base.format(p=1), "AllJobs", "AllJobs search (HTML) + עמוד משרה (JSON-LD)")
        if http.out_of_time():
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        detail_fail, seen_ids = 0, set()
        for page in range(1, MAX_PAGES + 1):
            try:
                html = http.get_text(base.format(p=page))
            except FetchError as e:
                (st.fail(str(e)) if page == 1 else st.partial(f"עצירה בעמוד {page}: {e}"))
                break
            soup = BeautifulSoup(html, "lxml")
            boxes = soup.select('div[id^="job-box-container"]')
            page_ids = []
            for b in boxes:
                a = b.select_one('a[href*="UploadSingle.aspx?JobID="]')
                t = b.select_one(".job-content-top-title")
                if not a or not t:
                    continue
                m = re.search(r"JobID=(\d+)", a["href"])
                if not m:
                    continue
                jid = m.group(1)
                page_ids.append(jid)
                card_title = t.get_text(" ", strip=True)
                if not rules.is_potential(card_title):
                    continue
                job_url = f"https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID={jid}"
                if not ctx.first_time(job_url):
                    continue
                date_el = b.select_one(".job-content-top-date")
                loc_el = b.select_one(".job-content-top-location")
                try:
                    dsoup = BeautifulSoup(http.get_text(job_url), "lxml")
                except FetchError:
                    detail_fail += 1
                    continue
                jp = find_jsonld_jobposting(dsoup)
                if not jp:
                    detail_fail += 1
                    continue
                org = jp.get("hiringOrganization") or {}
                company = org.get("name", "") if isinstance(org, dict) else str(org)
                ctx.saw_company(company, "AllJobs")
                loc = jsonld_location(jp)
                if loc_el:
                    loc_txt = re.sub(r"^(?:מיקום המשרה|Location)\s*:\s*", "", loc_el.get_text(" ", strip=True))
                    loc = loc_txt if loc_txt else loc
                ctx.add(RawJob(title=html_to_text(jp.get("title", "")) or card_title, company=company,
                               source="AllJobs", url=job_url, description=html_to_text(jp.get("description", "")),
                               location=loc, posted_raw=date_el.get_text(" ", strip=True) if date_el else "",
                               updated_raw=jp.get("datePosted", ""), job_id=jid, israeli_context=True,
                               listing_url=st.url))
            if not page_ids or set(page_ids) <= seen_ids:
                break
            seen_ids.update(page_ids)
        if detail_fail:
            st.partial(f"{detail_fail} עמודי משרה לא נטענו")


# ----------------------------------------------------------------------------- Indeed
def scan_indeed(ctx):
    """Indeed protects its pages with Cloudflare bot detection. We try, and report the result honestly."""
    http = ctx.http
    for q in ["data analyst", "analyst", "אנליסט"]:
        url = f"https://il.indeed.com/jobs?q={quote_plus(q)}&l=Israel&fromage={C.MAX_DAYS}"
        st = ctx.status(url, "Indeed", "Indeed search (HTML)")
        if http.out_of_time():
            st.fail("לא נסרק - הסתיים זמן הסריקה", "חלקי")
            continue
        try:
            html = http.get_text(url, retries=1)
        except FetchError as e:
            st.fail(f"{e} - האתר חוסם גישה אוטומטית (הגנת בוטים של Cloudflare)" if e.status in (401, 403)
                    else str(e), "לא נגיש" if e.status in (401, 403) else "נכשל")
            continue
        m = re.search(r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});', html, re.S)
        if not m:
            st.fail("לא נמצאו נתוני משרות בעמוד (ייתכן דף אימות/CAPTCHA)", "לא נגיש")
            continue
        try:
            results = json.loads(m.group(1))["metaData"]["mosaicProviderJobCardsModel"]["results"]
        except (ValueError, KeyError):
            st.fail("מבנה עמוד לא מוכר")
            continue
        for r in results:
            title, jk = r.get("displayTitle") or r.get("title", ""), r.get("jobkey")
            if not jk or not rules.is_potential(title):
                continue
            job_url = f"https://il.indeed.com/viewjob?jk={jk}"
            if not ctx.first_time(job_url):
                continue
            try:
                dsoup = BeautifulSoup(http.get_text(job_url, retries=1), "lxml")
            except FetchError:
                st.partial("חלק מעמודי המשרה לא נטענו")
                continue
            desc = dsoup.select_one("#jobDescriptionText")
            if not desc:
                continue
            ctx.add(RawJob(title=title, company=r.get("company", ""), source="Indeed", url=job_url,
                           description=desc.get_text("\n", strip=True), location=r.get("formattedLocation", ""),
                           posted_raw=r.get("formattedRelativeTime", ""), job_id=jk, israeli_context=True,
                           listing_url=st.url))
