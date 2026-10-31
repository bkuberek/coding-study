"""Transfers booked to run later, handed out in the order they fall due."""

import heapq
from dataclasses import dataclass


@dataclass(slots=True, eq=False)
class ScheduledTransfer:
    """Money booked to move from `source_id` to `target_id` at time `due`.

    The ids are those given at booking time; a merge may hand them to another account.
    """

    source_id: str
    target_id: str
    amount: int
    due: int
    pending: bool = True


class TransferScheduler:
    """Numbers booked transfers and hands them out by due time, ties in booking order.

    A cancelled transfer stays in the queue and is dropped when it reaches the front,
    since a heap can only remove its front cheaply.
    """

    def __init__(self) -> None:
        self._booked: dict[str, ScheduledTransfer] = {}
        self._queue: list[tuple[int, int, ScheduledTransfer]] = []

    def book(self, transfer: ScheduledTransfer) -> str:
        """Queue `transfer` and return its id, `transfer<k>` for the k-th booking."""
        number = len(self._booked) + 1
        transfer_id = f"transfer{number}"
        self._booked[transfer_id] = transfer
        heapq.heappush(self._queue, (transfer.due, number, transfer))
        return transfer_id

    def find_pending(self, transfer_id: str) -> ScheduledTransfer | None:
        transfer = self._booked.get(transfer_id)
        return transfer if transfer is not None and transfer.pending else None

    def cancel(self, transfer: ScheduledTransfer) -> None:
        transfer.pending = False

    def take_due(self, timestamp: int) -> list[ScheduledTransfer]:
        """Remove and return the pending transfers due by `timestamp`, in run order."""
        due: list[ScheduledTransfer] = []
        while self._queue and self._queue[0][0] <= timestamp:
            _, _, transfer = heapq.heappop(self._queue)
            if transfer.pending:
                transfer.pending = False
                due.append(transfer)
        return due
