"""The run order of booked transfers, without a bank around them."""

from bank.scheduler import ScheduledTransfer, TransferScheduler


def _due_at(due: int) -> ScheduledTransfer:
    return ScheduledTransfer("payer", "payee", amount=10, due=due)


def test_book_numbers_bookings_from_one() -> None:
    scheduler = TransferScheduler()
    ids = [scheduler.book(_due_at(5)), scheduler.book(_due_at(5))]
    assert ids == ["transfer1", "transfer2"]


def test_take_due_hands_out_the_earliest_due_first() -> None:
    scheduler = TransferScheduler()
    late, early = _due_at(20), _due_at(10)
    scheduler.book(late)
    scheduler.book(early)
    assert scheduler.take_due(20) == [early, late]


def test_take_due_runs_equal_due_times_in_booking_order() -> None:
    scheduler = TransferScheduler()
    first, second = _due_at(10), _due_at(10)
    scheduler.book(first)
    scheduler.book(second)
    assert scheduler.take_due(10) == [first, second]


def test_take_due_keeps_transfers_due_later() -> None:
    scheduler = TransferScheduler()
    scheduler.book(_due_at(11))
    assert scheduler.take_due(10) == []


def test_take_due_skips_a_cancelled_transfer() -> None:
    scheduler = TransferScheduler()
    cancelled = _due_at(10)
    scheduler.book(cancelled)
    scheduler.cancel(cancelled)
    assert scheduler.take_due(10) == []


def test_a_transfer_handed_out_is_no_longer_pending() -> None:
    scheduler = TransferScheduler()
    transfer_id = scheduler.book(_due_at(10))
    scheduler.take_due(10)
    assert scheduler.find_pending(transfer_id) is None
