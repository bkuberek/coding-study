def job_scheduling(start_time: list[int], end_time: list[int], profit: list[int]) -> int:
    jobs = sorted(zip(end_time, start_time, profit))
    # best[i] is the most profit from the first i jobs in end-time order.
    best = [0] * (len(jobs) + 1)
    for i, (_, start, pay) in enumerate(jobs):
        # Walk back to the last job that ends no later than this one starts.
        compatible = i - 1
        while compatible >= 0 and jobs[compatible][0] > start:
            compatible -= 1
        best[i + 1] = max(best[i], pay + best[compatible + 1])
    return best[len(jobs)]
