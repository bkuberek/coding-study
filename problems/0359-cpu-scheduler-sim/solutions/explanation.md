# CPU Scheduler Sim: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| clock-loop | optimal | O(n^2) for shortest job first; O(n log n + T (k + c^2)) for the clock loops, T the ticks simulated | O(n + s) for s timeline segments | default answer; one loop with one queue per core serves round robin and the cores, and a sibling loop with one queue per level serves the feedback queue |

Here `n` is the number of processes, `T` the ticks from 0 to the last completion, `k` the number of feedback queues, `c` the number of cores and `s` the number of timeline segments.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | A workload and the result of the latest run | the processes in add order with their arrival and burst; a run object with each process's first tick and completion, and one core record (segments, last process, switches, busy ticks) |
| 2 | A clock that advances one tick at a time | nothing new in the result: response times read the first ticks, and switches are counted as the segments are recorded |
| 3 | One queue per level | per process, its level and the ticks used at that level |
| 4 | One queue per core | per core, its queue, running process and slice; the run gains a count of migrations and its length |

The choice that keeps the later levels cheap is to record every run through one small "core" object that merges touching segments and counts switches as they happen. The first come and shortest job policies write whole bursts into it, and the clock loops write one tick at a time; the timeline, the switches, the busy time and the utilization all come out of the same record. A second choice is to write round robin as the multicore loop with one core and stealing off, so that the tie rules of level 2 are written once.

## Approach: clock-loop (One clock loop with a ready queue per core)

### Intuition

A scheduler is a rule for one decision: who runs next. The non-preemptive policies make that decision only when a process finishes, so they can jump from one completion to the next. The preemptive ones also decide when a time slice ends, when a higher queue fills, at a boost or when a core runs dry, and several of those can happen at the same tick. Advancing a clock one tick at a time and settling each tick in the fixed order of the statement makes every tie explicit: whoever reads the code can point to the line that decides it.

### Algorithm

1. Level 1: store the processes in add order. First come, first served sorts them by arrival, stably, so equal arrivals stay in add order, and runs each from `max(now, arrival)` to its end. Shortest job first repeats: take the arrived processes that are not done; if there are none, jump to the next arrival; otherwise run the one with the smallest `(burst, arrival, add position)` to completion. Each run records into a fresh run object, which replaces the previous one.
2. Recording: when process `p` runs on a core from `start` to `end`, extend the core's last segment if it is `p` and ends at `start`; otherwise count a switch when the core's previous process is not `p`, and open a new segment. Add the ticks to the core's busy time, and remember the first tick of `p`.
3. Level 2, per tick `t`: if the running process has no work left, it is done at `t`; else if its slice has `quantum` ticks, take it off the CPU. Queue the arrivals of `t` in add order, then the preempted process, then dispatch the front of the queue with a fresh slice. Run one tick.
4. Level 3, per tick `t`: the same, with a queue per level. A process that used its allotment moves down one level (not below the last) with its count reset. After the arrivals and the demoted process are queued, a boost tick joins all the queues into queue 0, top first, and resets every level and count, the running process's too. Then, if a queue above the running process's level is not empty, the running process goes to the back of its own queue with its count kept. Dispatch from the highest non-empty queue.
5. Level 4: the step 3 loop, with arrays of queues, running processes and slices. Each arrival goes to the core with the smallest load, counting the running process, the queue and a process preempted at this tick; then each core queues its preempted process and dispatches; then, with stealing on, each idle core in order takes the back of the longest queue (lowest core on ties) and counts a migration. The run ends at the tick when no process is left; utilization is a core's busy ticks over that tick, reduced by their greatest common divisor.

### Correctness

Each policy is the statement's rule applied at every moment the rule can change its answer. Between two such moments nothing can change: a running process keeps running, queues only grow by arrivals, and arrivals happen only at whole ticks. The tick loops visit every tick, so they cannot miss a moment; the non-preemptive loop visits every completion and jumps idle stretches only to the next arrival, where the next decision falls.

Ties are decided by the order of the steps. For round robin, queuing the arrivals before the preempted process is the statement's rule, and since the steps run in that order every time, the queue is the same in every language. For the feedback queue, a demoted process is queued before the boost check, so a boost at the same tick lifts it; the preemption check runs after the boost, so a boosted running process is never preempted at that tick, since nothing is above queue 0.

The merge rule makes a segment maximal: a new segment starts only when the core ran a different process before or was idle at the tick before, which are exactly the boundaries of the statement. A switch is counted exactly when a new segment starts on a core whose previous process differs, which is the statement's definition, idle gaps included.

Allotments: a process's count is reset at arrival, demotion and boost and nowhere else, and it grows by one for each tick it runs, so it is the number of ticks used at its current level over all its turns. Demotion happens when the count reaches the level's allotment, and a preempted process keeps its count, so its next turn ends after the rest of its allotment.

### Complexity

- Time: O(n^2) for shortest job first; O(n log n + T (k + c^2)) for the clock loops, T the ticks simulated — shortest job first scans the remaining processes at each of its `n` decisions; the clock loops sort the arrivals once and then do, per tick, a check of up to `k` queues for a preemption or a dispatch, and for each arrival or idle core a scan of the `c` cores. A boost joins the queues in O(n), at most once per period.
- Space: O(n + s) for s timeline segments — per-process counters, queues that hold each process at most once, and the segments. `s` is at most the number of ticks, and in practice the number of dispatches.

### Trade-offs

- A tick loop is the simplest correct simulation, and its cost is the length of the run, not the number of events. An event-driven simulation jumps from event to event (an arrival, the end of a slice, a completion, a boost) with a priority queue of times, which costs O(e log e) for `e` events and wins when bursts are long and quanta are large. It must then handle all the events of one instant together, in the same order as the tick loop.
- Shortest job first could keep the ready processes in a heap ordered by `(burst, arrival, position)` for O(n log n). With at most 100 processes the scan is simpler and fast enough.
- A real scheduler cannot know bursts: shortest job first is the yardstick, and the feedback queue is how a scheduler approximates it by watching how long each process runs.
- Per-core queues avoid one shared, locked queue and keep each process near its cached data. A single shared queue balances perfectly but makes every core contend for it and moves processes between cores all the time.

### Pitfalls and edge cases

- Tie order in round robin: the processes that arrive at the tick a slice ends go before the preempted process. Queuing the preempted process first is the most common mistake, and the hidden cases are full of arrivals at slice boundaries.
- A process whose last tick is also the last tick of its slice is done, not preempted: check "no work left" before "slice used up".
- A process that continues after its own slice, because nobody else waits, is one segment and no switch; but a process that starts after an idle gap is a switch if the CPU's previous process was another one.
- Measure waiting, turnaround and response from the arrival, not from time 0; the hidden cases have late arrivals.
- Shortest job first is non-preemptive and only looks at processes that have arrived, including one that arrives at the very tick the CPU frees up.
- In the feedback queue, a preempted process keeps the allotment it has used and goes to the back of its own queue; it is not demoted. The running process is boosted too. The boost clock counts idle ticks.
- Placement counts the process whose slice ended at this tick, which has not been queued again yet; leaving it out sends an arrival to a busy core.
- Utilization divides by the length of the whole run, from time 0 to the last completion, not by the core's own last tick; an unused core is `0/1`.
- Answers are about the latest run: a process added after it gives `-1`, and averages divide by the number of processes in that run.

### Language notes

- Queues: Python uses `deque`; TypeScript uses arrays with `shift`, which is linear in the length but cheap for at most 100 processes; Java and Kotlin use `ArrayDeque`, whose `pollLast` and `removeLast` take the back of a queue for a steal; Go uses slices, and Rust `VecDeque` with `pop_back`.
- Fractions: Python has `math.gcd`; the other languages write the three-line Euclid loop. All values fit in a 32-bit integer: a run is at most about 1.1 * 10^5 ticks, and a sum of 100 turnarounds stays below 1.2 * 10^7.
- `runMulticore` returns a list of lists of strings: `List<List<String>>` in Java and Kotlin, `[][]string` in Go, `Vec<Vec<String>>` in Rust. Go returns `[]string{}` rather than `nil` for an empty core, although the runner encodes both as `[]`.
- The per-core record of segments is a small class in every language; Rust keeps the segments as `(String, i32, i32)` tuples and formats them at the end.

## Further reading

- R. H. Arpaci-Dusseau and A. C. Arpaci-Dusseau, [Operating Systems: Three Easy Pieces](https://pages.cs.wisc.edu/~remzi/OSTEP/), version 1.10, free online:
  - [Scheduling: Introduction](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched.pdf): turnaround and response time, first in first out and the convoy effect, shortest job first and its optimality when all jobs arrive together, round robin, the time slice and amortizing the cost of a context switch.
  - [Scheduling: The Multi-Level Feedback Queue](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-mlfq.pdf): the rules of the feedback queue, the allotment counted over all turns at a level, starvation and the priority boost.
  - [Multiprocessor Scheduling (Advanced)](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-multi.pdf): single-queue and multi-queue scheduling, cache affinity, load imbalance, migration and work stealing.
- F. J. Corbató, M. Merwin-Daggett and R. C. Daley, "An experimental time-sharing system", Proceedings of the Spring Joint Computer Conference, May 1962, [doi:10.1145/1460833.1460871](https://doi.org/10.1145/1460833.1460871): the time-sharing system in which, as the textbook above recounts, the multi-level feedback queue was first described.
- R. D. Blumofe and C. E. Leiserson, "Scheduling multithreaded computations by work stealing", Journal of the ACM 46(5), 1999, [doi:10.1145/324133.324234](https://doi.org/10.1145/324133.324234): processors that need work steal it from other processors, with the first provably good work-stealing scheduler for computations with dependencies.
