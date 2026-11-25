import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from busapp import importer, reports                      # noqa: E402
from busapp.logic import RouteBook, compute_summary, find_warnings, to_min  # noqa: E402
from busapp.storage import load_routes, save_routes       # noqa: E402
from busapp.validation import ValidationError, build_route, clean_stops, clean_time  # noqa: E402


def make(rid="R1", stops="A Stop|B Stop|C Stop", **kw):
    d = dict(route_id=rid, name="Test Route", stops=stops, start_time="08:00",
             end_time="18:00", interval_min=10, capacity=40, status="Active")
    d.update(kw)
    return build_route(d)


class ValidationTests(unittest.TestCase):
    def test_time_padding(self):
        self.assertEqual(clean_time("7:05"), "07:05")

    def test_bad_time(self):
        for bad in ["24:00", "7pm", "", "12:60"]:
            with self.assertRaises(ValidationError):
                clean_time(bad)

    def test_stops_need_two(self):
        with self.assertRaises(ValidationError):
            clean_stops("Only One")

    def test_duplicate_stop_rejected_but_loop_ok(self):
        with self.assertRaises(ValidationError):
            clean_stops("A Stop, B Stop, A Stop, C Stop")
        self.assertEqual(len(clean_stops("A Stop, B Stop, C Stop, A Stop")), 4)

    def test_interval_bounds(self):
        with self.assertRaises(ValidationError):
            make(interval_min=0)
        with self.assertRaises(ValidationError):
            make(interval_min=121)

    def test_end_before_start(self):
        with self.assertRaises(ValidationError):
            make(start_time="20:00", end_time="08:00")

    def test_status_shortcut(self):
        self.assertEqual(make(status="sus").status, "Suspended")


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.book = RouteBook([
            make("R1", "Main Gate|Library|Canteen"),
            make("R2", "Canteen|Library|Main Gate"),
            make("R10", "Hostel|Main Gate", status="Suspended"),
        ])

    def test_natural_order(self):
        self.assertEqual([r.route_id for r in self.book.all()], ["R1", "R2", "R10"])

    def test_search_partial_and_case(self):
        ids = [r.route_id for r, _ in self.book.search_stop("main")]
        self.assertEqual(sorted(ids), ["R1", "R10", "R2"])

    def test_direction_matters(self):
        ids = [t[0].route_id for t in self.book.connecting("Main Gate", "Canteen")]
        self.assertEqual(ids, ["R1"])

    def test_next_buses(self):
        r = self.book.get("R1")
        self.assertEqual(self.book.next_buses(r, 0, to_min("08:05"), 2), [to_min("08:10"), to_min("08:20")])

    def test_suspended_has_no_buses(self):
        self.assertEqual(self.book.next_buses(self.book.get("R10"), 0, 0), [])

    def test_summary_and_warnings(self):
        s = compute_summary(self.book)
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["status"]["Suspended"], 1)
        msgs = " ".join(m for _, m in find_warnings(self.book))
        self.assertIn("suspended", msgs)
        self.assertIn("Hostel", msgs)       # only served by a suspended route

    def test_empty_summary(self):
        self.assertEqual(compute_summary(RouteBook())["total"], 0)


class StorageTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            save_routes(p, [make()])
            routes, notes = load_routes(p)
            self.assertEqual(len(routes), 1)
            self.assertEqual(notes, [])

    def test_missing_file_created(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "nope.json")
            routes, notes = load_routes(p)
            self.assertEqual(routes, [])
            self.assertTrue(os.path.exists(p))

    def test_corrupt_file_recovered(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            with open(p, "w") as f:
                f.write("{ this is not json")
            routes, notes = load_routes(p)
            self.assertEqual(routes, [])
            self.assertTrue(any("damaged" in n for n in notes))
            self.assertTrue(any(".corrupt-" in n for n in os.listdir(d)))


class ImportAndExportTests(unittest.TestCase):
    def test_import_with_errors(self):
        here = os.path.dirname(__file__)
        src = os.path.join(here, "..", "data", "sample_import_with_errors.csv")
        book = RouteBook([make("R1")])
        with tempfile.TemporaryDirectory() as d:
            res = importer.import_csv(src, book, d)
            self.assertEqual(res.added, 2)
            self.assertEqual(res.skipped, 6)
            self.assertTrue(os.path.exists(res.log_path))

    def test_import_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            res = importer.import_csv(os.path.join(d, "none.csv"), RouteBook(), d)
            self.assertEqual(res.added, 0)
            self.assertEqual(res.skipped, 1)

    def test_exports_written(self):
        book = RouteBook([make()])
        with tempfile.TemporaryDirectory() as d:
            for fn in (reports.export_text, reports.export_markdown, reports.export_csv):
                self.assertTrue(os.path.getsize(fn(book, d)) > 0)


if __name__ == "__main__":
    unittest.main()
