import java.util.*;

/**
 * Tasks and their dependencies form a graph. The order counts the unlisted dependencies of each
 * task and keeps the ready names in a heap, so that the smallest ready name goes next.
 *
 * <p>A ledger keyed by (task, day) records each partition's state. Every write gets a number, and
 * the partition remembers the number of each input it read, which is all it takes to tell a stale
 * partition and to find what a backfill must rerun. Runs and backfills share one attempt loop,
 * which follows the scripted outcomes and the task's retries.
 */
public class PipelineScheduler {
    private static final String DONE = "done";
    private static final String FAILED = "failed";
    private static final String MISSING = "missing";

    private record Part(String task, int day) {}

    private record Outcome(int round, String status, int attempts) {}

    private final Map<String, List<String>> deps = new LinkedHashMap<>();
    private final Map<List<String>, Integer> windows = new HashMap<>();
    private final Map<String, Integer> retries = new HashMap<>();
    private final Map<Part, Deque<String>> scripts = new HashMap<>();
    private final Map<Part, String> state = new HashMap<>();
    private final Map<Part, Integer> written = new HashMap<>();
    private final Map<Part, Map<Part, Integer>> reads = new HashMap<>();
    private int writes = 0;

    // Level 1
    public boolean addTask(String name, List<String> deps) {
        if (this.deps.containsKey(name)) {
            return false;
        }
        this.deps.put(name, new ArrayList<>(new LinkedHashSet<>(deps)));
        return true;
    }

    public List<List<String>> validate() {
        List<List<String>> problems = new ArrayList<>();
        for (Map.Entry<String, List<String>> entry : deps.entrySet()) {
            for (String dep : entry.getValue()) {
                if (!deps.containsKey(dep)) {
                    problems.add(List.of("unknown-dependency", entry.getKey(), dep));
                }
            }
        }
        Set<String> listed = new HashSet<>(order());
        for (String task : deps.keySet()) {
            if (!listed.contains(task) && reachesItself(task)) {
                problems.add(List.of("cycle", task));
            }
        }
        problems.sort((a, b) -> {
            for (int i = 0; i < Math.min(a.size(), b.size()); i++) {
                int c = a.get(i).compareTo(b.get(i));
                if (c != 0) {
                    return c;
                }
            }
            return Integer.compare(a.size(), b.size());
        });
        return problems;
    }

    public List<String> runOrder() {
        return validate().isEmpty() ? order() : new ArrayList<>();
    }

    // Level 2
    public boolean setWindow(String task, String dep, int days) {
        if (!deps.getOrDefault(task, List.of()).contains(dep)) {
            return false;
        }
        windows.put(List.of(task, dep), days);
        return true;
    }

    public void markDone(String task, int day) {
        store(task, day);
    }

    public List<String> runnable(int day) {
        List<String> tasks = new ArrayList<>();
        for (String task : deps.keySet()) {
            if (!DONE.equals(state.get(new Part(task, day))) && inputsDone(task, day)) {
                tasks.add(task);
            }
        }
        Collections.sort(tasks);
        return tasks;
    }

    // Level 3
    public void setRetries(String task, int retries) {
        this.retries.put(task, retries);
    }

    public void script(String task, int day, List<String> outcomes) {
        scripts.put(new Part(task, day), new ArrayDeque<>(outcomes));
    }

    public List<List<String>> run(int day) {
        List<List<String>> rows = new ArrayList<>();
        for (String task : runOrder()) {
            if (!inputsDone(task, day)) {
                rows.add(List.of(task, "skipped", "0"));
                continue;
            }
            int attempts = attempt(task, day);
            boolean succeeded = attempts > 0;
            rows.add(List.of(task, succeeded ? "success" : "failed", String.valueOf(Math.abs(attempts))));
        }
        return rows;
    }

    public String status(String task, int day) {
        return state.getOrDefault(new Part(task, day), MISSING);
    }

    // Level 4
    public List<String> stale(int day) {
        List<String> tasks = new ArrayList<>();
        for (String task : deps.keySet()) {
            if (isStale(new Part(task, day))) {
                tasks.add(task);
            }
        }
        Collections.sort(tasks);
        return tasks;
    }

    public List<List<String>> plan(String task, int fromDay, int toDay) {
        List<List<String>> rows = new ArrayList<>();
        for (Part p : makePlan(task, fromDay, toDay)) {
            rows.add(List.of(String.valueOf(p.day()), p.task()));
        }
        return rows;
    }

    public List<List<String>> backfill(String task, int fromDay, int toDay, int cap) {
        List<Part> plan = makePlan(task, fromDay, toDay);
        Set<Part> planned = new HashSet<>(plan);
        Map<Part, Outcome> outcome = new HashMap<>();
        int round = 0;
        while (outcome.size() < plan.size()) {
            round += 1;
            // Inputs come before their users in plan order, so one pass settles every skip.
            for (Part p : plan) {
                if (!outcome.containsKey(p) && blocked(p, planned, outcome)) {
                    outcome.put(p, new Outcome(round, "skipped", 0));
                }
            }
            List<Part> ready = new ArrayList<>();
            for (Part p : plan) {
                if (ready.size() < cap && !outcome.containsKey(p) && plannedInputsSucceeded(p, planned, outcome)) {
                    ready.add(p);
                }
            }
            for (Part p : ready) {
                int attempts = attempt(p.task(), p.day());
                outcome.put(p, new Outcome(round, attempts > 0 ? "success" : "failed", Math.abs(attempts)));
            }
        }
        Map<String, Integer> rank = rank();
        List<Part> decided = new ArrayList<>(plan);
        decided.sort(Comparator.<Part>comparingInt(p -> outcome.get(p).round())
                .thenComparingInt(Part::day)
                .thenComparingInt(p -> rank.get(p.task())));
        List<List<String>> rows = new ArrayList<>();
        for (Part p : decided) {
            Outcome o = outcome.get(p);
            rows.add(List.of(
                    String.valueOf(o.round()), String.valueOf(p.day()), p.task(), o.status(),
                    String.valueOf(o.attempts())));
        }
        return rows;
    }

    // The graph
    private Map<String, List<String>> users() {
        Map<String, List<String>> users = new HashMap<>();
        for (String task : deps.keySet()) {
            users.put(task, new ArrayList<>());
        }
        for (Map.Entry<String, List<String>> entry : deps.entrySet()) {
            for (String dep : entry.getValue()) {
                if (users.containsKey(dep)) {
                    users.get(dep).add(entry.getKey());
                }
            }
        }
        return users;
    }

    private List<String> order() {
        Map<String, Integer> waiting = new HashMap<>();
        PriorityQueue<String> ready = new PriorityQueue<>();
        for (Map.Entry<String, List<String>> entry : deps.entrySet()) {
            int count = 0;
            for (String dep : entry.getValue()) {
                if (deps.containsKey(dep)) {
                    count += 1;
                }
            }
            waiting.put(entry.getKey(), count);
            if (count == 0) {
                ready.add(entry.getKey());
            }
        }
        Map<String, List<String>> users = users();
        List<String> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            String task = ready.poll();
            order.add(task);
            for (String user : users.get(task)) {
                int left = waiting.merge(user, -1, Integer::sum);
                if (left == 0) {
                    ready.add(user);
                }
            }
        }
        return order;
    }

    private boolean reachesItself(String start) {
        Set<String> seen = new HashSet<>();
        Deque<String> stack = new ArrayDeque<>();
        for (String dep : deps.get(start)) {
            if (deps.containsKey(dep)) {
                stack.push(dep);
            }
        }
        while (!stack.isEmpty()) {
            String task = stack.pop();
            if (task.equals(start)) {
                return true;
            }
            if (seen.add(task)) {
                for (String dep : deps.get(task)) {
                    if (deps.containsKey(dep)) {
                        stack.push(dep);
                    }
                }
            }
        }
        return false;
    }

    private Map<String, Integer> rank() {
        Map<String, Integer> rank = new HashMap<>();
        List<String> order = runOrder();
        for (int i = 0; i < order.size(); i++) {
            rank.put(order.get(i), i);
        }
        return rank;
    }

    // The partitions
    private int width(String task, String dep) {
        return windows.getOrDefault(List.of(task, dep), 1);
    }

    private List<Part> inputs(String task, int day) {
        List<Part> inputs = new ArrayList<>();
        for (String dep : deps.get(task)) {
            for (int d = Math.max(0, day - width(task, dep) + 1); d <= day; d++) {
                inputs.add(new Part(dep, d));
            }
        }
        return inputs;
    }

    private int current(Part p) {
        return DONE.equals(state.get(p)) ? written.get(p) : 0;
    }

    private boolean inputsDone(String task, int day) {
        for (Part p : inputs(task, day)) {
            if (!DONE.equals(state.get(p))) {
                return false;
            }
        }
        return true;
    }

    private void store(String task, int day) {
        writes += 1;
        Part p = new Part(task, day);
        state.put(p, DONE);
        written.put(p, writes);
        Map<Part, Integer> seen = new HashMap<>();
        for (Part input : inputs(task, day)) {
            seen.put(input, current(input));
        }
        reads.put(p, seen);
    }

    /** The number of attempts, negated when every attempt failed. */
    private int attempt(String task, int day) {
        Deque<String> script = scripts.getOrDefault(new Part(task, day), new ArrayDeque<>());
        int limit = 1 + retries.getOrDefault(task, 0);
        for (int attempt = 1; attempt <= limit; attempt++) {
            String next = script.isEmpty() ? "ok" : script.pollFirst();
            if (next.equals("ok")) {
                store(task, day);
                return attempt;
            }
        }
        state.put(new Part(task, day), FAILED);
        return -limit;
    }

    private boolean isStale(Part p) {
        if (!DONE.equals(state.get(p))) {
            return false;
        }
        for (Map.Entry<Part, Integer> entry : reads.get(p).entrySet()) {
            if (current(entry.getKey()) != entry.getValue()) {
                return true;
            }
        }
        return false;
    }

    private List<Part> makePlan(String task, int fromDay, int toDay) {
        Map<String, List<String>> users = users();
        Set<Part> planned = new HashSet<>();
        Deque<Part> frontier = new ArrayDeque<>();
        for (int day = fromDay; day <= toDay; day++) {
            planned.add(new Part(task, day));
            frontier.push(new Part(task, day));
        }
        while (!frontier.isEmpty()) {
            Part p = frontier.pop();
            for (String user : users.get(p.task())) {
                for (int later = p.day(); later < p.day() + width(user, p.task()); later++) {
                    Part next = new Part(user, later);
                    if (DONE.equals(state.get(next)) && planned.add(next)) {
                        frontier.push(next);
                    }
                }
            }
        }
        Map<String, Integer> rank = rank();
        List<Part> plan = new ArrayList<>(planned);
        plan.sort(Comparator.comparingInt(Part::day).thenComparingInt(p -> rank.get(p.task())));
        return plan;
    }

    private boolean blocked(Part p, Set<Part> planned, Map<Part, Outcome> outcome) {
        for (Part input : inputs(p.task(), p.day())) {
            if (planned.contains(input)) {
                Outcome o = outcome.get(input);
                if (o != null && !o.status().equals("success")) {
                    return true;
                }
            } else if (!DONE.equals(state.get(input))) {
                return true;
            }
        }
        return false;
    }

    private boolean plannedInputsSucceeded(Part p, Set<Part> planned, Map<Part, Outcome> outcome) {
        for (Part input : inputs(p.task(), p.day())) {
            if (planned.contains(input)) {
                Outcome o = outcome.get(input);
                if (o == null || !o.status().equals("success")) {
                    return false;
                }
            }
        }
        return true;
    }
}
