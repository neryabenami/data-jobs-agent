"""Daily entry point.

    python -m agent.main run                 # the scheduled daily job (scan -> xlsx -> wait for 10:00 -> e-mail)
    python -m agent.main run --no-send       # build the report only (nothing is e-mailed, state is not changed)
    python -m agent.main run --test-email    # send a clearly-marked test e-mail now (state is not changed)
    python -m agent.main run --only linkedin,drushim --max-minutes 10 --no-send
"""
import argparse
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta

from . import config as C
from . import dates, excel, mailer, pipeline
from .net import Http

log = logging.getLogger("agent")


def il_now():
    return datetime.now(dates.TZ)


def at_il(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=dates.TZ)


def wait_until(target):
    """Sleep until `target` (Israel time). Guarantees the report is never sent before 10:00."""
    while True:
        remaining = (target - il_now()).total_seconds()
        if remaining <= 0:
            return
        log.info("report ready - waiting %.0f minutes until %s", remaining / 60, target.strftime("%H:%M"))
        time.sleep(min(remaining, 300))


def prune_reports():
    files = sorted(glob.glob(os.path.join(C.REPORTS_DIR, "jobs_report_*.xlsx")))
    for f in files[:-C.KEEP_REPORTS]:
        os.remove(f)


def write_github_summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def run(args):
    now = il_now()
    today = now.date()
    state = pipeline.load_state()
    daily = not (args.no_send or args.test_email)

    if daily and state.get("last_sent_date") == today.isoformat() and not args.force:
        log.info("today's report (%s) was already sent - nothing to do", today)
        return 0

    send_at = at_il(today, C.SEND_HOUR)
    if daily and (send_at - now) > timedelta(hours=5, minutes=20):
        # GitHub jobs are limited to 6h; a run this early cannot wait for 10:00. A later trigger will do it.
        log.warning("too early (%s) - the scheduled run closer to 10:00 will produce today's report",
                    now.strftime("%H:%M"))
        return 0

    deadline = at_il(today, *C.SCAN_DEADLINE)
    if now >= deadline - timedelta(minutes=10):
        deadline = now + timedelta(minutes=C.LATE_RUN_SCAN_MINUTES)
    if not daily:
        deadline = now + timedelta(minutes=args.max_minutes or 120)
    elif args.max_minutes:
        deadline = min(deadline, now + timedelta(minutes=args.max_minutes))
    log.info("scan started %s, must finish by %s (Israel time)", now.strftime("%H:%M"), deadline.strftime("%H:%M"))

    http = Http(deadline=time.time() + (deadline - now).total_seconds())
    only = set(args.only.split(",")) if args.only else None
    ctx, accepted, stale, reasons = pipeline.scan_and_evaluate(http, now, only)
    new_jobs, cumulative, removed = pipeline.update_cumulative(state, accepted, stale, now)

    report = os.path.join(C.REPORTS_DIR, f"jobs_report_{today.isoformat()}.xlsx")
    excel.build(report, new_jobs, cumulative, ctx.statuses)
    excel.verify(report, len(new_jobs))

    summary = [f"## דוח {today}", f"- משרות גולמיות שנבדקו: {len(ctx.raw_jobs)}",
               f"- עברו את כל הכללים: {len(accepted)}", f"- חדשות: {len(new_jobs)}",
               f"- ברשימה המצטברת: {len(cumulative)} (הוסרו {removed})",
               f"- קישורים שנסרקו: {len(ctx.statuses)}", "", "### סיבות סינון",
               *[f"- {k}: {v}" for k, v in reasons.most_common()]]
    log.info("\n".join(summary))
    write_github_summary(summary)
    with open(os.path.join(C.DATA_DIR, "last_run.json"), "w", encoding="utf-8") as f:
        json.dump({"run_at": now.isoformat(), "raw": len(ctx.raw_jobs), "accepted": len(accepted),
                   "new": len(new_jobs), "cumulative": len(cumulative), "removed": removed,
                   "links": len(ctx.statuses), "reasons": dict(reasons),
                   "locations_treated_as_abroad": dict(ctx.foreign_locations.most_common(80))},
                  f, ensure_ascii=False, indent=1)

    if args.no_send:
        log.info("--no-send: report saved to %s (state not modified)", report)
        return 0

    subject = f"דוח משרות Data Analytics | {today.strftime('%d/%m/%Y')} | {len(new_jobs)} משרות חדשות"
    body = mailer.body_html(today.strftime("%d/%m/%Y"), new_jobs, cumulative, ctx.statuses, removed)
    if args.test_email:
        to = mailer.send("[בדיקה] " + subject, body, report)
        log.info("test e-mail sent to %s (state not modified)", to)
        return 0

    wait_until(send_at)  # hard rule: never before 10:00 Asia/Jerusalem
    assert il_now() >= send_at
    excel.verify(report, len(new_jobs))  # the attachment is today's, freshly built file
    to = mailer.send(subject, body, report)
    log.info("report e-mailed at %s to %s", il_now().strftime("%H:%M:%S"), to)

    state["jobs"] = [j.to_dict() for j in cumulative]
    state["last_sent_date"] = today.isoformat()
    state["history"] = (state.get("history", []) + [{
        "date": today.isoformat(), "sent_at": il_now().strftime("%H:%M:%S"), "new": len(new_jobs),
        "cumulative": len(cumulative), "links": len(ctx.statuses)}])[-60:]
    pipeline.save_state(state)
    prune_reports()
    return 0


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    for noisy in ("urllib3", "charset_normalizer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    p = argparse.ArgumentParser(prog="agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--no-send", action="store_true", help="build the xlsx only")
    r.add_argument("--test-email", action="store_true", help="send a marked test e-mail immediately")
    r.add_argument("--force", action="store_true", help="run even if today's report was already sent")
    r.add_argument("--only", default="", help="comma list: user,linkedin,drushim,jobmaster,alljobs,indeed,ats,"
                                              "generic,discovery")
    r.add_argument("--max-minutes", type=int, default=0)
    args = p.parse_args(argv)
    os.makedirs(C.DATA_DIR, exist_ok=True)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
