import csv
import os
from datetime import datetime

from .logic import DuplicateRoute
from .validation import build_route, ValidationError

REQUIRED = ["route_id", "name", "stops", "start_time", "end_time", "interval_min", "capacity"]


class ImportResult:
    def __init__(self):
        self.added = 0
        self.errors = []        # (line_number, message)
        self.log_path = None

    @property
    def skipped(self):
        return len(self.errors)


def import_csv(path, book, log_dir):
    res = ImportResult()
    try:
        f = open(path, "r", newline="", encoding="utf-8-sig")
    except OSError as e:
        res.errors.append((0, f"Could not open file: {e.strerror or e}"))
        return res

    with f:
        reader = csv.DictReader(f)
        header = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            res.errors.append((1, "Missing column(s): " + ", ".join(missing)))
            return _finish(res, path, log_dir)
        for row in reader:
            line = reader.line_num
            clean_row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
            try:
                route = build_route(clean_row)
                book.add(route)
                res.added += 1
            except (ValidationError, DuplicateRoute) as e:
                res.errors.append((line, str(e)))
    return _finish(res, path, log_dir)


def _finish(res, src, log_dir):
    if res.errors:
        os.makedirs(log_dir, exist_ok=True)
        res.log_path = os.path.join(log_dir, f"import_errors_{datetime.now():%Y%m%d_%H%M%S}.log")
        with open(res.log_path, "w", encoding="utf-8") as f:
            f.write(f"Import of {src}\n{res.added} added, {res.skipped} rejected\n\n")
            for line, msg in res.errors:
                f.write(f"line {line}: {msg}\n")
    return res
