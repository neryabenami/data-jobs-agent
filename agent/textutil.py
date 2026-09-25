"""Text helpers: HTML -> clean text, normalization, JSON-LD extraction, main-content extraction."""
import html
import json
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from bs4 import BeautifulSoup

NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]
NOISE_ATTR_RE = re.compile(
    r"(^|[\s_-])(nav|navbar|menu|footer|header|cookie|breadcrumb|related|similar|recommend|share|social|"
    r"sidebar|banner|popup|modal|newsletter|more-jobs|other-jobs|jobs-list)([\s_-]|$)", re.I)


def html_to_text(fragment):
    if not fragment:
        return ""
    if "<" not in fragment and "&" in fragment:
        fragment = html.unescape(fragment)
    if "<" not in fragment:
        return re.sub(r"[ \t]+", " ", fragment).strip()
    soup = BeautifulSoup(fragment, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{2,}", "\n", text)


def norm(s):
    """Lower-case, unify separators (/ - & and , |) and whitespace. Used for title/location matching."""
    s = (s or "").lower()
    s = s.replace("‏", " ").replace("‎", " ").replace("\xa0", " ")
    s = re.sub(r"[\"'`׳״]", "", s)
    s = re.sub(r"[/\\\-–—&_,|()\[\]:;+.!?]", " ", s)
    s = re.sub(r"\band\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_he_gender(s):
    """Fold Hebrew feminine / slashed forms to the masculine base: אנליסטית / אנליסט/ית -> אנליסט."""
    s = re.sub(r"\s?[/.\\]\s?(?:ית|ה|ת|ות|ים)(?![\u05d0-\u05ea])", "", s)
    s = re.sub(r"(אנליסט)ית\b", r"\1", s)
    s = re.sub(r"(פיננסי|עסקי)ת\b", r"\1", s)
    return s


def find_jsonld_jobposting(soup):
    for sc in soup.select('script[type="application/ld+json"]'):
        raw = sc.string or sc.get_text() or ""
        try:
            data = json.loads(raw.strip())
        except ValueError:
            try:
                data = json.loads(re.sub(r"[\x00-\x1f]", " ", raw.strip()))
            except ValueError:
                continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                t = d.get("@type")
                if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                    return d
                if "@graph" in d:
                    stack.extend(d["@graph"] if isinstance(d["@graph"], list) else [d["@graph"]])
            elif isinstance(d, list):
                stack.extend(d)
    return None


def jsonld_location(jp):
    locs = jp.get("jobLocation") or []
    if isinstance(locs, dict):
        locs = [locs]
    parts = []

    def as_text(v):
        if isinstance(v, dict):
            return str(v.get("name", "") or "")
        if isinstance(v, list):
            return ", ".join(as_text(x) for x in v if x)
        return str(v or "")

    for loc in locs:
        if isinstance(loc, str):
            parts.append(loc)
            continue
        if not isinstance(loc, dict):
            continue
        addrs = loc.get("address") or {}
        for addr in (addrs if isinstance(addrs, list) else [addrs]):
            if isinstance(addr, str):
                parts.append(addr)
                continue
            if not isinstance(addr, dict):
                continue
            city = as_text(addr.get("addressLocality"))
            region = as_text(addr.get("addressRegion"))
            country = as_text(addr.get("addressCountry"))
            if country in ("IL", "ISR"):
                country = "Israel"
            parts.append(", ".join(p for p in [city, region, country] if p))
    if jp.get("jobLocationType") == "TELECOMMUTE" and not parts:
        parts.append("Remote")
    return " | ".join(p for p in parts if p)


def main_content_text(soup):
    """Best-effort job-description text: drop site chrome (menus, header, footer, related jobs)."""
    for t in soup(NOISE_TAGS):
        t.decompose()
    for el in soup.find_all(True):
        if el.attrs is None:
            continue
        attrs = " ".join([el.get("id") or ""] + list(el.get("class") or []))
        if attrs and NOISE_ATTR_RE.search(attrs) and el.name not in ("body", "html", "main", "article"):
            el.decompose()
    candidates = soup.select(
        "[class*=description], [class*=Description], [id*=description], [class*=job-body], "
        "[class*=jobBody], [class*=posting], main, article, [role=main]")
    best = max(candidates, key=lambda e: len(e.get_text(" ", strip=True)), default=None)
    node = best if best is not None and len(best.get_text(strip=True)) > 200 else soup.body or soup
    return re.sub(r"\n{2,}", "\n", node.get_text("\n", strip=True))


TRACKING_PARAMS = re.compile(r"^(utm_|ref|refid|trk|tracking|position|pagenum|gh_src|source|src|lever-|fbclid|gclid)", re.I)


def canonical_url(url):
    try:
        p = urlparse(url.strip())
    except ValueError:
        return url
    host = p.netloc.lower()
    if host.endswith("linkedin.com"):
        m = re.search(r"(\d{8,})", p.path) or re.search(r"currentJobId=(\d+)", p.query)
        if m:
            return f"https://www.linkedin.com/jobs/view/{m.group(1)}"
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False) if not TRACKING_PARAMS.match(k)]
    path = re.sub(r"/+$", "", p.path) or "/"
    return urlunparse(("https", host.replace("www.", "", 1) if host.startswith("www.") else host, path, "",
                       urlencode(sorted(q)), ""))


def site_name(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    known = {
        "linkedin.com": "LinkedIn", "indeed.com": "Indeed", "jobmaster.co.il": "JobMaster",
        "drushim.co.il": "Drushim", "alljobs.co.il": "AllJobs", "greenhouse.io": "Greenhouse",
        "lever.co": "Lever", "ashbyhq.com": "Ashby", "workable.com": "Workable",
        "smartrecruiters.com": "SmartRecruiters", "comeet.com": "Comeet", "comeet.co": "Comeet",
        "gotfriends.co.il": "GotFriends", "sqlink.com": "SQLink", "jobnet.co.il": "JobNet",
        "jobkarov.com": "JobKarov", "secrettelaviv.com": "Secret Tel Aviv", "bing.com": "Bing",
    }
    for dom, name in known.items():
        if host == dom or host.endswith("." + dom):
            return name
    host = re.sub(r"^(www|careers|jobs|career)\.", "", host)
    return host
