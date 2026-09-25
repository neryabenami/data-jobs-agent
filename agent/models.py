from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RawJob:
    """A job as collected from a source, after its full job page / description was fetched."""
    title: str
    company: str
    source: str                 # site the job was actually pulled from (LinkedIn, Drushim, Wix careers...)
    url: str                    # direct link to the job page
    description: str            # full job description text (description only - no site chrome)
    location: str = ""
    posted_raw: str = ""        # e.g. "2026-09-10" / "3 days ago" / "לפני 7 שעות"
    updated_raw: str = ""       # explicit "updated" date if the site shows one
    job_id: str = ""
    experience_hint: str = ""   # structured experience field from the site, if any
    israeli_context: bool = False  # found through an Israel-scoped search / Israeli site
    listing_url: str = ""       # the scanned link this job came from (for the sources tab)


@dataclass
class Job:
    """A job that passed every rule and goes to the report."""
    title: str
    company: str
    source: str
    location: str
    experience: str
    reason: str
    url: str
    date_display: str
    date_iso: Optional[str]     # relevant date (latest publish/update) or None when unknown
    key: str = ""
    alt_key: str = ""
    first_seen: str = ""
    last_seen: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in fields})


@dataclass
class SourceStatus:
    url: str
    site: str
    method: str
    status: str = "הצלחה"      # הצלחה / נכשל / חלקי / לא נגיש
    error: str = ""
    count: int = 0
    notes: list = field(default_factory=list)

    def fail(self, msg, status="נכשל"):
        self.status = status
        self.error = msg

    def partial(self, msg):
        if self.status == "הצלחה":
            self.status = "חלקי"
        self.notes.append(msg)
        self.error = "; ".join(dict.fromkeys(self.notes))[:500]
