"""Central configuration: every list and threshold defined in the agent spec lives here."""

TIMEZONE = "Asia/Jerusalem"
SEND_HOUR = 10            # report is sent at 10:00 Asia/Jerusalem, never earlier
SCAN_DEADLINE = (9, 40)   # stop scanning at 09:40 so the report is ready by 10:00
LATE_RUN_SCAN_MINUTES = 35  # scan budget when a run starts late (after the deadline)
MAX_DAYS = 20             # 20-day freshness rule

UNKNOWN = "לא ידוע / דורש אימות"
UNKNOWN_DATE = "תאריך לא ידוע / דורש אימות"

# ---------------------------------------------------------------------------
# Stage 1 - titles (section 3.1 / 3.2)
# ---------------------------------------------------------------------------
TITLES_EN = [
    # Data Analytics
    "Data Analyst", "Senior Data Analyst", "Junior Data Analyst", "Lead Data Analyst",
    "Data Analytics Analyst", "Data & Analytics Analyst", "Data and Analytics Analyst", "Analytics Analyst",
    # BI
    "BI Analyst", "Business Intelligence Analyst", "BI Data Analyst",
    # Business
    "Business Data Analyst", "Business Analytics Analyst", "Business Analyst",
    # Product
    "Product Data Analyst", "Product Analyst", "Product Analytics Analyst",
    # Marketing
    "Marketing Data Analyst", "Marketing Analyst", "Marketing Analytics Analyst",
    # Growth
    "Growth Data Analyst", "Growth Analyst", "Growth Analytics Analyst",
    # Digital
    "Digital Data Analyst", "Digital Analyst", "Digital Analytics Analyst",
    # Web
    "Web Analyst", "Web Analytics Analyst",
    # Performance
    "Performance Analyst", "Performance Data Analyst", "Business Performance Analyst",
    # CRM / Customer
    "CRM Analyst", "CRM Data Analyst", "Customer Analyst", "Customer Data Analyst",
    "Customer Analytics Analyst", "Customer Insights Analyst",
    # Operations
    "Operations Analyst", "Operations Data Analyst", "Operational Analyst", "Operational Data Analyst",
    # Sales / Revenue
    "Sales Analyst", "Sales Data Analyst", "Sales Analytics Analyst",
    "Revenue Analyst", "Revenue Data Analyst", "Revenue Analytics Analyst",
    # Financial / Risk / Fraud / Credit
    "Financial Analyst", "Financial Data Analyst", "Risk Analyst", "Risk Data Analyst",
    "Risk Analytics Analyst", "Fraud Analyst", "Fraud Data Analyst", "Fraud Analytics Analyst",
    "Credit Analyst", "Credit Data Analyst", "Credit Risk Analyst",
    # Retail / Pricing / Monetization
    "Retail Analyst", "Retail Data Analyst", "Pricing Analyst", "Pricing Data Analyst",
    "Monetization Analyst", "Monetization Data Analyst",
    # Insights / Research / Strategy
    "Insights Analyst", "Data Insights Analyst", "Business Insights Analyst", "Research Analyst",
    "Data Research Analyst", "Strategy Analyst", "Strategic Data Analyst", "Decision Analyst",
    "Decision Analytics Analyst",
    # Experimentation / Funnel / Retention / Acquisition
    "Experimentation Analyst", "Experiment Analyst", "Funnel Analyst", "Conversion Analyst",
    "Conversion Data Analyst", "Retention Analyst", "Retention Data Analyst",
    "User Acquisition Analyst", "UA Analyst",
]

TITLES_HE = [
    "דאטה אנליסט", "דאטה אנליסטית", "אנליסט דאטה", "אנליסטית דאטה", "אנליסט נתונים",
    "אנליסטית נתונים", "אנליסט/ית נתונים", "אנליסט/ית דאטה",
    "אנליסט BI", "אנליסטית BI", "אנליסט/ית BI", "אנליסט בינה עסקית", "אנליסטית בינה עסקית",
    "אנליסט עסקי", "אנליסטית עסקית", "אנליסט מוצר", "אנליסטית מוצר", "אנליסט שיווק", "אנליסטית שיווק",
    "אנליסט דיגיטל", "אנליסטית דיגיטל", "אנליסט ביצועים", "אנליסטית ביצועים",
    "אנליסט ביצועים עסקיים", "אנליסטית ביצועים עסקיים",
    "אנליסט CRM", "אנליסטית CRM", "אנליסט לקוחות", "אנליסטית לקוחות",
    "אנליסט תפעול", "אנליסטית תפעול", "אנליסט מכירות", "אנליסטית מכירות", "אנליסט הכנסות", "אנליסטית הכנסות",
    "אנליסט פיננסי", "אנליסטית פיננסית", "אנליסט סיכונים", "אנליסטית סיכונים", "אנליסט אשראי",
    "אנליסטית אשראי", "אנליסט הונאות", "אנליסטית הונאות",
    "אנליסט תמחור", "אנליסטית תמחור", "אנליסט אסטרטגיה", "אנליסטית אסטרטגיה", "אנליסט מחקר",
    "אנליסטית מחקר", "אנליסט תובנות", "אנליסטית תובנות",
]

# Search queries per source. LinkedIn supports boolean OR, so titles are grouped.
LINKEDIN_QUERY_GROUP_SIZE = 7
LINKEDIN_EXTRA_QUERIES = ["analyst", "analytics", "אנליסט", "אנליסטית", "אנליסט/ית"]
BOARD_QUERIES = [  # Israeli boards (Drushim / JobMaster / AllJobs / generic boards)
    "data analyst", "analyst", "BI analyst", "business analyst", "product analyst",
    "marketing analyst", "business intelligence", "analytics", "insights analyst",
    "risk analyst", "fraud analyst", "operations analyst", "financial analyst", "sales analyst",
    "אנליסט", "אנליסטית", "אנליסט נתונים", "דאטה אנליסט", "אנליסט BI", "אנליסט עסקי", "בינה עסקית",
]

# ---------------------------------------------------------------------------
# Stage 3 - mandatory keywords (case-insensitive, description only)
# ---------------------------------------------------------------------------
KEYWORDS = {
    "SQL": r"(?<![a-z])(?:t-|pl/|ms|my|postgre|spark\s?|advanced\s|complex\s)?sql(?![a-z])",
    "SQL Queries": r"sql\s+quer(?:y|ies)",
    "Querying": r"(?<![a-z])querying(?![a-z])",
    "Tableau": r"(?<![a-z])tableau(?![a-z])",
    "Power BI": r"power\s?-?bi(?![a-z])",
    "Looker": r"(?<![a-z])looker(?![a-z])",
    "Qlik": r"(?<![a-z])qlik(?:\s?sense|view)?(?![a-z])",
    "Python": r"(?<![a-z])python(?![a-z])",
    "Pandas": r"(?<![a-z])pandas(?![a-z])",
    "Database": r"(?<![a-z])databases?(?![a-z])",
    "Data Warehouse": r"data\s?-?warehous(?:e|es|ing)",
    "DWH": r"(?<![a-z])dwh(?![a-z])",
    "BigQuery": r"big\s?query",
    "Snowflake": r"(?<![a-z])snowflake(?![a-z])",
    "Redshift": r"(?<![a-z])redshift(?![a-z])",
    "Teradata": r"(?<![a-z])teradata(?![a-z])",
}
# Direct Hebrew translations of the keywords above (same keyword, different language).
# Set to False to require the English spelling only.
USE_HEBREW_KEYWORD_EQUIVALENTS = True
KEYWORDS_HE = {
    "Database (מסד/בסיס נתונים)": r"(?:מסד|מסדי|בסיס|בסיסי)\s?-?נתונים",
    "Data Warehouse (מחסן נתונים)": r"מחסני?\s?נתונים",
    "Python (פייתון)": r"פייתון|פיתון",
    "Querying (שאילתות)": r"שאילתות|שאילתא|שאילתה",
}

# ---------------------------------------------------------------------------
# Stage 4 - exclusions (section 6.1)
# ---------------------------------------------------------------------------
EXCLUDED_ROLES = [
    "data engineer", "analytics engineer", "software engineer", "backend engineer",
    "back end engineer", "frontend engineer", "front end engineer", "full stack engineer",
    "fullstack engineer", "machine learning engineer", "ml engineer", "data scientist",
    "dba", "database administrator", "bi developer", "etl developer", "data architect",
    "software developer", "backend developer", "frontend developer", "full stack developer",
    "מהנדס נתונים", "מהנדס דאטה", "מהנדסת נתונים", "מהנדסת דאטה", "דאטה אינג'ינר",
    "מפתח bi", "מפתחת bi", "מפתח etl", "מפתחת etl", "מפתח תוכנה", "מפתחת תוכנה",
    "מדען נתונים", "מדענית נתונים", "דאטה סיינטיסט", "מנהל מסדי נתונים", "ארכיטקט נתונים",
    "data science", "machine learning", "ai engineer", "ai developer", "ai researcher", "מדעי הנתונים",
    "research scientist", "applied scientist", "bi engineer", "data platform", "data infrastructure",
    # analyst titles whose core is not Data Analytics (section 6: analytics must be central to the role)
    "security analyst", "soc analyst", "malware analyst", "threat analyst", "threat intelligence analyst",
    "cyber analyst", "cyber security analyst", "cybersecurity analyst", "system analyst", "systems analyst",
    "qa analyst", "test analyst", "network analyst", "it analyst", "support analyst", "vulnerability analyst",
    "incident response analyst", "מנתח מערכות", "מנתחת מערכות", "אנליסט סייבר", "אנליסט אבטחת מידע",
    "analytics architect", "bi architect", "solutions architect", "solution architect",
    "data engineering", "noc analyst", "אנליסט noc", "security researcher", "threat researcher",
    "product manager", "project manager", "program manager", "מנהל מוצר", "מנהלת מוצר",
    "systems analysis", "system analysis", "failure analysis", "timing analysis", "threat hunter",
    "security operations", "security operations center analyst", "solutions architecture",
    "solution engineer", "solutions engineer", "sales engineer", "pre sales", "presales",
]
# Non-standard titles (not an analyst title) are accepted by essence only if they are not management /
# research / security roles - those are not Data Analyst positions even when the text is analytical.
CANDIDATE_BLOCK_TITLE = (
    r"\b(?:lead|leader|head|director|vp|vice president|chief|manager|management|researcher|research|security|"
    r"cyber|principal engineer|owner)\b|ראש צוות|ראש תחום|מנהל|מנהלת|חוקר|חוקרת|סייבר|אבטחת"
)

# Titles that may describe an analytics role even if not in the list (stage 1, 3.4)
CANDIDATE_TITLE_HINTS = (
    r"analyst|analytics|analysis|אנליס|ניתוח|נתונים|דאטה|\bdata\b|\bbi\b|business intelligence|"
    r"בינה עסקית|insight|תובנות|reporting|דוחות|metrics|kpi|statistic|סטטיסט|economist|כלכלן|"
    r"researcher|מחקר|fp&a|fpa"
)

# Essence scoring (section 6) - signals of analytics work vs engineering / science work
ANALYTICS_SIGNALS = [
    r"analy[sz]", r"analytic", r"insight", r"dashboard", r"report", r"\bkpis?\b", r"metrics?",
    r"a/b", r"experiment", r"trend", r"visuali[sz]", r"ad[- ]hoc", r"stakeholder", r"business question",
    r"data[- ]driven", r"recommendation", r"\bsql\b", r"tableau", r"power ?bi", r"looker", r"qlik",
    r"excel", r"funnel", r"segmentation", r"forecast", r"deep dive",
    r"ניתוח", r"תובנות", r"דוחות", r"דו\"חות", r"דשבורד", r"דאשבורד", r"מדדים", r"אנליזה",
    r"הסקת מסקנות", r"ויזואליזציה", r"מגמות", r"ממשקי\s?משתמש\s?עסקיים", r"המלצות",
]
ENGINEERING_SIGNALS = [
    r"pipelines?", r"\betl\b", r"\belt\b", r"airflow", r"\bspark\b", r"kafka", r"data infrastructure",
    r"data platform", r"data lake", r"microservice", r"\bbackend\b", r"back-end", r"front[- ]?end",
    r"full[- ]?stack", r"ci/cd", r"kubernetes", r"docker", r"terraform", r"\bjava\b", r"\bscala\b",
    r"c\+\+", r"golang", r"node\.?js", r"\breact\b", r"machine learning models?", r"train(?:ing)? models",
    r"deep learning", r"neural", r"mlops", r"model deployment", r"\bssis\b", r"informatica",
    r"datastage", r"software development", r"production code", r"distributed systems",
    r"build(?:ing)? and maintain(?:ing)? (?:scalable |robust )?(?:data )?(?:pipelines|infrastructure|services|systems)",
    r"פייפליין", r"פיתוח תהליכי", r"פיתוח backend", r"למידת מכונה", r"פיתוח תוכנה", r"תשתיות נתונים",
]

# ---------------------------------------------------------------------------
# Stage 5 - locations
# ---------------------------------------------------------------------------
ISRAEL_TERMS = [
    "israel", "ישראל", "tel aviv", "tel-aviv", "תל אביב", "ramat gan", "רמת גן", "givatayim", "גבעתיים",
    "herzliya", "herzlia", "הרצליה", "petah tikva", "petach tikva", "petah tiqwa", "petah-tikva", "פתח תקווה",
    "פתח תקוה", "ra'anana", "raanana", "רעננה", "kfar saba", "kefar sava", "כפר סבא", "hod hasharon",
    "hod ha sharon", "הוד השרון", "netanya", "נתניה", "rosh haayin", "rosh ha'ayin", "rosh ha'ain", "ראש העין",
    "holon", "חולון", "bat yam", "בת ים", "bnei brak", "bnei-brak", "בני ברק", "or yehuda", "אור יהודה",
    "yehud", "יהוד", "airport city", "איירפורט סיטי", "modiin", "modi'in", "מודיעין", "lod", "לוד",
    "ramla", "רמלה", "ness ziona", "nes ziona", "נס ציונה", "yavne", "יבנה", "kiryat ono", "קריית אונו",
    "קרית אונו", "ramat hasharon", "רמת השרון", "kfar yona", "כפר יונה", "even yehuda", "אבן יהודה",
    "caesarea", "קיסריה", "hadera", "חדרה", "or akiva", "אור עקיבא", "zichron", "זכרון יעקב", "shoham",
    "שוהם", "beit shemesh", "בית שמש", "mevaseret", "מבשרת", "ariel", "אריאל", "kfar qasem", "כפר קאסם",
    "givat shmuel", "גבעת שמואל", "רחובות", "ירושלים", "jerusalem", "rehovot",
    "rishon", "haifa", "חיפה", "beer sheva", "be'er sheva", "beersheba", "באר שבע", "ashdod", "אשדוד",
    "gush dan", "גוש דן", "sharon", "השרון", "merkaz", "מרכז", "center district", "central district",
    "petah", "רמת החייל", "ramat hahayal", "kiryat atidim", "קריית אטידים", "yokneam", "יקנעם",
    "matam", "מת\"ם", "savyon", "סביון", "tzur yigal", "kokhav yair", "כוכב יאיר", "ganei tikva", "גני תקווה",
    "elad", "אלעד", "kfar saba", "tirat carmel", "טירת כרמל", "nesher", "נשר", "kiryat", "קריית",
    "glilot", "גלילות", "herzliya pituach", "הרצליה פיתוח", "emek hefer", "עמק חפר", "yakum", "יקום",
    "shefayim", "שפיים", "kibbutz", "קיבוץ", "moshav", "מושב", "kfar", "kefar", "כפר", "givat", "גבעת",
    "ramat", "רמת", "neve", "נווה", "beit", "בית", "tzur", "צור", "sderot", "yakum", "hertzliya",
    "tel aviv yafo", "jaffa", "יפו", "tlv", "herzeliya", "hertzelia", "bnei brak", "petach", "raanana", "ramat aviv", "רמת אביב",
]
EXCLUDED_LOCATIONS = {
    "רחובות / Rehovot": ["rehovot", "rechovot", "רחובות"],
    "ראשון לציון / Rishon LeZion": ["rishon lezion", "rishon le zion", "rishon letsiyon", "rishon le-zion",
                                    "rishon leziyyon", "rishon lezyon", "rishon", "ראשון לציון", "ראשל\"צ", "ראשלצ"],
    "ירושלים / Jerusalem": ["jerusalem", "ירושלים", "al quds"],
    "אזור הצפון / North": [
        "northern israel", "north district", "northern district", "אזור הצפון", "מחוז הצפון", "איזור הצפון",
        "nazareth", "נצרת", "nof hagalil", "נוף הגליל", "nazareth illit", "afula", "עפולה", "tiberias", "טבריה",
        "safed", "tzfat", "zefat", "צפת", "karmiel", "carmiel", "כרמיאל", "nahariya", "נהריה", "akko", "acre",
        "עכו", "kiryat shmona", "קריית שמונה", "קרית שמונה", "ma'alot", "maalot", "מעלות", "migdal haemek",
        "migdal ha'emek", "מגדל העמק", "yokneam", "yoqneam", "יקנעם", "beit she'an", "beit shean", "בית שאן",
        "katzrin", "qatsrin", "קצרין", "rosh pina", "rosh pinna", "ראש פינה", "tefen", "תפן", "misgav", "משגב",
        "shlomi", "שלומי", "sakhnin", "סח'נין", "shefa-'amr", "shfar'am", "שפרעם", "tamra", "טמרה",
        "galilee", "galil", "גליל", "golan", "גולן", "kinneret", "כנרת", "migdal tefen",
        # A location that is exactly "North"/"צפון" is handled in location.py (not substring-matched)
    ],
    "אזור הדרום / South": [
        "southern israel", "south district", "southern district", "אזור הדרום", "מחוז הדרום", "איזור הדרום",
        "beer sheva", "be'er sheva", "beersheba", "beer-sheva", "be'er-sheva", "באר שבע", "ashdod", "אשדוד",
        "ashkelon", "אשקלון", "eilat", "אילת", "dimona", "דימונה", "kiryat gat", "קריית גת", "קרית גת",
        "sderot", "שדרות", "arad", "ערד", "netivot", "נתיבות", "ofakim", "אופקים", "yeruham", "ירוחם",
        "mitzpe ramon", "מצפה רמון", "kiryat malakhi", "קריית מלאכי", "negev", "נגב", "omer", "עומר",
        "rahat", "רהט", "lehavim", "להבים", "gan yavne", "גן יבנה",
    ],
}
# Administratively Haifa is its own district, but colloquially "the North". Excluded by default.
TREAT_HAIFA_AS_NORTH = True
HAIFA_TERMS = ["haifa", "חיפה", "krayot", "הקריות", "kiryat ata", "קריית אתא", "kiryat bialik", "קריית ביאליק",
               "kiryat motzkin", "קריית מוצקין", "kiryat yam", "קריית ים", "nesher", "נשר", "tirat carmel",
               "טירת כרמל", "matam haifa"]

FOREIGN_TERMS = [
    "united states", "usa", "u.s.", "new york", "nyc", "san francisco", "boston", "chicago", "austin",
    "seattle", "los angeles", "denver", "atlanta", "miami", "dallas", "remote - us", "remote us", "us remote",
    "united kingdom", "london", "uk", "england", "manchester", "ireland", "dublin", "germany", "berlin",
    "munich", "france", "paris", "spain", "madrid", "barcelona", "netherlands", "amsterdam", "poland",
    "warsaw", "krakow", "romania", "bucharest", "ukraine", "kyiv", "kiev", "portugal", "lisbon", "italy",
    "milan", "sweden", "stockholm", "denmark", "copenhagen", "switzerland", "zurich", "austria", "vienna",
    "czech", "prague", "hungary", "budapest", "bulgaria", "sofia", "serbia", "belgrade", "greece", "athens",
    "cyprus", "limassol", "canada", "toronto", "vancouver", "montreal", "mexico", "brazil", "argentina",
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "gurgaon", "singapore",
    "japan", "tokyo", "china", "shanghai", "hong kong", "australia", "sydney", "melbourne", "philippines",
    "manila", "vietnam", "uae", "dubai", "abu dhabi", "emea remote", "apac", "latam", "north america",
    "estonia", "tallinn", "latvia", "riga", "lithuania", "vilnius", "belgium", "brussels", "norway", "oslo",
    "finland", "helsinki", "south africa", "cape town", "colombia", "bogota", "chile", "costa rica",
    "armenia", "yerevan", "georgia", "tbilisi", "turkey", "istanbul", "morocco", "egypt", "cairo",
    "bangkok", "thailand", "kuala lumpur", "malaysia", "jakarta", "indonesia", "seoul", "korea", "taipei",
    "taiwan", "shenzhen", "beijing", "nairobi", "lagos", "saudi", "riyadh", "qatar", "doha", "bahrain",
    "new jersey", "california", "texas", "florida", "massachusetts", "washington", "illinois", "colorado",
]
FOREIGN_US_STATE_RE = r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b"

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
# Company ATS boards verified to exist and to publish Israeli jobs (seed list; discovery adds more)
SEED_ATS_BOARDS = [
    ("ashby", "finout"), ("ashby", "honeybook"), ("ashby", "lemonade"), ("ashby", "moonactive"),
    ("ashby", "sisense"), ("greenhouse", "apiiro"), ("greenhouse", "appsflyer"), ("greenhouse", "axonius"),
    ("greenhouse", "bigid"), ("greenhouse", "datarails"), ("greenhouse", "forter"), ("greenhouse", "gongio"),
    ("greenhouse", "innovid"), ("greenhouse", "island"), ("greenhouse", "jfrog"), ("greenhouse", "lightricks"),
    ("greenhouse", "melio"), ("greenhouse", "nanit"), ("greenhouse", "nice"), ("greenhouse", "obligo"),
    ("greenhouse", "optimove"), ("greenhouse", "orcasecurity"), ("greenhouse", "payoneer"),
    ("greenhouse", "riskified"), ("greenhouse", "similarweb"), ("greenhouse", "taboola"), ("greenhouse", "torq"),
    ("greenhouse", "transmitsecurity"), ("greenhouse", "tripactions"), ("greenhouse", "via"),
    ("greenhouse", "wizinc"), ("greenhouse", "yotpo"), ("lever", "cloudinary"), ("lever", "walkme"),
    ("smartrecruiters", "armis"),
]
ATS_KINDS = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]
# Display names for boards whose API does not return the company name
SEED_COMPANY_NAMES = {"finout": "Finout", "honeybook": "HoneyBook", "lemonade": "Lemonade",
                      "moonactive": "Moon Active", "sisense": "Sisense", "cloudinary": "Cloudinary",
                      "walkme": "WalkMe", "armis": "Armis"}
DISCOVERY_RECHECK_DAYS = 30
DISCOVERY_MAX_PROBES_PER_RUN = 400    # company slugs per run (x5 platforms); the rest waits for the next run
DISCOVERY_MAX_MINUTES = 12

# Additional Israeli job boards scanned with the generic crawler ({q} = url-encoded query)
# (SQLink, JobNet and Secret Tel Aviv were tested and render their results only with JavaScript -
#  their pages contain no jobs for a crawler, so they are not listed here.)
GENERIC_BOARDS = [
    ("GotFriends", "https://www.gotfriends.co.il/jobs/?search={q}"),
    ("JobKarov", "https://www.jobkarov.com/Search?q={q}"),
]
GENERIC_BOARD_QUERIES = ["data analyst", "analyst", "אנליסט", "BI"]
GENERIC_MAX_DETAIL_PER_PAGE = 40

# Best-effort search-engine discovery of company career pages hosted on ATS platforms
SEARCH_DISCOVERY_QUERIES = [
    'site:boards.greenhouse.io "Tel Aviv" analyst',
    'site:jobs.lever.co Israel analyst',
    'site:jobs.ashbyhq.com "Tel Aviv" analyst',
    'site:apply.workable.com Israel analyst',
    'site:comeet.com/jobs "data analyst"',
    'site:jobs.smartrecruiters.com Israel analyst',
]

USER_SOURCES_DIR = "user_sources"   # every .txt file here = user-uploaded links (one per line)
DATA_DIR = "data"
REPORTS_DIR = "reports"
KEEP_REPORTS = 30
