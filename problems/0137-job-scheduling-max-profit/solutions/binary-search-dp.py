from bisect import bisect_right


def job_scheduling(start_time: list[int], end_time: list[int], profit: list[int]) -> int:
    jobs = sorted(zip(end_time, start_time, profit))
    ends = [end for end, _, _ in jobs]
    # best[i] is the most profit from the first i jobs in end-time order.
    best = [0] * (len(jobs) + 1)
    for i, (_, start, pay) in enumerate(jobs):
        # The number of jobs that end no later than this one starts (all of them come first).
        compatible = bisect_right(ends, start, hi=i)
        best[i + 1] = max(best[i], pay + best[compatible])
    return best[len(jobs)]
