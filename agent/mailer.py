"""Section 12: e-mail the report (SMTP; defaults to Gmail with an App Password)."""
import html
import os
import smtplib
import ssl
from email.message import EmailMessage


class MailConfigError(Exception):
    pass


def settings():
    to = [a.strip() for a in os.environ.get("EMAIL_TO", "").replace(";", ",").split(",") if a.strip()]
    user = os.environ.get("SMTP_USER", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
    if not to:
        raise MailConfigError("לא הוגדרה כתובת יעד (EMAIL_TO). לא נשלח מייל לכתובת שלא הוגדרה במפורש.")
    if not user or not pwd:
        raise MailConfigError("חסרים פרטי SMTP (SMTP_USER / SMTP_PASSWORD)")
    return {
        "to": to, "user": user, "password": pwd,
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com",
        "port": int(os.environ.get("SMTP_PORT", "465") or 465),
        "from": os.environ.get("EMAIL_FROM", "").strip() or user,
    }


def body_html(day, new_jobs, cumulative, statuses, removed):
    ok = sum(1 for s in statuses if s.status == "הצלחה")
    partial = sum(1 for s in statuses if s.status == "חלקי")
    failed = len(statuses) - ok - partial
    # summary only - the jobs themselves are in the attached Excel file
    return f"""<div dir="rtl" style="font-family:Arial,sans-serif">
<h2>דוח משרות Data Analytics - {day}</h2>
<ul>
<li><b>משרות חדשות:</b> {len(new_jobs)}</li>
<li><b>ברשימה המצטברת:</b> {len(cumulative)} (הוסרו {removed} משרות ישנות מ-20 ימים)</li>
<li><b>קישורים שנסרקו:</b> {len(statuses)} (הצלחה {ok}, חלקי {partial}, נכשל/לא נגיש {failed})</li>
</ul>
<p>כל המשרות מופיעות בקובץ ה-Excel המצורף (4 לשוניות).</p>
</div>"""


def send(subject, html_body, attachment_path):
    cfg = settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = ", ".join(cfg["to"])
    msg.set_content("דוח משרות Data Analytics - הקובץ המלא מצורף.")
    msg.add_alternative(html_body, subtype="html")
    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application",
                           subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           filename=os.path.basename(attachment_path))
    ctx = ssl.create_default_context()
    if cfg["port"] == 465:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=60) as s:
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=60) as s:
            s.ehlo()
            if s.has_extn("starttls"):
                s.starttls(context=ctx)
                s.ehlo()
            if s.has_extn("auth"):
                s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
    return cfg["to"]
