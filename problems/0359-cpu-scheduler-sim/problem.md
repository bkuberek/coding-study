# CPU Scheduler Sim

## Statement

Build `CpuScheduler`, a simulator of the part of an operating system that decides which program runs on the processor next. You describe a set of programs, run the simulation under one scheduling policy, and then ask how long each program waited. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**What is a process?** A *process* is a program that is running: the operating system's unit of work. Here a process has a name, an **arrival** time (when it asks for the processor) and a **burst** (how many ticks of processor time it needs before it is done). The processes in this problem only compute: they never wait for a disk or a network, so a process that has arrived is always ready to run until its burst is used up.

**What is a CPU scheduler?** A processor (a *CPU*, or a *core*) runs one process at a time. When several processes are ready, they wait in a *ready queue*, and the *scheduler* is the rule that picks the next one. Different rules finish the same work in a different order, and that changes how long each process waits. A *non-preemptive* scheduler lets a process run until it is done; a *preemptive* one may stop a process (*preempt* it) to run another, and put it back to wait.

**Time.** Time is a whole number of *ticks*, starting at `0`; there is no clock to read, every time is given as data. "A process runs during tick `t`" means from time `t` to time `t + 1`. A process with a burst of 3 that starts at time 5 and is never stopped runs during ticks 5, 6 and 7 and is done at time 8. When no process is ready, the CPU is *idle*.

**The measures.** For each process, with *completion* the time its last tick ends:

- **turnaround time** = completion - arrival: how long the process was in the system;
- **waiting time** = turnaround - burst: the ticks it spent ready but not running;
- **response time** (from level 2) = the time of its first tick on a CPU - arrival: how long before it got any service.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `CpuScheduler()`: creates a simulator with no processes.
- A **process name** is 1 to 8 letters and digits, such as `A`, `P7` or `web2`, and names are compared exactly.
- Times, bursts and the other numbers are integers. Each level's section describes the methods it adds and their parameters.

## Output

- **The workload and the latest run.** Processes are added to a *workload*, and a run simulates the whole workload under one policy and keeps its result. The questions about times answer for the **latest run** only: a process added after it is not part of it until the next run.
- **A timeline** is a list of *segments*, in time order, each written `name:start-end`: the process `name` ran during the ticks from `start` up to but not including `end`. A segment is as long as possible: two touching stretches of the same process on the same CPU are one segment. Idle time is not listed. `["A:0-6", "B:6-8"]` means A ran from 0 to 6 and B from 6 to 8.
- **An average** is an exact fraction written `p/q`: the sum of the values over the number of processes in the run, in lowest terms, with `q` at least 1. A whole number is written over 1: `11/3`, `3/2`, `5/1`, `0/1`.
- **Absent values.** Before the first run, a question about a time returns `-1`, an average returns `""`, and a count returns `-1`. A process that is not in the latest run also has the time `-1`.

## Level 1: First come, first served and shortest job first

- `addProcess(pid, arrival, burst)`: adds a process to the workload and returns `true`. If a process with the name `pid` is already in the workload, it returns `false` and changes nothing. The order in which processes are added is the *add order*, used below to break ties.
- `runFcfs()`: simulates **first come, first served** on the workload and returns its timeline. Whenever the CPU is free at time `t`, it takes, among the processes that have arrived (arrival `<= t`) and are not done, the one that arrived first; on equal arrivals, the one added first. That process runs to completion. When no process has arrived, the CPU idles until the next arrival.
- `runSjf()`: simulates **shortest job first** and returns its timeline. Whenever the CPU is free at time `t`, it takes, among the processes that have arrived and are not done, the one with the smallest burst; on equal bursts, the earlier arrival; then the one added first. It is non-preemptive: the chosen process runs to completion, even if a shorter one arrives meanwhile. A process that arrives at the very tick the CPU frees up is a candidate.
- `waitingTime(pid)` and `turnaroundTime(pid)`: the waiting and turnaround time of the process `pid` in the latest run.
- `averageWaiting()` and `averageTurnaround()`: the averages over the processes of the latest run.

**A worked example, by hand.** Three processes arrive: `A` at 0 needing 6 ticks, `B` at 1 needing 2, `C` at 2 needing 1. Under first come, first served, `A` runs from 0 to 6, `B` from 6 to 8 and `C` from 8 to 9.

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|------------|---------|
| A | 0 | 6 | 6 | 6 - 0 = 6 | 6 - 6 = 0 |
| B | 1 | 2 | 8 | 8 - 1 = 7 | 7 - 2 = 5 |
| C | 2 | 1 | 9 | 9 - 2 = 7 | 7 - 1 = 6 |

The average waiting time is (0 + 5 + 6) / 3 = `11/3`. `B` and `C` need three ticks between them, yet they wait 11 ticks in total behind `A`: short jobs stuck behind a long one is the **convoy effect**. Shortest job first picks the shortest *ready* job, so it helps when several jobs wait at once: at time 6, `C` goes before `B`.

When every process arrives at the same time, running the shortest burst first gives the smallest average waiting time of any order, because each burst is waited for by every job that runs after it. The price is that a long job can wait as long as shorter jobs keep arriving: it can *starve*.

### Example 1

<!-- case: ex1 -->

The worked example above. Under shortest job first, `A` still runs first, because at time 0 it is the only process that has arrived and the scheduler never stops it; at time 6 both `B` and `C` are ready and the shorter `C` goes first.

### Example 2

<!-- case: ex2 -->

Before any run, the questions answer `-1` and `""`. Adding a second `Q` returns `false`. `P`, `Q` and `R` all arrive at time 0, so first come, first served runs them in the order added and the long `P` makes the others wait (average waiting `5/1`); shortest job first runs `R`, `Q`, `P` and the average falls to `3/2`. `S` arrives at 20, after the others are done, so the CPU is idle from 13 to 20 and `S` waits for nothing.

## Level 2: Round robin

A scheduler that runs every job to completion makes the last job wait for all the others before it gets any service at all. **Round robin** gives each ready process a turn of at most `quantum` ticks (the *time slice*), and then moves on.

- `runRoundRobin(quantum)`: simulates round robin with a time slice of `quantum` ticks and returns its timeline. The ready queue is first in, first out. At every time `t`, in this order:
  1. If the running process has finished its burst, it is done. Otherwise, if it has now run `quantum` ticks since it was last dispatched, it is preempted.
  2. The processes that arrive at `t` join the back of the queue, in add order.
  3. A process preempted in step 1 joins the back of the queue, **after** the arrivals of step 2.
  4. If the CPU is free, the process at the front of the queue is *dispatched*: it runs from `t` with a fresh time slice. If the queue is empty, the CPU is idle.

  A process whose quantum ends while the queue is empty is preempted, queued and dispatched again at once: it simply continues, and its timeline segment goes on.
- `responseTime(pid)`: the response time of `pid` in the latest run (any policy).
- `averageResponse()`: the average response time of the latest run.
- `contextSwitches()`: the number of **context switches** in the latest run. A switch is a CPU changing from one process to a *different* process: each time a CPU starts a process that is not the last process it ran. The first process a CPU runs is not a switch; a process that continues after its own quantum is not one; and idle time in between does not matter: if `A` finishes, the CPU idles, and `B` starts later, that is one switch.

**The trade-off.** A short quantum gives every process a turn soon, so response times are low. But round robin stretches every job out: when all jobs are of similar length, each finishes near the end, and the average turnaround is worse than with first come, first served. A context switch also costs real time (saving and restoring a process, and refilling caches), which this simulation leaves out: a quantum must be long enough that the switches are a small share of the time, and short enough to keep response times low.

### Example 1

<!-- case: ex3 -->

With a quantum of 2: `A` runs 0 to 2. At time 2, `C` arrives and `A`'s quantum ends, so the queue becomes `B`, `C`, `A`: the arrival goes before the preempted process. `B` runs 2 to 4, `C` finishes at 5, then `A`, `B` and `A` again. Each process gets its first tick within 2 ticks of arriving. The timeline has six segments, so five switches.

### Example 2

<!-- case: ex4 -->

Three jobs of 3 ticks arrive together. First come, first served gives an average response of `3/1` and turnaround of `6/1` with 2 switches; round robin with a quantum of 1 gives a response of `1/1`, but every job finishes near the end, so the turnaround rises to `8/1`, at the cost of 8 switches. Then `D` arrives at 20 alone: its quantum ends with nobody waiting, so it continues in one segment `D:20-25`. The switch from `C` to `D` counts, even though the CPU was idle in between.

## Level 3: Multi-level feedback queue

Shortest job first needs the bursts in advance, which a real scheduler does not know. A **multi-level feedback queue** (MLFQ) learns them as it goes: it assumes a new process is short and gives it high priority, and moves it down each time it uses up its share of the CPU.

- `runMlfq(quanta, boostPeriod)`: simulates a feedback queue and returns its timeline. `quanta` has one entry per **queue**: queue 0 has the highest priority, and `quanta[i]` is the **allotment** of queue `i`, the number of ticks a process may run at that level before it is moved down. `boostPeriod` is the period of the priority boost, `0` for none.

The rules:

- **Priority.** The CPU always runs a process from the highest-priority queue that is not empty. Within a queue, processes take turns in first in, first out order.
- **Arrival.** A new process joins the back of queue 0 with a fresh allotment.
- **Demotion.** A process at queue `i` that has run `quanta[i]` ticks at that level, counted over all its turns at the level, is moved to the back of queue `i + 1` with a fresh allotment. In the lowest queue it stays there, with a fresh allotment, at the back of that queue.
- **Preemption.** When a queue of higher priority than the running process's queue is not empty, the running process is preempted at once: it goes to the back of its own queue and **keeps the part of its allotment it has used**. Its next turn ends when the allotment is used up.
- **Boost.** At every multiple of `boostPeriod` (times `boostPeriod`, `2 * boostPeriod`, ...; never at time 0), every process that has arrived and is not done moves to queue 0 with a fresh allotment, including the running process, which stays on the CPU. Queue 0 becomes the old queue 0, then the old queue 1, and so on down, each in its own order. The boost clock counts every tick, busy or idle.

At every time `t`, in this order:

1. If the running process has finished, it is done. Otherwise, if it has used its allotment, it is demoted and leaves the CPU.
2. The processes that arrive at `t` join queue 0, in add order.
3. A process demoted in step 1 joins the back of its new queue.
4. If `t` is a boost time, the boost happens.
5. If the running process is in a lower queue than some process that waits, it is preempted.
6. If the CPU is free, the front process of the highest non-empty queue runs from `t`.

With a single queue, `runMlfq([q], 0)` is round robin with a quantum of `q`.

**Why the boost?** Without it, a long job in a low queue runs only when every higher queue is empty, so a steady stream of short jobs can starve it. The boost lifts everyone back up regularly, so every job gets a turn within a bounded time, at the cost of some delay to the short jobs. How often to boost is a tuning choice with no right answer.

### Example 1

<!-- case: ex5 -->

`A` starts in queue 0, uses its 2 ticks and moves to queue 1, uses 4 more and moves to queue 2: since nobody else waits, it never leaves the CPU, and the timeline shows one segment `A:0-7`. At 7, `B` arrives in queue 0 and preempts `A` at once. `B` uses its 2 ticks, moves to queue 1, and still runs first, since queue 1 is above `A`'s queue 2. `A` then resumes in queue 2, where it had used 1 of its 8 ticks.

### Example 2

<!-- case: ex6 -->

A long job `A` and a short job arriving every two ticks. Without a boost, `A` drops to queue 1 at time 2 and waits until every short job is done: its turnaround is 18. With a boost every 4 ticks, `A` is lifted back to queue 0 at times 4 and 8 and takes turns with the short jobs: its turnaround falls to 14, and the average over all jobs rises from `30/7` to `38/7`, because the short jobs now wait for `A`.

## Level 4: Several cores

A machine has several cores. A simple and scalable design gives each core its own ready queue and its own scheduler, here round robin, and places each new process on one core.

- `runMulticore(cores, quantum, steal)`: simulates `cores` cores, numbered from 0, each running round robin with a quantum of `quantum` over its own queue, and returns one timeline per core, in core order. `steal` turns work stealing on or off.

The rules:

- **Placement.** An arriving process joins the back of the queue of the core with the smallest **load**: the number of processes placed on that core that are not done (the running one, the queued ones, and one whose quantum just ended). On equal load, the lowest-numbered core. Processes arriving at the same time are placed one by one, in add order, each seeing the loads after the previous ones.
- **Stealing.** When `steal` is `true`, a core that would be idle after dispatching from its own queue steals: it takes the **last** process of the longest queue of another core (lowest-numbered core on equal lengths) and runs it from that tick with a fresh time slice. The process then belongs to the thief. A core steals only when some queue holds a waiting process. Each steal is one **migration**.

At every time `t`, in this order:

1. For each core, in core order: its running process is done, or is preempted when its quantum ends.
2. The processes that arrive at `t` are placed, in add order.
3. Each core queues its preempted process at the back, after its new arrivals, and dispatches the front of its queue if it is free.
4. If stealing is on, each core that is still idle, in core order, steals.

- `utilization(core)`: the share of the latest run during which `core` was busy: its busy ticks over the length of the run, from time 0 to the completion of the last process, as a fraction in lowest terms. A core that never ran is `0/1`. A run on one CPU (any earlier method) has core 0 only. `""` for a core that the latest run does not have, or before any run.
- `migrations()`: the number of steals in the latest run; `0` for a run without stealing.

The questions of the earlier levels answer for a multicore run too: `contextSwitches()` adds up the switches of every core, and each core counts its own.

**Load balancing.** Separate queues keep each process on one core, where its data stays in that core's caches, and avoid one shared lock. But a count of processes says nothing about how much work each one has left, so one core can run out of work while another has a long queue. Stealing fixes the imbalance, at the price of moving a process away from its cached data. Taking the last process of a queue takes the one that would otherwise have waited longest.

### Example 1

<!-- case: ex7 -->

`A`, `B` and `C` arrive at 0: `A` goes to core 0, `B` to core 1, and `C` to core 0 (both cores have a load of 1). At 1, `D` goes to core 1, whose load is 1 against 2. Without stealing, core 1 runs out of work at 4 while core 0 alternates `A` and `C` until 12: core 1 is busy `1/3` of the time. With stealing, at 4 the idle core 1 takes `C` from the back of core 0's queue: both cores are busy to the end, the run ends at 8, and the average turnaround falls from `27/4` to `21/4`.

### Example 2

<!-- case: ex8 -->

Five processes arrive at 0 on three cores: core 0 gets `A` and `D`, core 1 `B` and `E`, core 2 `C`. `F` arrives at 2 and goes to core 1, the lowest of the two cores with a load of 1. At 4, core 2 has finished `C` and its queue is empty, so it steals `A`, the only waiting process, from core 0. Every core is busy until 6.

## Constraints

- At most 100 processes are added in a test, and at most 200 calls are made.
- `0 <= arrival <= 10^4` and `1 <= burst <= 1000`.
- `1 <= quantum <= 100`; `quanta` has 1 to 5 entries, each from 1 to 100; `0 <= boostPeriod <= 10^4`; `1 <= cores <= 8`.
- Every run happens when the workload has at least one process.

## Follow-ups

- Shortest time-to-completion first is the preemptive version of shortest job first: a new process that needs less than the running one has left takes the CPU. How would you add it, and what does it do to starvation?
- Add a context-switch cost of `c` ticks during which the CPU does no work. How does the best quantum for average turnaround change as `c` grows?
- A process that gives up the CPU just before its allotment ends would stay in queue 0 forever under a rule that resets the allotment on every turn. Why does counting the allotment over all turns at a level close that loophole?
- Placement by load counts processes, not work. What would placement by the sum of remaining bursts gain, and why can a real kernel not do it?
- Real feedback schedulers raise the quantum as the priority falls. Which jobs does that help, and which does it hurt?

## Hints

### Hint 1

Do the worked example by hand on paper: draw a line of ticks, mark where each process runs, and write down each completion time. Turnaround is completion minus arrival, and waiting is turnaround minus burst. Everything else in this problem is about computing those completion times under different rules.

### Hint 2

For the two non-preemptive policies you only need a current time. Repeat: find the processes that have arrived and are not done; if there are none, jump the time to the next arrival; otherwise pick one with the policy's rule, run it to completion and move the time to its end.

### Hint 3

For the preemptive policies, move time forward one tick at a time. At each tick, do exactly the steps the statement lists, in the same order: the order is what decides the ties. Then let the running process run one tick: lower its remaining work and count the ticks of its slice.

### Hint 4

Keep the timeline as a list of `[name, start, end]`. When a process runs during tick `t`, extend the last segment if it is the same process and ends at `t`; otherwise start a new one, and count a switch if this CPU's previous process was a different one. Remember the first tick of each process, for the response time.

### Hint 5

For the feedback queue, keep one queue per level, and for each process its level and the ticks it has used at that level. Demotion and boost reset that count; preemption does not.

### Hint 6

For several cores, keep per core: a queue, the running process, the ticks of its slice, and its timeline. Compute the load from these, including a process whose quantum ended at this tick and has not been queued yet.

### Hint 7

One loop serves round robin and the cores: round robin is one core with stealing off. Each tick, for every core, finish or preempt; place the arrivals by load; requeue the preempted process after the arrivals and dispatch; then, when stealing is on, let each idle core take the back of the longest other queue. Run one tick on each busy core and record it. Utilization is a core's busy ticks over the time the last process finished, reduced by the greatest common divisor.
