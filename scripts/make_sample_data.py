"""Regenerates the demo data in /data. Run: python scripts/make_sample_data.py"""
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from busapp.validation import build_route  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

STOPS = ["Main Gate", "Admin Block", "Central Library", "Engineering Block", "Science Complex",
         "Boys Hostel A", "Boys Hostel B", "Girls Hostel", "Sports Complex", "Canteen",
         "Medical Centre", "Auditorium", "Faculty Quarters", "Parking Lot 2", "Metro Station",
         "Bus Depot", "Research Park", "Student Activity Centre", "Pharmacy Block", "Back Gate"]

HAND_MADE = [
    # id, name, stops, start, end, interval, capacity, status  (edge cases on purpose)
    ("R1", "Main Gate Shuttle", "Main Gate|Admin Block|Central Library|Engineering Block", "06:30", "21:30", 10, 40, "Active"),
    ("R2", "Hostel Loop", "Boys Hostel A|Boys Hostel B|Girls Hostel|Canteen|Boys Hostel A", "07:00", "22:00", 15, 30, "Active"),
    ("R3", "Metro Connector", "Metro Station|Main Gate|Admin Block", "06:00", "23:00", 20, 50, "Delayed"),
    ("R4", "Night Safety Ride", "Central Library|Girls Hostel|Boys Hostel A", "21:00", "23:30", 30, 12, "Active"),
    ("R5", "Sports Special", "Sports Complex|Canteen", "16:00", "18:00", 60, 25, "Suspended"),
    ("R6", "Ultra Frequent", "Main Gate|Metro Station", "08:00", "10:00", 1, 120, "Active"),       # interval boundary (min)
    ("R7", "Sunday Skeleton", "Back Gate|Bus Depot", "09:00", "17:00", 120, 10, "Active"),          # interval/capacity boundary
    ("R8", "Grand Campus Tour", "|".join(STOPS[:20]), "09:00", "18:00", 45, 60, "Active"),         # many stops
]


def make_random(rng, n):
    rows = []
    for i in range(9, 9 + n):
        k = rng.randint(3, 8)
        stops = rng.sample(STOPS, k)
        start_h = rng.choice([6, 7, 8, 9])
        end_h = rng.choice([17, 19, 21, 22])
        rows.append((f"R{i}", (f"{stops[0]} to {stops[-1]}" if len(stops[0]) + len(stops[-1]) <= 34 else f"{stops[0]} Express"), "|".join(stops),
                     f"{start_h:02d}:{rng.choice([0, 15, 30, 45]):02d}", f"{end_h:02d}:00",
                     rng.choice([8, 10, 12, 15, 20, 25, 30, 40]), rng.choice([20, 30, 40, 45, 50, 60]),
                     rng.choices(["Active", "Delayed", "Suspended"], [8, 2, 1])[0]))
    return rows


def main():
    rng = random.Random(28)
    rows = HAND_MADE + make_random(rng, 34)
    routes = [build_route(dict(zip(
        ["route_id", "name", "stops", "start_time", "end_time", "interval_min", "capacity", "status"], r)))
        for r in rows]
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "routes.json"), "w", encoding="utf-8") as f:
        json.dump({"version": 1, "routes": [r.to_dict() for r in routes]}, f, indent=2)
    header = ["route_id", "name", "stops", "start_time", "end_time", "interval_min", "capacity", "status"]
    with open(os.path.join(DATA, "sample_routes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)

    bad = [
        ["R101", "Good Row One", "Main Gate|Canteen", "07:00", "20:00", "15", "40", "Active"],
        ["R102", "Bad Time", "Main Gate|Canteen", "25:99", "20:00", "15", "40", "Active"],
        ["R103", "Bad Interval", "Main Gate|Canteen", "07:00", "20:00", "abc", "40", "Active"],
        ["R104", "One Stop Only", "Main Gate", "07:00", "20:00", "15", "40", "Active"],
        ["", "Blank ID", "Main Gate|Canteen", "07:00", "20:00", "15", "40", "Active"],
        ["R1", "Duplicate of R1", "Main Gate|Canteen", "07:00", "20:00", "15", "40", "Active"],
        ["R105", "Backwards Hours", "Main Gate|Canteen", "20:00", "07:00", "15", "40", "Active"],
        ["R106", "Another Good One", "Back Gate|Medical Centre|Canteen", "08:00", "18:00", "20", "35", "delayed"],
    ]
    with open(os.path.join(DATA, "sample_import_with_errors.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(bad)
    print(f"Wrote {len(routes)} routes + sample CSVs to {os.path.abspath(DATA)}")


if __name__ == "__main__":
    main()
