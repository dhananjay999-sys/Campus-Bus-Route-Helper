import json
import os
import time

from .validation import build_route, ValidationError


def load_routes(path):
    """Returns (routes, notes). Never raises for missing/corrupt files."""
    notes = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        notes.append("No data file yet - starting with an empty route book.")
        save_routes(path, [])
        return [], notes
    except json.JSONDecodeError:
        backup = f"{path}.corrupt-{int(time.time())}"
        os.replace(path, backup)
        notes.append(f"Data file was damaged. Moved it to {os.path.basename(backup)} and started fresh.")
        save_routes(path, [])
        return [], notes

    if not isinstance(raw, dict) or not isinstance(raw.get("routes"), list):
        notes.append("Data file had an unexpected layout - ignoring its contents.")
        return [], notes

    routes = []
    for i, rec in enumerate(raw["routes"], start=1):
        try:
            routes.append(build_route(rec if isinstance(rec, dict) else {}))
        except ValidationError as e:
            notes.append(f"Skipped stored record #{i}: {e}")
    return routes, notes


def save_routes(path, routes):
    """Write to a temp file first so a crash can't leave half a file behind."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    payload = {"version": 1, "routes": [r.to_dict() for r in routes]}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
