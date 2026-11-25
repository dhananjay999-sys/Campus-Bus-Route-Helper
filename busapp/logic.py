import re
from collections import Counter

MIN_PER_STOP = 3   # rough assumption: bus takes ~3 min between consecutive stops


class DuplicateRoute(Exception):
    pass


def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(mins):
    mins %= 1440
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _natural(route_id):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", route_id)]


def find_stop_index(stops, query):
    """Exact (case-insensitive) match wins; otherwise first partial match."""
    q = query.casefold().strip()
    if not q:
        return None
    for i, s in enumerate(stops):
        if s.casefold() == q:
            return i
    for i, s in enumerate(stops):
        if q in s.casefold():
            return i
    return None


def trips_per_day(route):
    span = to_min(route.end_time) - to_min(route.start_time)
    return span // route.interval_min + 1


class RouteBook:
    def __init__(self, routes=None):
        self._routes = {}
        for r in routes or []:
            self._routes[r.route_id] = r

    def __len__(self):
        return len(self._routes)

    def all(self):
        return sorted(self._routes.values(), key=lambda r: _natural(r.route_id))

    def get(self, route_id):
        return self._routes.get(route_id.strip().upper())

    def add(self, route):
        if route.route_id in self._routes:
            raise DuplicateRoute(f"Route {route.route_id} already exists.")
        self._routes[route.route_id] = route

    def replace(self, route):
        self._routes[route.route_id] = route

    def remove(self, route_id):
        return self._routes.pop(route_id.strip().upper(), None)

    # ---- searching -------------------------------------------------
    def search_stop(self, query):
        q = query.casefold().strip()
        if not q:
            return []
        found = []
        for r in self.all():
            hits = [s for s in r.stops if q in s.casefold()]
            if hits:
                exact = any(s.casefold() == q for s in hits)
                found.append((not exact, r, hits))
        found.sort(key=lambda t: t[0])          # exact matches first, stable otherwise
        return [(r, hits) for _, r, hits in found]

    def connecting(self, origin, dest):
        """Routes that go from origin to dest in that direction."""
        out = []
        for r in self.all():
            i = find_stop_index(r.stops, origin)
            j = find_stop_index(r.stops, dest)
            if i is None or j is None:
                continue
            if i < j:
                out.append((r, i, j, (j - i) * MIN_PER_STOP))
            elif r.is_loop and i != j:
                hops = (len(r.stops) - 1 - i) + j
                out.append((r, i, j, hops * MIN_PER_STOP))
        out.sort(key=lambda t: t[3])
        return out

    def filter(self, keyword="", status=None):
        kw = keyword.casefold().strip()
        res = []
        for r in self.all():
            if status and r.status != status:
                continue
            if kw:
                blob = " ".join([r.route_id, r.name] + r.stops).casefold()
                if kw not in blob:
                    continue
            res.append(r)
        return res

    def next_buses(self, route, stop_index, after_min, count=3):
        if route.status == "Suspended":
            return []
        start, end = to_min(route.start_time), to_min(route.end_time)
        offset = stop_index * MIN_PER_STOP
        times, dep = [], start
        while dep <= end and len(times) < count:
            if dep + offset >= after_min:
                times.append(dep + offset)
            dep += route.interval_min
        return times


# ---- analytics ---------------------------------------------------------
def compute_summary(book):
    routes = book.all()
    n = len(routes)
    if n == 0:
        return {"total": 0}
    status = Counter(r.status for r in routes)
    running = [r for r in routes if r.status != "Suspended"]

    stop_routes, display = {}, {}
    for r in routes:
        for s in set(x.casefold() for x in r.stops):
            stop_routes.setdefault(s, set()).add(r.route_id)
        for s in r.stops:
            display.setdefault(s.casefold(), s)
    top_stops = sorted(((display[k], len(v)) for k, v in stop_routes.items()),
                       key=lambda t: (-t[1], t[0]))[:5]

    bands = Counter()
    for r in routes:
        i = r.interval_min
        label = "<=10 min" if i <= 10 else "11-20 min" if i <= 20 else "21-30 min" if i <= 30 else ">30 min"
        bands[label] += 1

    daily_trips = sum(trips_per_day(r) for r in running)
    daily_seats = sum(trips_per_day(r) * r.capacity for r in running)
    span_hours = [(to_min(r.end_time) - to_min(r.start_time)) / 60 for r in routes]

    return {
        "total": n,
        "status": dict(status),
        "unique_stops": len(stop_routes),
        "avg_interval": sum(r.interval_min for r in routes) / n,
        "avg_stops": sum(len(r.stops) for r in routes) / n,
        "avg_capacity": sum(r.capacity for r in routes) / n,
        "avg_span_hours": sum(span_hours) / n,
        "daily_trips": daily_trips,
        "daily_seats": daily_seats,
        "top_stops": top_stops,
        "bands": {k: bands.get(k, 0) for k in ("<=10 min", "11-20 min", "21-30 min", ">30 min")},
        "longest": max(routes, key=lambda r: len(r.stops)),
        "most_frequent": min(routes, key=lambda r: r.interval_min),
    }


def find_warnings(book):
    """Returns a list of (level, message). Level is 'WARN' or 'CRIT'."""
    out = []
    routes = book.all()
    for r in routes:
        if r.status == "Suspended":
            out.append(("CRIT", f"{r.route_id} ({r.name}) is suspended."))
        elif r.status == "Delayed":
            out.append(("WARN", f"{r.route_id} ({r.name}) is running delayed."))
        if r.interval_min > 45:
            out.append(("WARN", f"{r.route_id} only runs every {r.interval_min} min - long wait."))
        span = to_min(r.end_time) - to_min(r.start_time)
        if span < 240:
            out.append(("WARN", f"{r.route_id} has a short service window ({span // 60}h{span % 60:02d}m)."))
        if r.capacity < 15 or r.capacity > 100:
            out.append(("WARN", f"{r.route_id} has an unusual capacity ({r.capacity} seats)."))

    # stops that lose all service when suspended routes are ignored
    live, dead = set(), {}
    for r in routes:
        for s in r.stops:
            if r.status == "Suspended":
                dead.setdefault(s.casefold(), s)
            else:
                live.add(s.casefold())
    for key, name in sorted(dead.items()):
        if key not in live:
            out.append(("CRIT", f"Stop '{name}' has no running service at all."))
    return out
