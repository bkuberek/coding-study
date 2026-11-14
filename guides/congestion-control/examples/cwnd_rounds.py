"""A congestion window, one round trip at a time, counted in segments.

Slow start doubles the window each round while it is below ssthresh; congestion avoidance adds
one segment per round. Three duplicate ACKs halve it (fast retransmit, then fast recovery); a
timeout drops it to one segment and starts slow start again. The model treats a round as one
whole window sent and acknowledged, which is coarser than the per-ACK rules of RFC 5681, so
here doubling stops at ssthresh instead of passing it.
"""

INITIAL_WINDOW = 4  # segments: RFC 5681's initial window for segments of up to 1,095 bytes
LOSSES = {9: "3 duplicate ACKs", 15: "timeout"}  # the round at whose end each loss is seen

cwnd, ssthresh = INITIAL_WINDOW, 32  # ssthresh starts high; 32 keeps the table short
print("round  cwnd  ssthresh  phase")
for round_number in range(1, 21):
    phase = "slow start" if cwnd < ssthresh else "congestion avoidance"
    print(f"{round_number:>5}  {cwnd:>4}  {ssthresh:>8}  {phase:<20}  {'#' * cwnd}")
    loss = LOSSES.get(round_number)
    if loss is not None:
        ssthresh = max(cwnd // 2, 2)  # half of what was in flight, at least two segments
        cwnd = ssthresh if loss == "3 duplicate ACKs" else 1
        print(f"       {loss}: ssthresh {ssthresh}, cwnd {cwnd}")
    elif cwnd < ssthresh:
        cwnd = min(2 * cwnd, ssthresh)
    else:
        cwnd += 1
