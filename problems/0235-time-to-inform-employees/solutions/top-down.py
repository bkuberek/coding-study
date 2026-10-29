def num_of_minutes(n: int, head_id: int, manager: list[int], inform_time: list[int]) -> int:
    reports: list[list[int]] = [[] for _ in range(n)]
    for employee, boss in enumerate(manager):
        if boss != -1:
            reports[boss].append(employee)
    longest = 0
    pending = [(head_id, 0)]  # (employee, minute at which they hear the news)
    while pending:
        employee, heard_at = pending.pop()
        longest = max(longest, heard_at)
        passed_on_at = heard_at + inform_time[employee]
        pending.extend((report, passed_on_at) for report in reports[employee])
    return longest
