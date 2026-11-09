"""The vendor of the building next door, which says most things in the body of a 200."""

from datetime import date
from urllib.parse import urlencode

from vendors import Slot, VendorError, ask_with_retries, get

NAME = "annex-vendor"
MAX_REQUESTS = 2
MINUTES_PER_HOUR = 60
MS_PER_SECOND = 1000


def wait_before_retry(body: object) -> float | None:
    """Seconds it asks you to wait before asking again; None if it does not ask."""
    match body:
        case {
            "ok": False,
            "error": {"code": "BUSY", "retry_after_ms": int() | float() as ms},
        }:
            return ms / MS_PER_SECOND
        case _:
            return None


class AnnexVendor:
    name = NAME

    def __init__(self, base_url: str) -> None:
        self._url = f"{base_url}/v2/spaces/open"

    def open_slots(self, day: date) -> list[Slot]:
        url = f"{self._url}?{urlencode({'day': day.strftime('%Y%m%d')})}"
        match ask_with_retries(lambda: _body(url), wait_before_retry, MAX_REQUESTS):
            case {"ok": True, "result": {"spaces": list(spaces)}}:
                return [slot for space in spaces for slot in _open_slots(space)]
            case body:
                raise VendorError(f"{NAME} gave no spaces: {body!r}")


def _body(url: str) -> object:
    """Its 5xx means down for maintenance, so any status but 2xx ends the asking."""
    answer = get(url)
    if not answer.ok:
        raise VendorError(f"{NAME} answered {answer.status}")
    return answer.json()


def _open_slots(space: object) -> list[Slot]:
    match space:
        case {"code": str(code), "open": list(windows)}:
            return [_slot(code, window) for window in windows]
        case _:
            raise VendorError(f"{NAME} sent a space it does not document: {space!r}")


def _slot(code: str, window: object) -> Slot:
    match window:
        case {"from_minute": int(start), "minutes": int(length)}:
            return Slot(code, _clock(start), _clock(start + length), NAME)
        case _:
            raise VendorError(f"{NAME} sent a window it does not document: {window!r}")


def _clock(minutes_since_midnight: int) -> str:
    hours, minutes = divmod(minutes_since_midnight, MINUTES_PER_HOUR)
    return f"{hours:02d}:{minutes:02d}"
