import java.util.*;

/**
 * A workload of processes and the result of the latest run over it.
 *
 * <p>First come, first served and shortest job first run each process to completion, so they jump
 * from one completion to the next. Round robin, the feedback queue and the cores advance a clock
 * one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
 * the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
 * then a steal. One core records its segments, merging a slice that continues the one before.
 * Round robin is the case of one core without stealing.
 */
public class CpuScheduler {
    private static final class Segment {
        final String pid;
        final int start;
        int end;

        Segment(String pid, int start, int end) {
            this.pid = pid;
            this.start = start;
            this.end = end;
        }
    }

    private static final class Core {
        final List<Segment> segments = new ArrayList<>();
        String last;
        int switches;
        int busy;

        void run(String pid, int start, int end) {
            Segment tail = segments.isEmpty() ? null : segments.get(segments.size() - 1);
            if (tail != null && tail.pid.equals(pid) && tail.end == start) {
                tail.end = end;
            } else {
                if (last != null && !last.equals(pid)) switches++;
                segments.add(new Segment(pid, start, end));
            }
            last = pid;
            busy += end - start;
        }
    }

    private static final class Run {
        final List<String> pids;
        final Map<String, Integer> first = new HashMap<>();
        final Map<String, Integer> done = new HashMap<>();
        final List<Core> cores = new ArrayList<>();
        int migrations;
        int makespan;

        Run(List<String> pids, int coreCount) {
            this.pids = new ArrayList<>(pids);
            for (int c = 0; c < coreCount; c++) cores.add(new Core());
        }

        void started(String pid, int time) {
            first.putIfAbsent(pid, time);
        }

        List<List<String>> timelines() {
            List<List<String>> lines = new ArrayList<>();
            for (Core core : cores) {
                List<String> line = new ArrayList<>();
                for (Segment s : core.segments) line.add(s.pid + ":" + s.start + "-" + s.end);
                lines.add(line);
            }
            return lines;
        }
    }

    private final List<String> pids = new ArrayList<>();
    private final Map<String, Integer> arrival = new HashMap<>();
    private final Map<String, Integer> burst = new HashMap<>();
    private Run latest;

    public CpuScheduler() {}

    // Level 1
    public boolean addProcess(String pid, int arrival, int burst) {
        if (this.arrival.containsKey(pid)) return false;
        pids.add(pid);
        this.arrival.put(pid, arrival);
        this.burst.put(pid, burst);
        return true;
    }

    public List<String> runFcfs() {
        Run run = new Run(pids, 1);
        int clock = 0;
        for (String pid : byArrival()) {
            clock = runToCompletion(run, pid, Math.max(clock, arrival.get(pid)));
        }
        return keep(run, clock).get(0);
    }

    public List<String> runSjf() {
        Run run = new Run(pids, 1);
        Map<String, Integer> position = new HashMap<>();
        for (int i = 0; i < pids.size(); i++) position.put(pids.get(i), i);
        Comparator<String> order = Comparator.<String>comparingInt(burst::get)
                .thenComparingInt(arrival::get)
                .thenComparingInt(position::get);
        List<String> pending = new ArrayList<>(pids);
        int clock = 0;
        while (!pending.isEmpty()) {
            final int now = clock;
            Optional<String> pick = pending.stream().filter(p -> arrival.get(p) <= now).min(order);
            if (pick.isEmpty()) {
                clock = pending.stream().mapToInt(arrival::get).min().getAsInt();
                continue;
            }
            pending.remove(pick.get());
            clock = runToCompletion(run, pick.get(), clock);
        }
        return keep(run, clock).get(0);
    }

    public int waitingTime(String pid) {
        int turnaround = turnaroundTime(pid);
        return turnaround == -1 ? -1 : turnaround - burst.get(pid);
    }

    public int turnaroundTime(String pid) {
        if (latest == null || !latest.done.containsKey(pid)) return -1;
        return latest.done.get(pid) - arrival.get(pid);
    }

    public String averageWaiting() {
        return average(this::waitingTime);
    }

    public String averageTurnaround() {
        return average(this::turnaroundTime);
    }

    // Level 2
    public List<String> runRoundRobin(int quantum) {
        return roundRobin(1, quantum, false).get(0);
    }

    public int responseTime(String pid) {
        if (latest == null || !latest.first.containsKey(pid)) return -1;
        return latest.first.get(pid) - arrival.get(pid);
    }

    public String averageResponse() {
        return average(this::responseTime);
    }

    public int contextSwitches() {
        if (latest == null) return -1;
        int total = 0;
        for (Core core : latest.cores) total += core.switches;
        return total;
    }

    // Level 3
    public List<String> runMlfq(int[] quanta, int boostPeriod) {
        Run run = new Run(pids, 1);
        Core core = run.cores.get(0);
        Map<String, Integer> remaining = new HashMap<>(burst);
        Deque<String> arrivals = new ArrayDeque<>(byArrival());
        List<Deque<String>> queues = new ArrayList<>();
        for (int i = 0; i < quanta.length; i++) queues.add(new ArrayDeque<>());
        Map<String, Integer> level = new HashMap<>();
        Map<String, Integer> used = new HashMap<>();
        String running = null;
        int left = pids.size();
        int clock = 0;
        while (true) {
            String demoted = null;
            if (running != null) {
                if (remaining.get(running) == 0) {
                    run.done.put(running, clock);
                    running = null;
                    left--;
                } else if (used.get(running) == quanta[level.get(running)]) {
                    level.put(running, Math.min(level.get(running) + 1, quanta.length - 1));
                    used.put(running, 0);
                    demoted = running;
                    running = null;
                }
            }
            if (left == 0) break;
            while (!arrivals.isEmpty() && arrival.get(arrivals.peekFirst()) == clock) {
                String pid = arrivals.pollFirst();
                level.put(pid, 0);
                used.put(pid, 0);
                queues.get(0).addLast(pid);
            }
            if (demoted != null) queues.get(level.get(demoted)).addLast(demoted);
            if (boostPeriod > 0 && clock > 0 && clock % boostPeriod == 0) {
                Deque<String> merged = new ArrayDeque<>();
                for (Deque<String> queue : queues) {
                    merged.addAll(queue);
                    queue.clear();
                }
                queues.set(0, merged);
                List<String> lifted = new ArrayList<>(merged);
                if (running != null) lifted.add(running);
                for (String pid : lifted) {
                    level.put(pid, 0);
                    used.put(pid, 0);
                }
            }
            if (running != null) {
                boolean higher = false;
                for (int i = 0; i < level.get(running); i++) higher |= !queues.get(i).isEmpty();
                if (higher) {
                    queues.get(level.get(running)).addLast(running);
                    running = null;
                }
            }
            if (running == null) {
                for (Deque<String> queue : queues) {
                    if (!queue.isEmpty()) {
                        running = queue.pollFirst();
                        break;
                    }
                }
            }
            if (running != null) {
                run.started(running, clock);
                core.run(running, clock, clock + 1);
                remaining.merge(running, -1, Integer::sum);
                used.merge(running, 1, Integer::sum);
            }
            clock++;
        }
        return keep(run, clock).get(0);
    }

    // Level 4
    public List<List<String>> runMulticore(int cores, int quantum, boolean steal) {
        return roundRobin(cores, quantum, steal);
    }

    public String utilization(int core) {
        if (latest == null || core < 0 || core >= latest.cores.size()) return "";
        return fraction(latest.cores.get(core).busy, latest.makespan);
    }

    public int migrations() {
        return latest == null ? -1 : latest.migrations;
    }

    // The clock loops
    private List<List<String>> roundRobin(int cores, int quantum, boolean steal) {
        Run run = new Run(pids, cores);
        Map<String, Integer> remaining = new HashMap<>(burst);
        Deque<String> arrivals = new ArrayDeque<>(byArrival());
        List<Deque<String>> queues = new ArrayList<>();
        for (int c = 0; c < cores; c++) queues.add(new ArrayDeque<>());
        String[] running = new String[cores];
        int[] used = new int[cores];
        int left = pids.size();
        int clock = 0;
        while (true) {
            String[] expired = new String[cores];
            for (int c = 0; c < cores; c++) {
                String pid = running[c];
                if (pid != null && remaining.get(pid) == 0) {
                    run.done.put(pid, clock);
                    running[c] = null;
                    left--;
                } else if (pid != null && used[c] == quantum) {
                    expired[c] = pid;
                    running[c] = null;
                }
            }
            if (left == 0) break;
            while (!arrivals.isEmpty() && arrival.get(arrivals.peekFirst()) == clock) {
                int target = 0;
                int lowest = Integer.MAX_VALUE;
                for (int c = 0; c < cores; c++) {
                    int load = queues.get(c).size() + (running[c] != null ? 1 : 0) + (expired[c] != null ? 1 : 0);
                    if (load < lowest) {
                        lowest = load;
                        target = c;
                    }
                }
                queues.get(target).addLast(arrivals.pollFirst());
            }
            for (int c = 0; c < cores; c++) {
                if (expired[c] != null) queues.get(c).addLast(expired[c]);
                if (running[c] == null && !queues.get(c).isEmpty()) {
                    running[c] = queues.get(c).pollFirst();
                    used[c] = 0;
                }
            }
            for (int c = 0; steal && c < cores; c++) {
                if (running[c] != null) continue;
                int victim = 0;
                for (int v = 1; v < cores; v++) {
                    if (queues.get(v).size() > queues.get(victim).size()) victim = v;
                }
                if (!queues.get(victim).isEmpty()) {
                    running[c] = queues.get(victim).pollLast();
                    used[c] = 0;
                    run.migrations++;
                }
            }
            for (int c = 0; c < cores; c++) {
                String pid = running[c];
                if (pid == null) continue;
                run.started(pid, clock);
                run.cores.get(c).run(pid, clock, clock + 1);
                remaining.merge(pid, -1, Integer::sum);
                used[c]++;
            }
            clock++;
        }
        return keep(run, clock);
    }

    private int runToCompletion(Run run, String pid, int start) {
        int end = start + burst.get(pid);
        run.started(pid, start);
        run.cores.get(0).run(pid, start, end);
        run.done.put(pid, end);
        return end;
    }

    private List<String> byArrival() {
        List<String> order = new ArrayList<>(pids);
        order.sort(Comparator.comparingInt(arrival::get));
        return order;
    }

    private List<List<String>> keep(Run run, int makespan) {
        run.makespan = makespan;
        latest = run;
        return run.timelines();
    }

    private interface Metric {
        int of(String pid);
    }

    private String average(Metric metric) {
        if (latest == null) return "";
        int total = 0;
        for (String pid : latest.pids) total += metric.of(pid);
        return fraction(total, latest.pids.size());
    }

    private static String fraction(int numerator, int denominator) {
        int a = numerator;
        int b = denominator;
        while (b != 0) {
            int r = a % b;
            a = b;
            b = r;
        }
        return numerator / a + "/" + denominator / a;
    }
}
