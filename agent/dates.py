"""Stage 6: posting / update date parsing and the 20-day rule."""
import re
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

from . import config as C

TZ = ZoneInfo(C.TIMEZONE)

HE_WORDS = {"יום": 1, "יומיים": 2, "שבוע": 7, "שבועיים": 14, "חודש": 30, "חודשיים": 60, "שעה": 0, "שעתיים": 0,
            "דקה": 0, "דקות": 0}
UNIT_DAYS = {"minute": 0, "min": 0, "hour": 0, "hr": 0, "day": 1, "week": 7, "month": 30, "year": 365,
             "דקות": 0, "דקה": 0, "שעות": 0, "שעה": 0, "ימים": 1, "יום": 1, "שבועות": 7, "שבוע": 7,
             "חודשים": 30, "חודש": 30, "שנים": 365, "שנה": 365}


def today_il(now=None):
    return (now or datetime.now(TZ)).astimezone(TZ).date()


def parse_date(raw, now=None):
    """Parse absolute (ISO / dd/mm/yyyy / epoch ms) or relative ("3 days ago", "לפני 3 ימים") dates.

    Returns a date in Israel time or None when it cannot be determined reliably.
    """
    if raw is None or raw == "":
        return None
    now = (now or datetime.now(TZ)).astimezone(TZ)
    if isinstance(raw, (int, float)):
        ts = raw / 1000 if raw > 1e11 else raw
        return datetime.fromtimestamp(ts, timezone.utc).astimezone(TZ).date()
    if isinstance(raw, datetime):
        return (raw if raw.tzinfo else raw.replace(tzinfo=TZ)).astimezone(TZ).date()
    if isinstance(raw, date):
        return raw
    s = str(raw).strip().replace("‏", "").replace("‎", "")
    s_low = s.lower()

    # ISO 8601
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[t ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(z|[+-]\d{2}:?\d{2})?)?", s_low)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if m.group(4) and m.group(7):
            try:
                dt = datetime.fromisoformat(m.group(0).upper().replace("Z", "+00:00").replace(" ", "T"))
                return dt.astimezone(TZ).date()
            except ValueError:
                pass
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    # dd/mm/yyyy or dd.mm.yyyy (Israeli format)
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b", s_low)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y += 2000 if y < 100 else 0
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    # English month names: "Sep 17, 2026" / "17 September 2026"
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(re.sub(r"(\d)(st|nd|rd|th)", r"\1", s.strip()), fmt).date()
        except ValueError:
            pass

    base = now.date()
    if re.search(r"\b(just now|today|just posted|few (?:hours|minutes) ago)\b|היום|ממש עכשיו|עכשיו", s_low):
        return base
    if re.search(r"\byesterday\b|אתמול", s_low):
        return base - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*(minute|min|hour|hr|day|week|month|year)s?\s*ago", s_low)
    if m:
        return base - timedelta(days=int(m.group(1)) * UNIT_DAYS[m.group(2)])
    m = re.search(r"(?:before|לפני)?\s*(\d+)\+?\s*(דקות|דקה|שעות|שעה|ימים|יום|שבועות|שבוע|חודשים|חודש|שנים|שנה)", s)
    if m:
        return base - timedelta(days=int(m.group(1)) * UNIT_DAYS[m.group(2)])
    m = re.search(r"לפני\s+(יומיים|שבועיים|חודשיים|שעתיים|יום|שבוע|חודש|שעה|דקה)", s)
    if m:
        return base - timedelta(days=HE_WORDS[m.group(1)])
    m = re.search(r"\b(?:an?|one)\s+(hour|day|week|month)\s+ago", s_low)
    if m:
        return base - timedelta(days=UNIT_DAYS[m.group(1)])
    return None


def relevant_date(posted_raw, updated_raw, now=None):
    """Latest of posted / updated (the update date wins when it is newer)."""
    ds = [d for d in (parse_date(posted_raw, now), parse_date(updated_raw, now)) if d]
    if not ds:
        return None
    d = max(ds)
    # dates in the future (timezone skew) are clamped to today
    return min(d, today_il(now))


def age_days(d, now=None):
    return (today_il(now) - d).days


def is_fresh(d, now=None):
    """True/False for a known date, None when the date is unknown (keep & mark)."""
    if d is None:
        return None
    return age_days(d, now) <= C.MAX_DAYS
