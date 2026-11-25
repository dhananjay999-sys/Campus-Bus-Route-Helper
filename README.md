# Campus Bus Route Helper

A terminal app for storing campus bus routes and finding which bus serves a stop.
Pure Python 3.10+ standard library - nothing to install.

## Run it

```bash
python main.py
```

Windows users can use `py main.py`. Set `NO_COLOR=1` if your terminal shows odd characters.

## What it does

- Add, edit, delete and list routes (with paging for long lists)
- Search by stop name (partial, case-insensitive) or filter by keyword/status
- "Find a ride": routes that actually go from stop A to stop B, direction-aware, with the next bus
- Next buses at any stop for a given time
- Summary report: totals, averages, busiest stops, frequency trend, daily seat capacity
- Warnings: delayed/suspended routes, long waits, short service windows, odd capacities, stops with no running service
- Export a text audit log, Markdown report and CSV into `exports/`
- Bulk CSV import with a row-by-row error log in `logs/`
- Data saved to `data/routes.json` automatically; a damaged file is backed up and replaced, not a crash

## Try the demo data

`data/routes.json` ships with 42 routes (including edge cases like 1-minute intervals,
a 20-stop tour and a loop). To try the importer, choose option 10 and enter:

```
data/sample_import_with_errors.csv
```

It has 2 good rows and 6 deliberately bad ones, so you can see the error log.
`python scripts/make_sample_data.py` rebuilds all the sample files.

## Tests

```bash
python -m unittest discover -s tests
```

## CSV format

`route_id,name,stops,start_time,end_time,interval_min,capacity,status` - stops are separated by `|`.

## Layout

```
main.py            entry point
busapp/models.py       Route dataclass
busapp/validation.py   all input checks
busapp/storage.py      JSON load/save (atomic writes, corruption recovery)
busapp/logic.py        search, next-bus times, analytics, warnings
busapp/reports.py      summary text + exports
busapp/importer.py     CSV import
busapp/ui.py           menus and prompts
```

## Assumption

Bus-to-bus travel time between neighbouring stops is assumed to be 3 minutes (`MIN_PER_STOP` in `logic.py`).
