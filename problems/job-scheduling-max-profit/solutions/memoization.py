from bisect import bisect_left
from functools import cache


def job_scheduling(start_time: list[int], end_time: list[int], profit: list[int]) -> int:
    jobs = sorted(zip(start_time, end_time, profit))
    starts = [start for start, _, _ in jobs]

    @cache
    def best_from(index: int) -> int:
        # The most profit from jobs[index:], all of which start at or after jobs[index].
        if index == len(jobs):
            return 0
        _, end, pay = jobs[index]
        # The first job that starts once this one has ended.
        following = bisect_left(starts, end, lo=index + 1)
        return max(best_from(index + 1), pay + best_from(following))

    return best_from(0)
