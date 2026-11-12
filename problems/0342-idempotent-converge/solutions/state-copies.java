import java.util.*;
import java.util.regex.Pattern;

/**
 * Tasks describe the state a host should be in. Running a task compares that state with the host's
 * and changes the host only when they differ, so a second run finds nothing to do. A run works
 * through the hosts in batches; in each batch it applies every task to every host still standing,
 * then the handlers that a change notified. A check run does the same on copies of the hosts, so
 * later tasks see what earlier ones would have done while the real hosts stay as they were.
 */
public class Converger {
    private static final List<String> COUNTED = List.of("ok", "changed", "failed", "skipped");
    private static final Pattern WHOLE = Pattern.compile("-?[0-9]+");

    private static final class Host {
        final Map<String, String> files;
        final Map<String, String> packages;
        final Map<String, String> facts;

        Host() {
            this(new HashMap<>(), new HashMap<>(), new HashMap<>());
        }

        Host(Map<String, String> files, Map<String, String> packages, Map<String, String> facts) {
            this.files = files;
            this.packages = packages;
            this.facts = facts;
        }

        Host copy() {
            return new Host(new HashMap<>(files), new HashMap<>(packages), facts);
        }
    }

    private record Action(String kind, String target, String value) {}

    private record Outcome(String status, List<String> diff) {}

    private final LinkedHashMap<String, Host> hosts = new LinkedHashMap<>();
    private final LinkedHashMap<String, Action> tasks = new LinkedHashMap<>();
    private final LinkedHashMap<String, Action> handlers = new LinkedHashMap<>();
    private final Map<String, List<String>> links = new HashMap<>();
    private final Map<String, List<Action>> conditions = new HashMap<>();
    private int batch = 0;
    private Map<String, Map<String, Integer>> counts = new HashMap<>();

    public Converger() {}

    // Level 1
    public boolean addHost(String host) {
        return hosts.putIfAbsent(host, new Host()) == null;
    }

    public boolean setState(String host, String kind, String target, String value) {
        Host found = hosts.get(host);
        if (found == null) {
            return false;
        }
        apply(found, kind, target, value);
        return true;
    }

    public boolean addTask(String name, String kind, String target, String value) {
        return tasks.putIfAbsent(name, new Action(kind, target, value)) == null;
    }

    public List<List<String>> run() {
        Map<String, Map<String, Integer>> fresh = zeros();
        List<List<String>> rows = play(hosts, false, fresh);
        counts = fresh;
        return rows;
    }

    public List<List<String>> state(String host) {
        Host found = hosts.get(host);
        List<List<String>> rows = new ArrayList<>();
        if (found == null) {
            return rows;
        }
        found.files.forEach((path, content) -> rows.add(List.of("file", path, content)));
        found.packages.forEach((name, service) -> {
            rows.add(List.of("package", name, "present"));
            rows.add(List.of("service", name, service));
        });
        rows.sort(Comparator.<List<String>, String>comparing(row -> row.get(0)).thenComparing(row -> row.get(1)));
        return rows;
    }

    // Level 2
    public List<List<String>> check() {
        LinkedHashMap<String, Host> copies = new LinkedHashMap<>();
        hosts.forEach((name, host) -> copies.put(name, host.copy()));
        return play(copies, true, zeros());
    }

    // Level 3
    public boolean addHandler(String name, String kind, String target, String value) {
        return handlers.putIfAbsent(name, new Action(kind, target, value)) == null;
    }

    public boolean notifies(String task, String handler) {
        if (!tasks.containsKey(task) || !handlers.containsKey(handler)) {
            return false;
        }
        List<String> linked = links.computeIfAbsent(task, t -> new ArrayList<>());
        if (linked.contains(handler)) {
            return false;
        }
        linked.add(handler);
        return true;
    }

    // Level 4
    public boolean setFact(String host, String key, String value) {
        Host found = hosts.get(host);
        if (found == null) {
            return false;
        }
        return found.facts.put(key, value) == null;
    }

    public boolean onlyIf(String task, String fact, String comparison, String value) {
        if (!tasks.containsKey(task)) {
            return false;
        }
        conditions.computeIfAbsent(task, t -> new ArrayList<>()).add(new Action(fact, comparison, value));
        return true;
    }

    public boolean setBatchSize(int size) {
        boolean changed = size != batch;
        batch = size;
        return changed;
    }

    public List<List<String>> summary() {
        List<List<String>> rows = new ArrayList<>();
        for (String host : hosts.keySet()) {
            Map<String, Integer> tally = counts.get(host);
            List<String> row = new ArrayList<>(List.of(host));
            for (String name : COUNTED) {
                row.add(String.valueOf(tally == null ? 0 : tally.get(name)));
            }
            rows.add(row);
        }
        return rows;
    }

    // Running
    private Map<String, Map<String, Integer>> zeros() {
        Map<String, Map<String, Integer>> fresh = new HashMap<>();
        for (String host : hosts.keySet()) {
            Map<String, Integer> tally = new HashMap<>();
            COUNTED.forEach(name -> tally.put(name, 0));
            fresh.put(host, tally);
        }
        return fresh;
    }

    private List<List<String>> play(
            LinkedHashMap<String, Host> on, boolean dry, Map<String, Map<String, Integer>> tally) {
        List<String> names = new ArrayList<>(on.keySet());
        int size = batch > 0 ? batch : Math.max(names.size(), 1);
        List<List<String>> rows = new ArrayList<>();
        for (int start = 0; start < names.size(); start += size) {
            List<String> group = names.subList(start, Math.min(start + size, names.size()));
            Set<String> failed = new HashSet<>();
            Map<String, Set<String>> notified = new HashMap<>();
            group.forEach(host -> notified.put(host, new HashSet<>()));
            for (Map.Entry<String, Action> task : tasks.entrySet()) {
                for (String host : group) {
                    if (failed.contains(host)) {
                        continue;
                    }
                    Outcome outcome = task(on.get(host), task.getKey(), task.getValue());
                    if (outcome.status().equals("failed")) {
                        failed.add(host);
                    } else if (outcome.status().equals("changed")) {
                        notified.get(host).addAll(links.getOrDefault(task.getKey(), List.of()));
                    }
                    record(rows, tally, host, task.getKey(), outcome, dry);
                }
            }
            for (Map.Entry<String, Action> handler : handlers.entrySet()) {
                for (String host : group) {
                    if (failed.contains(host) || !notified.get(host).contains(handler.getKey())) {
                        continue;
                    }
                    Outcome outcome = change(on.get(host), handler.getValue());
                    if (outcome.status().equals("failed")) {
                        failed.add(host);
                    }
                    record(rows, tally, host, handler.getKey(), outcome, dry);
                }
            }
            if (failed.size() == group.size()) {
                break;
            }
        }
        return rows;
    }

    private static void record(List<List<String>> rows, Map<String, Map<String, Integer>> tally,
            String host, String name, Outcome outcome, boolean dry) {
        tally.get(host).merge(outcome.status(), 1, Integer::sum);
        List<String> row = new ArrayList<>(List.of(host, name, outcome.status()));
        if (dry) {
            row.addAll(outcome.diff());
        }
        rows.add(row);
    }

    private Outcome task(Host host, String name, Action action) {
        for (Action condition : conditions.getOrDefault(name, List.of())) {
            String have = host.facts.get(condition.kind());
            if (have == null) {
                return new Outcome("failed", List.of());
            }
            Boolean holds = compare(have, condition.target(), condition.value());
            if (holds == null) {
                return new Outcome("failed", List.of());
            }
            if (!holds) {
                return new Outcome("skipped", List.of());
            }
        }
        return change(host, action);
    }

    /** The truth of one condition, or null when it cannot be decided. */
    private static Boolean compare(String fact, String operator, String value) {
        if (operator.equals("==")) {
            return fact.equals(value);
        }
        if (operator.equals("!=")) {
            return !fact.equals(value);
        }
        if (!WHOLE.matcher(fact).matches() || !WHOLE.matcher(value).matches()) {
            return null;
        }
        long left = Long.parseLong(fact);
        long right = Long.parseLong(value);
        return switch (operator) {
            case "<" -> left < right;
            case "<=" -> left <= right;
            case ">" -> left > right;
            default -> left >= right;
        };
    }

    /** The state a task of this kind compares with, or null for a missing service. */
    private static String current(Host host, String kind, String target) {
        return switch (kind) {
            case "file" -> host.files.getOrDefault(target, "");
            case "package" -> host.packages.containsKey(target) ? "present" : "absent";
            default -> host.packages.get(target);
        };
    }

    private static Outcome change(Host host, Action action) {
        String before = current(host, action.kind(), action.target());
        if (before == null) {
            return new Outcome("failed", List.of());
        }
        if (before.equals(action.value()) && !action.value().equals("restarted")) {
            return new Outcome("ok", List.of());
        }
        apply(host, action.kind(), action.target(), action.value());
        return new Outcome("changed", List.of(before, action.value()));
    }

    private static void apply(Host host, String kind, String target, String value) {
        if (kind.equals("file")) {
            host.files.put(target, value);
        } else if (kind.equals("package") && value.equals("present")) {
            host.packages.putIfAbsent(target, "stopped");
        } else if (kind.equals("package")) {
            host.packages.remove(target);
        } else {
            host.packages.put(target, value.equals("restarted") ? "running" : value);
        }
    }
}
