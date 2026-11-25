from dataclasses import dataclass, asdict

STATUSES = ("Active", "Delayed", "Suspended")


@dataclass
class Route:
    route_id: str
    name: str
    stops: list          # ordered, first stop -> last stop
    start_time: str      # first departure, "HH:MM"
    end_time: str        # last departure, "HH:MM"
    interval_min: int    # minutes between buses
    capacity: int        # seats per bus
    status: str = "Active"

    def to_dict(self):
        return asdict(self)

    @property
    def is_loop(self):
        return len(self.stops) > 2 and self.stops[0].casefold() == self.stops[-1].casefold()
