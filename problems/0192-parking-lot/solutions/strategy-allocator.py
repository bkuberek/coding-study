import heapq
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24
DAILY_CAP_HOURS = 8


class SpotSize(Enum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"


class VehicleType(Enum):
    """Each type lists the spot sizes it fits, smallest first, and its hourly rate in cents."""

    MOTORCYCLE = ((SpotSize.SMALL, SpotSize.MEDIUM, SpotSize.LARGE), 100)
    CAR = ((SpotSize.MEDIUM, SpotSize.LARGE), 250)
    VAN = ((SpotSize.LARGE,), 400)

    def __init__(self, fits: tuple[SpotSize, ...], hourly_rate: int) -> None:
        self.fits = fits
        self.hourly_rate = hourly_rate


@dataclass(frozen=True, slots=True, order=True)
class Spot:
    level: int
    index: int

    def label(self) -> str:
        return f"{self.level}-{self.index}"


@dataclass(frozen=True, slots=True)
class Ticket:
    ticket_id: str
    plate: str
    vehicle: VehicleType
    spot: Spot
    parked_at: int


class PricingPolicy(Protocol):
    def fee(self, vehicle: VehicleType, parked_at: int, left_at: int) -> int: ...


def _billable_hours(parked_at: int, left_at: int) -> int:
    """Started hours, at least one."""
    return max(1, -(-(left_at - parked_at) // SECONDS_PER_HOUR))


class HourlyPricing:
    def fee(self, vehicle: VehicleType, parked_at: int, left_at: int) -> int:
        return _billable_hours(parked_at, left_at) * vehicle.hourly_rate


class DailyCapPricing:
    """Hourly, but each started day costs at most DAILY_CAP_HOURS hours."""

    def fee(self, vehicle: VehicleType, parked_at: int, left_at: int) -> int:
        days, hours = divmod(_billable_hours(parked_at, left_at), HOURS_PER_DAY)
        cap = DAILY_CAP_HOURS * vehicle.hourly_rate
        return days * cap + min(hours * vehicle.hourly_rate, cap)


PRICING_SCHEMES: dict[str, type[PricingPolicy]] = {"HOURLY": HourlyPricing, "DAILY_CAP": DailyCapPricing}


class SpotAllocator:
    """Free spots per size; hands out the smallest fitting size, then the lowest level and index."""

    def __init__(self, layout: list[str]) -> None:
        self._free: dict[SpotSize, list[Spot]] = {size: [] for size in SpotSize}
        self._sizes: dict[Spot, SpotSize] = {}
        for level, row in enumerate(layout):
            for index, code in enumerate(row):
                spot = Spot(level, index)
                self._sizes[spot] = SpotSize(code)
                self._free[self._sizes[spot]].append(spot)
        for spots in self._free.values():
            heapq.heapify(spots)

    def allocate(self, vehicle: VehicleType) -> Spot | None:
        for size in vehicle.fits:
            if self._free[size]:
                return heapq.heappop(self._free[size])
        return None

    def release(self, spot: Spot) -> None:
        heapq.heappush(self._free[self._sizes[spot]], spot)

    def free_count(self, vehicle: VehicleType) -> int:
        return sum(len(self._free[size]) for size in vehicle.fits)


class ParkingLot:
    def __init__(self, levels: list[str]) -> None:
        self._allocator = SpotAllocator(levels)
        self._pricing: PricingPolicy = HourlyPricing()
        self._tickets: dict[str, Ticket] = {}
        self._parked: dict[str, Ticket] = {}  # plate -> open ticket
        self._issued = 0

    def park(self, timestamp: int, plate: str, vehicle_type: str) -> str:
        vehicle = VehicleType.__members__.get(vehicle_type)
        if vehicle is None or plate in self._parked:
            return ""
        spot = self._allocator.allocate(vehicle)
        if spot is None:
            return ""
        self._issued += 1
        ticket = Ticket(f"T{self._issued}", plate, vehicle, spot, timestamp)
        self._tickets[ticket.ticket_id] = ticket
        self._parked[plate] = ticket
        return ticket.ticket_id

    def leave(self, timestamp: int, ticket_id: str) -> int:
        ticket = self._tickets.pop(ticket_id, None)
        if ticket is None:
            return -1
        del self._parked[ticket.plate]
        self._allocator.release(ticket.spot)
        return self._pricing.fee(ticket.vehicle, ticket.parked_at, timestamp)

    def locate(self, plate: str) -> str:
        ticket = self._parked.get(plate)
        return "" if ticket is None else ticket.spot.label()

    def free_spots(self, vehicle_type: str) -> int:
        vehicle = VehicleType.__members__.get(vehicle_type)
        return -1 if vehicle is None else self._allocator.free_count(vehicle)

    def set_pricing(self, scheme: str) -> bool:
        policy = PRICING_SCHEMES.get(scheme)
        if policy is None:
            return False
        self._pricing = policy()
        return True
