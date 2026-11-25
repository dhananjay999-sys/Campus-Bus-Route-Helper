import os
import sys
from datetime import datetime

from . import importer, reports
from .logic import (DuplicateRoute, MIN_PER_STOP, RouteBook, find_stop_index,
                    find_warnings, to_hhmm, to_min, trips_per_day)
from .models import STATUSES
from .storage import save_routes
from .validation import (ValidationError, build_route, clean_capacity, clean_id,
                         clean_interval, clean_name, clean_status, clean_stops, clean_time)

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def green(t): return paint(t, "32")
def red(t): return paint(t, "31")
def yellow(t): return paint(t, "33")
def cyan(t): return paint(t, "36")
def bold(t): return paint(t, "1")
def dim(t): return paint(t, "2")


class Cancelled(Exception):
    pass


def ask(prompt, cleaner=None, default=None):
    """Keep asking until the cleaner is happy. Type 'cancel' to bail out."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        try:
            raw = input(f"{prompt}{suffix}: ").strip()
        except EOFError:
            raise Cancelled()
        if raw.lower() == "cancel":
            raise Cancelled()
        if raw == "" and default is not None:
            return default
        if cleaner is None:
            return raw
        try:
            return cleaner(raw)
        except ValidationError as e:
            print(red("  x " + str(e)))


def banner():
    line = "=" * 52
    print(cyan(line))
    print(cyan("  CAMPUS BUS ROUTE HELPER".center(52)))
    print(cyan("  find your stop, find your bus".center(52)))
    print(cyan(line))


MENU = """
  1) Add a route            6) Next buses at a stop
  2) List all routes        7) Summary report
  3) Search by stop name    8) Warnings
  4) Find a ride (A -> B)   9) Export reports
  5) Filter / keyword      10) Import CSV
  11) Edit a route         12) Delete a route
   0) Save & exit
"""


def table(routes, page_size=10):
    if not routes:
        print(dim("  (nothing to show)"))
        return
    head = f"{'ID':<6}{'Name':<28}{'Stops':>5}  {'Hours':<12}{'Every':>6}{'Seats':>6}  Status"
    for start in range(0, len(routes), page_size):
        print(bold(head))
        print("-" * len(head))
        for r in routes[start:start + page_size]:
            name = r.name if len(r.name) <= 26 else r.name[:25] + "~"
            status = {"Active": green, "Delayed": yellow, "Suspended": red}[r.status](r.status)
            print(f"{r.route_id:<6}{name:<28}{len(r.stops):>5}  {r.start_time}-{r.end_time:<6}{r.interval_min:>4}m{r.capacity:>6}  {status}")
        end = min(start + page_size, len(routes))
        print(dim(f"  showing {start + 1}-{end} of {len(routes)}"))
        if end < len(routes):
            if input(dim("  [Enter] next page, q to stop: ")).strip().lower() == "q":
                break


def show_route(r):
    print(bold(f"\n{r.route_id} - {r.name}") + f"  ({r.status})")
    print(f"  {r.start_time} to {r.end_time}, every {r.interval_min} min, {r.capacity} seats, "
          f"{trips_per_day(r)} trips/day" + (", loop" if r.is_loop else ""))
    print("  " + " -> ".join(r.stops))


class App:
    def __init__(self, book, data_path, export_dir, log_dir):
        self.book = book
        self.path = data_path
        self.export_dir = export_dir
        self.log_dir = log_dir

    def save(self):
        save_routes(self.path, self.book.all())

    # ---- actions ------------------------------------------------------
    def add_route(self):
        print(dim("Type 'cancel' at any prompt to go back.\n"))
        while True:
            rid = ask("Route ID (e.g. R12)", clean_id)
            if self.book.get(rid):
                print(red(f"  x {rid} is already taken."))
                continue
            break
        name = ask("Route name", clean_name)
        stops = ask("Stops in order, comma separated", clean_stops)
        while True:
            start = ask("First departure (HH:MM)", clean_time)
            end = ask("Last departure (HH:MM)", clean_time)
            if to_min(end) > to_min(start):
                break
            print(red("  x Last departure has to be after the first one."))
        interval = ask("Minutes between buses", clean_interval)
        cap = ask("Seats per bus", clean_capacity)
        status = ask("Status (Active/Delayed/Suspended)", clean_status, default="Active")
        route = build_route(dict(route_id=rid, name=name, stops=stops, start_time=start,
                                 end_time=end, interval_min=interval, capacity=cap, status=status))
        self.book.add(route)
        self.save()
        print(green(f"\nSaved route {rid}."))

    def edit_route(self):
        r = self.book.get(ask("Route ID to edit", clean_id))
        if not r:
            print(red("No such route."))
            return
        show_route(r)
        print(dim("\nPress Enter to keep the current value.\n"))
        data = dict(
            route_id=r.route_id,
            name=ask("Name", clean_name, default=r.name),
            stops=ask("Stops", clean_stops, default=", ".join(r.stops)),
            start_time=ask("First departure", clean_time, default=r.start_time),
            end_time=ask("Last departure", clean_time, default=r.end_time),
            interval_min=ask("Interval", clean_interval, default=r.interval_min),
            capacity=ask("Seats", clean_capacity, default=r.capacity),
            status=ask("Status", clean_status, default=r.status),
        )
        try:
            self.book.replace(build_route(data))
        except ValidationError as e:
            print(red(f"Not saved: {e}"))
            return
        self.save()
        print(green("Updated."))

    def delete_route(self):
        rid = ask("Route ID to delete", clean_id)
        r = self.book.get(rid)
        if not r:
            print(red("No such route."))
            return
        show_route(r)
        if input("Really delete it? (yes/no): ").strip().lower() == "yes":
            self.book.remove(rid)
            self.save()
            print(green("Deleted."))
        else:
            print("Kept it.")

    def list_routes(self):
        table(self.book.all())

    def search_stop(self):
        q = ask("Stop name (partial is fine)")
        hits = self.book.search_stop(q)
        if not hits:
            print(yellow(f"No route passes a stop matching '{q}'."))
            return
        print(f"\n{len(hits)} route(s) serve '{q}':")
        for r, stops in hits:
            name = r.name if len(r.name) <= 30 else r.name[:29] + "~"
            print(f"  {r.route_id:<6}{name:<32}" + dim("stop: " + ", ".join(stops)))

    def find_ride(self):
        a = ask("Starting stop")
        b = ask("Destination stop")
        options = self.book.connecting(a, b)
        if not options:
            print(yellow(f"No single route goes {a} -> {b}."))
            return
        now = datetime.now().hour * 60 + datetime.now().minute
        for r, i, j, ride in options:
            nxt = self.book.next_buses(r, i, now, 1)
            when = to_hhmm(nxt[0]) if nxt else "none today"
            tag = "" if r.status == "Active" else yellow(f" [{r.status}]")
            print(f"  {bold(r.route_id)} {r.name}{tag}: {r.stops[i]} -> {r.stops[j]}, "
                  f"~{ride} min ride, next bus {when}")

    def filter_routes(self):
        kw = ask("Keyword (blank = any)", default="")
        st = ask("Status filter (blank = any)", lambda v: clean_status(v) if v else None, default="")
        table(self.book.filter(kw, st or None))

    def next_buses(self):
        stop = ask("Stop name")
        t = ask("Time to check from (HH:MM)", clean_time, default=datetime.now().strftime("%H:%M"))
        mins = to_min(t)
        shown = False
        for r, hits in self.book.search_stop(stop):
            idx = find_stop_index(r.stops, stop)
            times = self.book.next_buses(r, idx, mins, 3)
            label = f"{r.route_id} {r.name} @ {r.stops[idx]}"
            if r.status == "Suspended":
                print(f"  {label}: {red('suspended')}")
            elif times:
                print(f"  {label}: " + ", ".join(to_hhmm(x) for x in times))
            else:
                print(f"  {label}: {dim('no more buses today')}")
            shown = True
        if not shown:
            print(yellow("No routes serve that stop."))
        else:
            print(dim(f"  (assumes ~{MIN_PER_STOP} min between stops)"))

    def summary(self):
        print()
        for line in reports.summary_lines(self.book):
            print("  " + line)

    def warnings(self):
        warns = find_warnings(self.book)
        if not warns:
            print(green("All clear - nothing to flag."))
            return
        for lvl, msg in warns:
            print((red("[CRIT] ") if lvl == "CRIT" else yellow("[WARN] ")) + msg)

    def export(self):
        a = reports.export_text(self.book, self.export_dir)
        b = reports.export_markdown(self.book, self.export_dir)
        c = reports.export_csv(self.book, self.export_dir)
        print(green("Exported:"))
        for p in (a, b, c):
            print("  " + p)

    def import_csv(self):
        path = ask("Path to CSV file").strip('"').strip("'")
        res = importer.import_csv(path, self.book, self.log_dir)
        if res.added:
            self.save()
        print(green(f"Imported {res.added} route(s).") + (red(f" Rejected {res.skipped}.") if res.skipped else ""))
        for line, msg in res.errors[:5]:
            print(red(f"  line {line}: ") + msg)
        if res.skipped > 5:
            print(dim(f"  ...and {res.skipped - 5} more."))
        if res.log_path:
            print(dim(f"Full error log: {res.log_path}"))

    # ---- main loop ----------------------------------------------------
    def run(self):
        actions = {
            "1": self.add_route, "2": self.list_routes, "3": self.search_stop,
            "4": self.find_ride, "5": self.filter_routes, "6": self.next_buses,
            "7": self.summary, "8": self.warnings, "9": self.export,
            "10": self.import_csv, "11": self.edit_route, "12": self.delete_route,
        }
        banner()
        while True:
            print(MENU)
            try:
                choice = input("Choose: ").strip()
            except (EOFError, KeyboardInterrupt):
                choice = "0"
            if choice == "0":
                self.save()
                print("Saved. See you!")
                return
            action = actions.get(choice)
            if not action:
                print(red("Pick a number from the menu."))
                continue
            try:
                action()
            except (Cancelled, KeyboardInterrupt):
                print(dim("\n(cancelled)"))
            except DuplicateRoute as e:
                print(red(str(e)))
