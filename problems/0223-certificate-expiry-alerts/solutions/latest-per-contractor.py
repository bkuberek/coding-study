from datetime import date, timedelta


def certificate_alerts(
    contractor_ids: list[str], expiry_dates: list[date], as_of_date: date, window_days: int
) -> list[list[str]]:
    latest: dict[str, date] = {}  # a renewal supersedes: only the latest expiry per contractor counts
    for contractor, expiry in zip(contractor_ids, expiry_dates, strict=True):
        if contractor not in latest or expiry > latest[contractor]:
            latest[contractor] = expiry
    horizon = as_of_date + timedelta(days=window_days)
    flagged = sorted((expiry, contractor) for contractor, expiry in latest.items() if expiry <= horizon)
    return [
        [contractor, expiry.isoformat(), "expired" if expiry <= as_of_date else "expiring"]
        for expiry, contractor in flagged
    ]
