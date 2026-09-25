"""Stages 1, 3, 4 of the spec: title relevance, mandatory keyword, role essence & exclusions."""
import re

from . import config as C
from .textutil import norm, norm_he_gender


def _norm_title(t):
    t = norm_he_gender(t or "")
    t = norm(t)
    t = re.sub(r"\b(?:sr|snr|jr|senior|junior|lead|principal|staff|mid|mid level|entry level|head)\b", " ", t)
    t = re.sub(r"\b(?:bi)\b", "bi", t)
    return re.sub(r"\s+", " ", t).strip()


def _phrase_re(phrases):
    normed = sorted({_norm_title(p) for p in phrases if _norm_title(p)}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(p) for p in normed) + r")(?!\w)")


LISTED_RE = _phrase_re(C.TITLES_EN + C.TITLES_HE)
EXCLUDED_RE = _phrase_re(C.EXCLUDED_ROLES)
ANALYST_WORD_RE = re.compile(r"(?<!\w)(?:analyst|analytics|אנליסט|דאטה אנליסט|מנתח(?: ?ת)? נתונים)(?!\w)")
# an analyst *role* word - required for a title to count as "combined" (e.g. "BI Developer / Data Analyst")
ANALYST_ROLE_RE = re.compile(r"(?<!\w)(?:analyst|אנליסט|מנתח(?: ?ת)? נתונים)(?!\w)")
CANDIDATE_BLOCK_RE = re.compile(C.CANDIDATE_BLOCK_TITLE, re.I)
CANDIDATE_RE = re.compile(C.CANDIDATE_TITLE_HINTS, re.I)
KEYWORD_RES = {k: re.compile(v, re.I) for k, v in C.KEYWORDS.items()}
if C.USE_HEBREW_KEYWORD_EQUIVALENTS:
    KEYWORD_RES.update({k: re.compile(v) for k, v in C.KEYWORDS_HE.items()})
ANALYTICS_RES = [re.compile(p, re.I) for p in C.ANALYTICS_SIGNALS]
ENGINEERING_RES = [re.compile(p, re.I) for p in C.ENGINEERING_SIGNALS]
# pure non-analytics titles that are never "analytics by essence"
NON_ANALYTICS_TITLE_RE = re.compile(
    r"(?<!\w)(?:engineer|developer|מפתח|מהנדס|scientist|מדען|architect|ארכיטקט|devops|qa|tester|"
    r"recruiter|מגייס|sales representative|account executive|nurse|אחות|teacher|מורה|driver|נהג)(?!\w)")


def title_class(title):
    """Return one of: 'listed', 'variant', 'combined', 'excluded', 'candidate', None (not a potential job)."""
    t = _norm_title(title)
    excluded = bool(EXCLUDED_RE.search(t))
    rest = EXCLUDED_RE.sub(" ", t)  # "Analytics Engineer" must not count as an analyst title
    listed = bool(LISTED_RE.search(rest))
    analystish = bool(ANALYST_WORD_RE.search(rest))
    if excluded and (listed or ANALYST_ROLE_RE.search(rest)):
        return "combined"
    if excluded:
        return "excluded"
    if listed:
        return "listed"
    if analystish:
        return "variant"
    raw_t = norm(norm_he_gender(title or ""))  # before "lead/head/senior" are stripped
    if CANDIDATE_RE.search(t) and not NON_ANALYTICS_TITLE_RE.search(t) and not CANDIDATE_BLOCK_RE.search(raw_t):
        return "candidate"
    return None


def is_potential(title):
    """Stage 1: should this job's full page be opened and checked?"""
    return title_class(title) in ("listed", "variant", "combined", "candidate")


def find_keywords(description):
    """Stage 3: mandatory keywords, searched case-insensitively inside the description only."""
    found = []
    text = description or ""
    for name, rx in KEYWORD_RES.items():
        if rx.search(text):
            found.append(name)
    # "SQL Queries" implies "SQL"; keep the list short and readable
    if "SQL Queries" in found and "SQL" in found:
        found.remove("SQL Queries")
    return found


def _score(res, text):
    return sum(1 for rx in res if rx.search(text))


def essence(title, description):
    """Stage 4: is Data Analytics a central part of the role? Returns (ok, reason_or_rejection)."""
    cls = title_class(title)
    text = (description or "").lower()
    ana = _score(ANALYTICS_RES, text)
    eng = _score(ENGINEERING_RES, text)
    if cls == "excluded":
        return False, "תפקיד החרגה לפי הכותרת"
    if cls == "combined":
        if ana >= 3 and ana >= eng:
            return True, "כותרת משולבת - עיקר העבודה אנליטי"
        return False, "כותרת משולבת - עיקר העבודה פיתוח/הנדסה"
    if cls == "listed":
        if eng >= 6 and eng > 2 * ana:
            return False, "עיקר התפקיד הנדסי למרות הכותרת"
        return True, "כותרת תואמת"
    if cls == "variant":
        if ana >= 3 and ana >= eng:
            return True, "וריאציה של כותרת אנליטית"
        return False, "וריאציה אנליטית ללא מהות אנליטית מספקת בתיאור"
    if cls == "candidate":
        if ana >= 5 and ana > 1.5 * eng and eng <= 3:
            return True, "כותרת לא סטנדרטית - מהות התפקיד Data Analytics"
        return False, "כותרת לא סטנדרטית ללא מהות אנליטית מרכזית"
    return False, "כותרת לא רלוונטית"


EXPERIENCE_RES = [
    re.compile(r"(\d{1,2}\s?(?:-|–|to)\s?\d{1,2}\+?\s*(?:years?|yrs?))", re.I),
    re.compile(r"(\d{1,2}\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+\w+){0,4}?\s+experience)", re.I),
    re.compile(r"((?:at least|minimum(?: of)?|min\.?)\s+\d{1,2}\+?\s*(?:years?|yrs?))", re.I),
    re.compile(r"(\d{1,2}\+?\s*(?:years?|yrs?))", re.I),
    re.compile(r"(ניסיון\s+של\s+(?:\d{1,2}|שנה|שנתיים|שלוש|ארבע|חמש)[^\n.,]{0,25})"),
    re.compile(r"((?:\d{1,2}|שנתיים)\+?\s*(?:-\s*\d{1,2}\s*)?שנות\s+ניסיון[^\n.,]{0,20})"),
    re.compile(r"(ניסיון\s+(?:מוכח\s+)?(?:של\s+)?(?:לפחות\s+)?(?:\d{1,2}|שנה|שנתיים)\s+שנ(?:ים|ות|ה)?[^\n.,]{0,15})"),
    re.compile(r"(ללא\s+ניסיון|אין\s+צורך\s+בניסיון|no (?:prior )?experience (?:required|needed))", re.I),
]


def extract_experience(description, hint=""):
    if hint:
        return hint.strip()
    text = description or ""
    for rx in EXPERIENCE_RES:
        m = rx.search(text)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:80]
    return ""
