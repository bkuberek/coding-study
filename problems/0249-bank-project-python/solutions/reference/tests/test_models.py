"""Balance history lookups, the part of the models with boundaries."""

from bank.models import Account, BalanceHistory


def test_history_has_no_balance_before_its_first_change() -> None:
    history = BalanceHistory()
    history.record(10, 0)
    assert history.balance_at(9) is None


def test_history_keeps_the_last_change_of_a_moment() -> None:
    history = BalanceHistory()
    history.record(10, 5)
    history.record(10, 8)
    assert history.balance_at(10) == 8


def test_history_holds_a_balance_until_the_next_change() -> None:
    history = BalanceHistory()
    history.record(10, 5)
    history.record(20, 8)
    assert history.balance_at(19) == 5


def test_a_new_account_starts_at_zero() -> None:
    account = Account("ivy", created_at=10)
    assert account.balance_at(10) == 0


def test_a_merged_away_account_has_no_balance_from_the_merge_on() -> None:
    kept, absorbed = Account("kept", created_at=1), Account("gone", created_at=2)
    kept.absorb(absorbed, timestamp=30)
    assert absorbed.balance_at(30) is None


def test_a_merged_away_account_answers_for_times_before_the_merge() -> None:
    kept, absorbed = Account("kept", created_at=1), Account("gone", created_at=2)
    absorbed.deposit(5, 40)
    kept.absorb(absorbed, timestamp=30)
    assert absorbed.balance_at(29) == 40
