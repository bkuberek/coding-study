"""The vendor of the main building's rooms: what it speaks, and when to ask it again."""

from datetime import date
from http import HTTPStatus
from urllib.parse import urlencode

from vendors import Answer, Slot, VendorError, ask_with_retries, get

NAME = "room-vendor"
MAX_REQUESTS = 3
SHORT_WAIT_S = 0.2


def wait_before_retry(answer: Answer) -> float | None:
    """Seconds to wait before asking again; None when asking again will not help."""
    if answer.status == HTTPStatus.TOO_MANY_REQUESTS:
        seconds = _whole_seconds(answer.headers.get("Retry-After"))
        return SHORT_WAIT_S if seconds is None else seconds
    if answer.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return SHORT_WAIT_S
    return None


def _whole_seconds(text: str | None) -> int | None:
    if text is None or not (text.isascii() and text.isdigit()):
        return None
    return int(text)


class RoomVendor:
    name = NAME

    def __init__(self, base_url: str) -> None:
        self._url = f"{base_url}/v1/rooms/availability"

    def open_slots(self, day: date) -> list[Slot]:
        url = f"{self._url}?{urlencode({'date': day.isoformat()})}"
        answer = ask_with_retries(lambda: get(url), wait_before_retry, MAX_REQUESTS)
        if not answer.ok:
            raise VendorError(f"{NAME} answered {answer.status}")
        match answer.json():
            case {"rooms": list(rooms)}:
                return [slot for room in rooms for slot in _open_slots(room)]
            case body:
                raise VendorError(f"{NAME} sent no rooms: {body!r}")


def _open_slots(room: object) -> list[Slot]:
    match room:
        case {"id": str(room_id), "slots": list(slots)}:
            found = (_slot_if_open(room_id, slot) for slot in slots)
            return [slot for slot in found if slot is not None]
        case _:
            raise VendorError(f"{NAME} sent a room it does not document: {room!r}")


def _slot_if_open(room_id: str, slot: object) -> Slot | None:
    match slot:
        case {"status": "open", "start": str(start), "end": str(end)}:
            return Slot(room_id, start, end, NAME)
        case {"status": str()}:
            return None
        case _:
            raise VendorError(f"{NAME} sent a slot it does not document: {slot!r}")
