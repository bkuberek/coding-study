"""One answer from any number of vendors, none of which can take another down."""

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from operator import attrgetter

from vendors import RoomSource, Slot, VendorError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomAvailability:
    slots: list[Slot]
    unavailable: list[str]


def room_availability(day: date, vendors: Sequence[RoomSource]) -> RoomAvailability:
    """Asks every vendor at once; one with no usable answer goes in `unavailable`."""
    with ThreadPoolExecutor(max_workers=len(vendors)) as pool:
        asked = {vendor.name: pool.submit(vendor.open_slots, day) for vendor in vendors}
    slots: list[Slot] = []
    unavailable: list[str] = []
    for name, answer in asked.items():
        try:
            slots.extend(answer.result())
        except VendorError as error:
            log.warning("%s is unavailable: %s", name, error)
            unavailable.append(name)
    return RoomAvailability(
        sorted(slots, key=attrgetter("start", "room")), sorted(unavailable)
    )
