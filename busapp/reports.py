import csv
import os
from datetime import datetime

from .logic import compute_summary, find_warnings, trips_per_day


def _bar(value, biggest, width=20):
    if biggest <= 0:
        return ""
    return "#" * max(1 if value else 0, round(width * value / biggest))


def summary_lines(book):
    s = compute_summary(book)
    if s["total"] == 0:
        return ["No routes stored yet."]
    L = []
    L.append(f"Routes stored        : {s['total']}")
    L.append("By status            : " + ", ".join(f"{k} {v}" for k, v in sorted(s["status"].items())))
    L.append(f"Unique stops served  : {s['unique_stops']}")
    L.append(f"Average interval     : {s['avg_interval']:.1f} min")
    L.append(f"Average stops/route  : {s['avg_stops']:.1f}")
    L.append(f"Average capacity     : {s['avg_capacity']:.0f} seats")
    L.append(f"Average service span : {s['avg_span_hours']:.1f} h")
    L.append(f"Daily trips (running): {s['daily_trips']}")
    L.append(f"Daily seat capacity  : {s['daily_seats']:,}")
    L.append(f"Longest route        : {s['longest'].route_id} ({len(s['longest'].stops)} stops)")
    L.append(f"Most frequent route  : {s['most_frequent'].route_id} (every {s['most_frequent'].interval_min} min)")
    L.append("")
    L.append("Busiest stops (number of routes):")
    top = max(c for _, c in s["top_stops"])
    for name, c in s["top_stops"]:
        L.append(f"  {name:<24} {c:>2}  {_bar(c, top)}")
    L.append("")
    L.append("Frequency trend (routes per interval band):")
    big = max(s["bands"].values())
    for band, c in s["bands"].items():
        L.append(f"  {band:<10} {c:>3}  {_bar(c, big)}")
    return L


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure(folder):
    os.makedirs(folder, exist_ok=True)
    return folder


def export_text(book, folder):
    path = os.path.join(_ensure(folder), f"audit_{_stamp()}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Campus Bus Route Helper - audit log\nGenerated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write("=" * 50 + "\n")
        f.write("\n".join(summary_lines(book)) + "\n\nWarnings\n--------\n")
        warns = find_warnings(book)
        f.write("\n".join(f"[{lvl}] {msg}" for lvl, msg in warns) if warns else "None")
        f.write("\n")
    return path


def export_markdown(book, folder):
    path = os.path.join(_ensure(folder), f"report_{_stamp()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Campus Bus Route Helper - Report\n\n")
        f.write(f"_Generated {datetime.now():%Y-%m-%d %H:%M}_\n\n## Summary\n\n```\n")
        f.write("\n".join(summary_lines(book)) + "\n```\n\n## Routes\n\n")
        f.write("| ID | Name | Stops | First | Last | Every | Seats | Status |\n")
        f.write("|----|------|-------|-------|------|-------|-------|--------|\n")
        for r in book.all():
            f.write(f"| {r.route_id} | {r.name} | {len(r.stops)} | {r.start_time} | {r.end_time} "
                    f"| {r.interval_min} min | {r.capacity} | {r.status} |\n")
        f.write("\n## Warnings\n\n")
        warns = find_warnings(book)
        if warns:
            for lvl, msg in warns:
                f.write(f"- **{lvl}** {msg}\n")
        else:
            f.write("No warnings.\n")
    return path


def export_csv(book, folder):
    path = os.path.join(_ensure(folder), f"routes_{_stamp()}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "name", "stops", "start_time", "end_time",
                    "interval_min", "capacity", "status", "trips_per_day"])
        for r in book.all():
            w.writerow([r.route_id, r.name, "|".join(r.stops), r.start_time, r.end_time,
                        r.interval_min, r.capacity, r.status, trips_per_day(r)])
    return path
