"""Every bit of user/file input goes through here before it touches a Route."""
import re

from .models import Route, STATUSES

MAX_STOPS = 25


class ValidationError(ValueError):
    pass


ID_RE = re.compile(r"^[A-Z]{1,2}\d{1,3}$")
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
TEXT_RE = re.compile(r"^[\w &'./()-]+$")


def clean_id(raw):
    v = str(raw).strip().upper()
    if not ID_RE.match(v):
        raise ValidationError("Route ID must look like R12 or GL3 (1-2 letters + 1-3 digits).")
    return v


def clean_name(raw):
    v = " ".join(str(raw).split())
    if not 3 <= len(v) <= 40:
        raise ValidationError("Route name must be 3-40 characters.")
    if not TEXT_RE.match(v):
        raise ValidationError("Route name has characters I can't accept.")
    return v


def clean_stop(raw):
    v = " ".join(str(raw).split())
    if not 2 <= len(v) <= 40 or not TEXT_RE.match(v):
        raise ValidationError(f"Bad stop name: '{v}'")
    return v


def clean_stops(raw):
    """Accepts 'A, B, C' or 'A|B|C' (the CSV uses pipes)."""
    if isinstance(raw, (list, tuple)):
        parts = [str(p) for p in raw]
    else:
        parts = re.split(r"[,|;]", str(raw))
    parts = [p for p in (p.strip() for p in parts) if p]
    if len(parts) < 2:
        raise ValidationError("A route needs at least 2 stops.")
    if len(parts) > MAX_STOPS:
        raise ValidationError(f"Too many stops (max {MAX_STOPS}).")
    stops = [clean_stop(p) for p in parts]
    seen = set()
    for i, s in enumerate(stops):
        key = s.casefold()
        is_loop_end = i == len(stops) - 1 and key == stops[0].casefold() and len(stops) > 2
        if key in seen and not is_loop_end:
            raise ValidationError(f"Stop '{s}' appears twice (only the last stop may repeat the first, for loops).")
        seen.add(key)
    return stops


def clean_time(raw):
    m = TIME_RE.match(str(raw).strip())
    if not m:
        raise ValidationError("Time must be 24h HH:MM, like 07:30.")
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def clean_int(raw, lo, hi, label):
    try:
        n = int(str(raw).strip())
    except ValueError:
        raise ValidationError(f"{label} must be a whole number.")
    if not lo <= n <= hi:
        raise ValidationError(f"{label} must be between {lo} and {hi}.")
    return n


def clean_interval(raw):
    return clean_int(raw, 1, 120, "Interval (minutes)")


def clean_capacity(raw):
    return clean_int(raw, 10, 120, "Capacity (seats)")


def clean_status(raw):
    v = str(raw).strip().casefold()
    if not v:
        raise ValidationError("Status is empty.")
    for s in STATUSES:
        if s.casefold() == v or s.casefold().startswith(v):
            return s
    raise ValidationError("Status must be one of: " + ", ".join(STATUSES))


def _to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def build_route(fields):
    """Validate a whole record at once and report every problem, not just the first."""
    steps = [
        ("route_id", clean_id), ("name", clean_name), ("stops", clean_stops),
        ("start_time", clean_time), ("end_time", clean_time),
        ("interval_min", clean_interval), ("capacity", clean_capacity),
    ]
    clean, problems = {}, []
    for key, fn in steps:
        try:
            clean[key] = fn(fields.get(key, ""))
        except ValidationError as e:
            problems.append(f"{key}: {e}")
    raw_status = fields.get("status", "") or "Active"
    try:
        clean["status"] = clean_status(raw_status)
    except ValidationError as e:
        problems.append(f"status: {e}")

    if "start_time" in clean and "end_time" in clean:
        if _to_min(clean["end_time"]) <= _to_min(clean["start_time"]):
            problems.append("end_time: last departure must be after the first departure.")
    if problems:
        raise ValidationError("; ".join(problems))
    return Route(**clean)
