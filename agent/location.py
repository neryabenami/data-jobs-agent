"""Stage 5: country & location filter."""
import re

from . import config as C
from .textutil import norm


def _terms_re(terms):
    normed = sorted({norm(t) for t in terms if norm(t)}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in normed) + r")(?!\w)")


ISRAEL_RE = _terms_re(C.ISRAEL_TERMS)
EXCLUDED_RES = {label: _terms_re(terms) for label, terms in C.EXCLUDED_LOCATIONS.items()}
if C.TREAT_HAIFA_AS_NORTH:
    EXCLUDED_RES["אזור הצפון / North"] = _terms_re(C.EXCLUDED_LOCATIONS["אזור הצפון / North"] + C.HAIFA_TERMS)
FOREIGN_RE = _terms_re(C.FOREIGN_TERMS)
US_STATE_RE = re.compile(C.FOREIGN_US_STATE_RE)
HEBREW_RE = re.compile(r"[א-ת]")  # a location written in Hebrew is an Israeli location
BARE_REGION = {"צפון": "אזור הצפון / North", "הצפון": "אזור הצפון / North", "north": "אזור הצפון / North",
               "דרום": "אזור הדרום / South", "הדרום": "אזור הדרום / South", "south": "אזור הדרום / South"}
GENERIC_LOC_RE = re.compile(r"^(?:remote|hybrid|on ?site|onsite|anywhere|multiple locations|various|flexible|"
                            r"more than one|home based|work from home|מהבית|היברידי|גמיש|כל הארץ|מספר מיקומים)$")
# Israel-wide "all areas" should not be read as excluded just because it lists every region
NATIONWIDE_RE = re.compile(r"כל הארץ|all israel|israel wide|nationwide")
# Israeli context clues inside a description or URL (used only when the location field is missing/generic)
DESC_ISRAEL_RE = re.compile(r"(?<!\w)(?:israel|ישראל|tel aviv|תל אביב|herzliya|הרצליה|petah tikva|פתח תקווה|"
                            r"ramat gan|רמת גן|ra'?anana|רעננה|netanya|נתניה|hod hasharon|הוד השרון|"
                            r"kfar saba|כפר סבא|israeli|ישראלי)(?!\w)", re.I)
ISRAEL_URL_RE = re.compile(r"(?:\.co\.il|\.org\.il|\.gov\.il|/il/|/israel|[?&]country=il|il\.linkedin\.com|lang=he|/he/)", re.I)


def title_says_abroad(title):
    """'Analyst (Bangkok Based, Relocation provided)' - the title itself places the job outside Israel."""
    n = norm(title)
    if ISRAEL_RE.search(n) and not FOREIGN_RE.search(n):
        return False
    return bool(FOREIGN_RE.search(n) or re.search(r"relocation|רילוקיישן", title or "", re.I))


def _split_locations(loc):
    parts = re.split(r"\s*(?:\||;|/| or | או |\n)\s*", loc or "")
    return [p for p in (x.strip() for x in parts) if p]


def classify(location, description="", url="", israeli_context=False):
    """Return (decision, display_location, note).

    decision: 'israel' (show) | 'unknown' (show, needs verification) | 'excluded' | 'foreign'
    """
    loc = (location or "").strip()
    nloc = norm(loc)
    if nloc in BARE_REGION:
        return "excluded", loc, BARE_REGION[nloc]

    parts = _split_locations(loc) or ([loc] if loc else [])
    allowed_il, excluded_hits, foreign_hits = [], [], []
    for p in parts:
        np_ = norm(p)
        if not np_ or GENERIC_LOC_RE.match(np_) or np_ in ("israel", "ישראל", "il"):
            continue
        if np_ in BARE_REGION:
            excluded_hits.append(BARE_REGION[np_])
            continue
        hit = next((lbl for lbl, rx in EXCLUDED_RES.items() if rx.search(np_)), None)
        if hit and not NATIONWIDE_RE.search(np_):
            excluded_hits.append(hit)
        elif ISRAEL_RE.search(np_) or HEBREW_RE.search(p):
            allowed_il.append(p)
        elif FOREIGN_RE.search(np_) or US_STATE_RE.search(p):
            foreign_hits.append(p)

    loc_says_israel = bool(ISRAEL_RE.search(nloc)) or nloc in ("il",)
    if allowed_il:
        return "israel", loc, ""
    if excluded_hits:
        return "excluded", loc, excluded_hits[0]
    if foreign_hits and not loc_says_israel:
        return "foreign", loc, "מחוץ לישראל"
    if loc_says_israel:
        return "israel", loc, ""

    # Location missing or generic ("Remote", "Hybrid") or unrecognized - infer from context (section 7)
    desc_il = bool(DESC_ISRAEL_RE.search(description or ""))
    url_il = bool(ISRAEL_URL_RE.search(url or ""))
    if israeli_context or desc_il or url_il:
        shown = loc if loc and not GENERIC_LOC_RE.match(nloc) else ("ישראל" + (f" ({loc})" if loc else ""))
        return "israel", shown, "ישראל הוסקה מההקשר"
    if loc and not GENERIC_LOC_RE.match(nloc):
        # a concrete place we do not recognize as Israeli and with no Israeli context -> treat as abroad
        return "foreign", loc, "מיקום לא ישראלי"
    if FOREIGN_RE.search(norm(description or "")[:600]):
        return "foreign", loc, "הקשר מצביע על חו\"ל"
    return "unknown", C.UNKNOWN, ""
