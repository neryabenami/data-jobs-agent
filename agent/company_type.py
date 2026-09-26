"""Company type ("סוג חברה") for every job, and the report's row order by that type.

The type is decided per company (all jobs of one company share it), from the strongest signal found:
  1. hidden company / recruiting agency            -> "חברת השמה / חסוי"
  2. the company's name matches a known sector list
  3. the industry LinkedIn shows on the job page
  4. the job came from a tech recruiting system (Greenhouse, Lever, Comeet, ...) -> "הייטק"
  5. tech words in the job description (SaaS, startup, Series B, ...)           -> "הייטק"
  6. nothing recognized                             -> "אחר"
"""
import re

from .textutil import norm

HITECH = "הייטק"
BANKS = "בנקים"
FINANCE = "ביטוח ופיננסים"
CONSULTING = "ייעוץ ושירותי IT"
HEALTH = "בריאות ופארמה"
MEDIA = "תקשורת ומדיה"
RETAIL = "קמעונאות ומוצרי צריכה"
INDUSTRY = "תעשייה ביטחון ואנרגיה"
OTHER = "אחר"
AGENCY = "חברת השמה / חסוי"

# display order in the report (agreed with the user)
ORDER = [HITECH, BANKS, FINANCE, CONSULTING, HEALTH, MEDIA, RETAIL, INDUSTRY, OTHER, AGENCY]
RANK = {t: i for i, t in enumerate(ORDER)}

# Manual decisions for specific companies (exact company name, case-insensitive) - edit here to override.
OVERRIDES = {
    "papaya": HITECH,           # Papaya Gaming
    "passportcard": FINANCE,    # travel insurance
    "solaredge technologies": HITECH,
    "lemonade": HITECH,
    "checkout.com": HITECH,
    "one zero": BANKS,
}

# --- 1. hidden company / recruiting agency -----------------------------------------------------------
HIDDEN_RE = re.compile(r"חסוי|confidential|discreet|דיסקרטית|לא צוין|^חברה בתחום|^חברה מובילה|^company$|^$", re.I)
AGENCY_RE = re.compile(
    r"השמה|גיוס|משאבי אנוש|recruit|staffing|talent|headhunt|\bhr\b|jobs\.ai|jobgether|experis|manpower|"
    r"gotfriends|לין ביכלר|איילת אלבז|ענת רונן|יערה פיינר|אקספנד ג.?ובס|הלפרין|\bhms\b|דנאל|אשד משאבי|"
    r"nisha|נישה|ethosia|אתוסיה|adam milo|אדם מילוא|sqlink", re.I)

# --- 2. company name -> sector (checked in this order; first match wins) ------------------------------
NAME_RULES = [
    (BANKS, r"\bbank\b|בנק|hapoalim|הפועלים|leumi\b|לאומי\b|discount|דיסקונט|mizrahi|מזרחי|טפחות|fibi|"
            r"הבינלאומי|one zero|pepper|פפר|hsbc|citi\b|citibank|barclays|jp ?morgan|goldman|\bubs\b"),
    (FINANCE, r"ביטוח|insurance|הראל|harel|מגדל|migdal|הפניקס|phoenix|\bכלל\b|clal|מנורה|menora|איילון|ayalon|"
              r"הכשרה|hachshara|\bidi\b|ביטוח ישיר|\bcal\b|כאל|כרטיסי אשראי|isracard|ישראכרט|\bmax\b|מקס|"
              r"השקעות|investment|פסגות|psagot|מיטב|meitav|אלטשולר|altshuler|\bibi\b|מור השקעות|"
              r"loanwise|אשראי|credit|פיננסים|financ|\bice\b|intercontinental exchange|plus500|nasdaq|"
              r"capital markets|שוק ההון"),
    (CONSULTING, r"\bey\b|ernst|deloitte|דלויט|kpmg|pwc|\bbdo\b|accenture|mckinsey|\bbcg\b|bain|"
                 r"matrix|מטריקס|\bness\b|\baman\b|אמן|g[- ]?stat|ג.?י סטט|gtech|logica|אלעד|\belad\b|"
                 r"וואן פתרונות|one technologies|malam|מלם|yael group|קבוצת יעל|\bsela\b|bynet|doit|"
                 r"codevalue|ntu international|consult|ייעוץ|יועצים"),
    (HEALTH, r"קופת חולים|\bכללית\b|clalit|\bמכבי\b|maccabi|\bמאוחדת\b|meuhedet|\bלאומית\b|leumit|בית חולים|\bhospitals?\b|"
             r"medical center|המרכז הרפואי|שיבא|sheba|איכילוב|ichilov|teva|טבע|pharma|פארמה|novo nordisk|"
             r"pfizer|abbvie|roche|novartis|sanofi|\bmsd\b|merck"),
    (MEDIA, r"בזק|bezeq|סלקום|cellcom|פרטנר|partner communications|פלאפון|pelephone|\bhot\b|\byes\b|"
            r"קשת|keshet|רשת 13|reshet|ynet|ידיעות|וואלה|walla|\bכאן\b|media|מדיה|broadcast|telecom|"
            r"תקשורת|golan telecom|אינטרנט רימון|rimon internet"),
    (RETAIL, r"שופרסל|shufersal|סופר.?פארם|super-?pharm|פוקס|\bfox\b|קסטרו|castro|factory 54|אסם|osem|"
             r"nestl|נסטלה|nespresso|tnuva|תנובה|strauss|שטראוס|pepsico|coca|קוקה|\bcbc\b|ferrero|"
             r"kimberly|קימברלי|unilever|יוניליוור|procter|p&g|diageo|כלמוביל|edikted|retail|קמעונא|"
             r"רמי לוי|יוחננוף|ויקטורי|terminal ?x|טרמינל"),
    (INDUSTRY, r"אלביט|elbit|רפאל|rafael|התעשייה האווירית|israel aerospace|\biai\b|thales|chevron|enlight|"
               r"\bicl\b|\bפז\b|\bpaz\b|\bflex\b|defense|ביטחון|energy|אנרגיה|\boil\b|\bgas\b|חשמל|electric company|"
               r"manufactur|תעשי"),
    (HITECH, r"software|technolog|\btech\b|\.io\b|\.ai\b|\bai\b|cyber|סייבר|security|data|cloud|games|"
             r"gaming|studios|labs|networks|similarweb|wix|monday|melio|appsflyer|axonius|check ?point|"
             r"cato|palo ?alto|paloaltonetworks|cyberark|\bwiz\b|jfrog|lightricks|moon active|playtika|"
             r"plarium|playstudios|scopely|voyantis|\bmize\b|placer|brandlight|connecteam|honeybook|hibob|"
             r"fiverr|payoneer|global-e|riskified|forter|\bgong\b|\btorq\b|nexxen|veeva|viber|play perfect|"
             r"\brounds\b|fetcherr|modellama|base44|cast ai|clover|\bflare\b|medulla|mylo|\bltx\b|shipin|"
             r"chainalysis|audiocodes|autods|aidoc|\bgett\b|nvidia|intel\b|google|microsoft|\bmeta\b|amazon|"
             r"apple|salesforce|oracle|\bsap\b|cisco|\bibm\b|mobileye|amdocs|\bnice\b|verint|sapiens|"
             r"taboola|outbrain|payPal|ebay|intuit|applied materials|\bkla\b|palantir|fortinet|qodo|"
             r"autofleet|explorium|trivago|hippo|nift|tripledot|product madness|dynamic yield|shavit software|"
             r"peak innovation|pulsenmore|paragon"),
]
NAME_RES = [(t, re.compile(p, re.I)) for t, p in NAME_RULES]

# --- 3. LinkedIn "Industries" field -> sector -----------------------------------------------------------
INDUSTRY_RULES = [
    (AGENCY, r"staffing|recruit|human resources services"),
    (BANKS, r"\bbanking\b"),
    (FINANCE, r"insurance|financial services|investment|capital markets|venture capital|credit"),
    (CONSULTING, r"it services|it consulting|business consulting|management consulting|accounting|"
                 r"outsourcing|professional services"),
    (HEALTH, r"\bhospitals?\b|health care|healthcare|pharmaceutical|medical|biotech|wellness"),
    (MEDIA, r"telecommunication|broadcast|media|newspaper|entertainment providers|online audio"),
    (RETAIL, r"retail|food|beverage|consumer goods|consumer services|apparel|fashion|wholesale|"
             r"motor vehicle|personal care"),
    (INDUSTRY, r"defense|aviation|aerospace|manufacturing|oil|energy|utilities|renewable|mining|chemical|"
               r"construction|semiconductor manufacturing"),
    (HITECH, r"software|internet|information technology|computer|technology|network security|games|"
             r"semiconductor|data infrastructure|information services|e-learning|marketplace"),
]
INDUSTRY_RES = [(t, re.compile(p, re.I)) for t, p in INDUSTRY_RULES]

# --- 4. recruiting systems used almost only by tech companies ------------------------------------------
TECH_ATS_RE = re.compile(r"greenhouse\.io|lever\.co|ashbyhq\.com|comeet\.co|workable\.com|smartrecruiters\.com|"
                         r"myworkdayjobs\.com", re.I)

# --- 5. tech words in the description (at least two different ones) ------------------------------------
TECH_WORDS_RE = [re.compile(p, re.I) for p in (
    r"\bsaas\b", r"start-?up", r"סטארט.?אפ", r"series [a-e]\b", r"סבב גיוס", r"\bb2b\b", r"cyber", r"סייבר",
    r"fintech", r"פינטק", r"our platform", r"the platform", r"product-led", r"tech company", r"חברת הייטק",
    r"unicorn", r"funding", r"\bvc\b")]

# signal strength: a stronger signal for the same company wins
STRENGTH = {"override": 6, "hidden": 5, "name": 4, "industry": 3, "ats": 2, "description": 1, "none": 0}


def classify(company, industry="", listing_url="", url="", description=""):
    """Return (type, strength_name) for one job."""
    name = (company or "").strip()
    low = name.lower()
    if low in OVERRIDES:
        return OVERRIDES[low], "override"
    if HIDDEN_RE.search(name) or AGENCY_RE.search(name):
        return AGENCY, "hidden"
    n = norm(name)
    for t, rx in NAME_RES:
        if rx.search(name) or rx.search(n):
            return t, "name"
    for t, rx in INDUSTRY_RES:
        if industry and rx.search(industry):
            return t, "industry"
    if TECH_ATS_RE.search(listing_url or "") or TECH_ATS_RE.search(url or ""):
        return HITECH, "ats"
    text = description or ""
    if sum(1 for rx in TECH_WORDS_RE if rx.search(text)) >= 2:
        return HITECH, "description"
    return OTHER, "none"


def company_map(pairs, key_fn):
    """pairs: [(job, raw)] -> {company_key: type}, keeping the strongest signal per company."""
    best = {}
    for job, raw in pairs:
        t, s = classify(raw.company, getattr(raw, "industry", ""), raw.listing_url, raw.url, raw.description)
        k = key_fn(job.company)
        if k not in best or STRENGTH[s] > best[k][1]:
            best[k] = (t, STRENGTH[s])
    return {k: v[0] for k, v in best.items()}


def sort_jobs(jobs):
    """Stable sort by the agreed type order; the existing order (newest first) is kept inside each type."""
    return sorted(jobs, key=lambda j: RANK.get(j.company_type or OTHER, RANK[OTHER]))
